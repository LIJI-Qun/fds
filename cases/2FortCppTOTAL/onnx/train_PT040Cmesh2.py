# train_PT040Cmesh2.py
import os, glob, time, random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt

# ================== 导入外部模型 ==================
from unet_model_pressure import ModifiedUNet

# ================== 配置 ==================
CSV_DIR = "./dataT40C"          # 40×40 网格的 CSV 数据目录
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
FIXED_VIS_FILE = "Thot_40_0_pressure_m1_step113000.csv"  # 40x40 可视化固定文件

BATCH_SIZE = 8
EPOCHS = 500
LR = 1e-3
VALID_SPLIT = 0.1

# 模型保存路径
MODEL_PATH = "best_pressure_delta_40x40_base24.pth"
RESULT_DIR = "results_pressure_delta_40x40"
os.makedirs(RESULT_DIR, exist_ok=True)

I_MAX = 40
K_MAX = 40

# 填充策略 40→48，左右上下各补4 (被 8 整除)
PAD_DIMS = (4, 4, 4, 4)   # (左, 右, 上, 下) -> 40×40 变 48×48

# ================== 随机种子 ==================
def seed_everything(seed=42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# ================== 数据集 ==================
class PressureDeltaDataset(Dataset):
    def __init__(self, csv_dir):
        self.files = glob.glob(os.path.join(csv_dir, "*.csv"))
        if not self.files:
            raise FileNotFoundError(f"未在 {csv_dir} 中找到 CSV 文件！")
        print(f"检测到 {len(self.files)} 个 CSV 样本文件。")

        self.data_cache = []
        print("正在将所有数据载入内存，请稍候...")
        for i, f in enumerate(self.files):
            df = pd.read_csv(f, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            try:
                vals = df[['I', 'K', 'X', 'Y', 'Z', 'Div', 'RHS', 'P_old', 'P_new']].values
            except KeyError as e:
                raise KeyError(f"\n文件 {os.path.basename(f)} 列名匹配失败！")
            self.data_cache.append(vals)
            
        # 计算输入特征和增量的全局统计量
        self.input_mean, self.input_std, self.delta_mean, self.delta_std = self._compute_stats()

    def __len__(self):
        return len(self.data_cache)

    def __getitem__(self, idx):
        vals = self.data_cache[idx]
        inputs = np.zeros((6, K_MAX, I_MAX), dtype=np.float32)
        target_delta = np.zeros((1, K_MAX, I_MAX), dtype=np.float32)
        p_old = np.zeros((1, K_MAX, I_MAX), dtype=np.float32)
        mask = np.zeros((1, K_MAX, I_MAX), dtype=np.float32)

        i_idx = vals[:, 0].astype(int) - 1
        k_idx = vals[:, 1].astype(int) - 1

        inputs[0, k_idx, i_idx] = vals[:, 2]   # X
        inputs[1, k_idx, i_idx] = vals[:, 3]   # Y
        inputs[2, k_idx, i_idx] = vals[:, 4]   # Z
        inputs[3, k_idx, i_idx] = vals[:, 5]   # Div
        inputs[4, k_idx, i_idx] = vals[:, 6]   # RHS
        inputs[5, k_idx, i_idx] = vals[:, 7]   # P_old

        # 目标：ΔP = P_new - P_old
        delta = vals[:, 8] - vals[:, 7]
        target_delta[0, k_idx, i_idx] = delta
        p_old[0, k_idx, i_idx] = vals[:, 7]
        mask[0, k_idx, i_idx] = 1.0

        # 标准化
        inputs = (inputs - self.input_mean) / (self.input_std + 1e-8)
        target_delta = (target_delta - self.delta_mean) / (self.delta_std + 1e-8)

        inputs = torch.from_numpy(inputs)
        target_delta = torch.from_numpy(target_delta)
        p_old = torch.from_numpy(p_old)
        mask = torch.from_numpy(mask)

        # Padding 策略：(核心修复，保证PyTorch的replicate不出错)
        # 特征 (inputs) 使用 replicate 以拟合泊松方程的诺依曼边界条件
        inputs = F.pad(inputs.unsqueeze(0), PAD_DIMS, mode='replicate').squeeze(0)
        
        # Target/Mask 等使用 0 填充，后续不会计入 Loss
        target_delta = F.pad(target_delta.unsqueeze(0), PAD_DIMS, mode='constant', value=0.0).squeeze(0)
        p_old = F.pad(p_old.unsqueeze(0), PAD_DIMS, mode='constant', value=0.0).squeeze(0)
        mask = F.pad(mask.unsqueeze(0), PAD_DIMS, mode='constant', value=0.0).squeeze(0)

        return inputs, target_delta, p_old, mask

    def _compute_stats(self):
        # 缓存文件名修改为适应 40x40
        cache_path = os.path.join(os.path.dirname(self.files[0]), "delta_stats_cache_40x40.npz")
        if os.path.exists(cache_path):
            print(f"读取本地缓存的均值与方差数据 ({cache_path})...")
            data = np.load(cache_path)
            return data['feat_mean'], data['feat_std'], data['delta_mean'], data['delta_std']

        print("首次运行，正在计算全局均值与方差（增量），请稍候...")
        all_feat = []
        all_delta = []
        for vals in self.data_cache:
            features = vals[:, 2:8]                    
            delta = (vals[:, 8] - vals[:, 7]).reshape(-1, 1)  
            all_feat.append(features)
            all_delta.append(delta)

        all_feat = np.concatenate(all_feat, axis=0)
        all_delta = np.concatenate(all_delta, axis=0)

        feat_mean = np.mean(all_feat, axis=0, keepdims=True).T.reshape(6, 1, 1).astype(np.float32)
        feat_std  = np.std(all_feat, axis=0, keepdims=True).T.reshape(6, 1, 1).astype(np.float32)
        delta_mean = np.mean(all_delta, axis=0, keepdims=True).reshape(1, 1, 1).astype(np.float32)
        delta_std  = np.std(all_delta, axis=0, keepdims=True).reshape(1, 1, 1).astype(np.float32)

        np.savez(cache_path,
                 feat_mean=feat_mean, feat_std=feat_std,
                 delta_mean=delta_mean, delta_std=delta_std)
        print("增量均值与方差计算完毕并已缓存。")
        return feat_mean, feat_std, delta_mean, delta_std

# ================== 训练与验证 ==================
def train_epoch(model, loader, optimizer, criterion):
    model.train()
    total_loss = 0.0
    for inputs, targets, _, masks in loader:
        inputs, targets, masks = inputs.to(DEVICE), targets.to(DEVICE), masks.to(DEVICE)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        
        # Huber Loss (SmoothL1Loss) 计算
        loss = criterion(outputs * masks, targets * masks) / (masks.sum() + 1e-8)
        loss.backward()
        
        # 梯度裁剪：限制梯度最大 L2 范数，防止因为流体奇异点导致的梯度爆炸
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        total_loss += loss.item() * inputs.size(0)
    return total_loss / len(loader.dataset)

def validate(model, loader, criterion):
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for inputs, targets, _, masks in loader:
            inputs, targets, masks = inputs.to(DEVICE), targets.to(DEVICE), masks.to(DEVICE)
            outputs = model(inputs)
            loss = criterion(outputs * masks, targets * masks) / (masks.sum() + 1e-8)
            total_loss += loss.item() * inputs.size(0)
    return total_loss / len(loader.dataset)


def plot_predictions_fixed_file(model, dataset, delta_mean, delta_std, epoch, device, target_filename):
    """
    固定使用某个 CSV 文件做可视化
    """
    model.eval()
    try:
        file_idx = [os.path.basename(f) for f in dataset.files].index(target_filename)
    except ValueError:
        # 如果指定文件不存在，回退到索引0
        print(f"警告：文件 {target_filename} 不在数据集中，将使用第一个样本可视化。")
        file_idx = 0
        target_filename = os.path.basename(dataset.files[0])

    inputs, target_delta, p_old, mask = dataset[file_idx]
    inputs = inputs.unsqueeze(0).to(device)

    with torch.no_grad():
        pred_delta = model(inputs).cpu()

    pred_delta_np = pred_delta[0,0].numpy()
    true_delta_np = target_delta[0].numpy()        
    p_old_np = p_old[0].numpy()
    mask_np = mask[0].numpy()

    # 反归一化
    pred_delta_np = pred_delta_np * delta_std.item() + delta_mean.item()
    true_delta_np = true_delta_np * delta_std.item() + delta_mean.item()

    pred_pressure = p_old_np + pred_delta_np
    true_pressure = p_old_np + true_delta_np

    pred_pressure[mask_np < 0.5] = np.nan
    true_pressure[mask_np < 0.5] = np.nan

    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    vmin = np.nanmin(true_pressure)
    vmax = np.nanmax(true_pressure)

    im0 = ax[0].imshow(true_pressure, cmap='jet', origin='lower', vmin=vmin, vmax=vmax)
    ax[0].set_title(f'Target P_new (Pa)\n{target_filename}')
    im1 = ax[1].imshow(pred_pressure, cmap='jet', origin='lower', vmin=vmin, vmax=vmax)
    ax[1].set_title('Predicted P_new (Pa)')
    error = np.abs(pred_pressure - true_pressure)
    im2 = ax[2].imshow(error, cmap='hot', origin='lower')
    ax[2].set_title(f'Abs Error (Max: {np.nanmax(error):.2e})')

    for a in ax: a.axis('off')
    plt.colorbar(im0, ax=ax[0], fraction=0.046)
    plt.colorbar(im1, ax=ax[1], fraction=0.046)
    plt.colorbar(im2, ax=ax[2], fraction=0.046)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIR, f'epoch_{epoch}_{target_filename}.png'))
    plt.close()


def main():
    seed_everything(42)
    print(f"PyTorch {torch.__version__} | 设备: {DEVICE}")
    
    dataset = PressureDeltaDataset(CSV_DIR)

    val_size = int(len(dataset) * VALID_SPLIT)
    train_size = len(dataset) - val_size
    train_set, val_set = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, drop_last=True)
    val_loader   = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # ================== 模型调用 ==================
    model = ModifiedUNet(in_channels=6, out_channels=1, base=32).to(DEVICE)

    # 损失函数使用 Huber Loss
    criterion = nn.SmoothL1Loss(reduction='sum')
    
    # 优化器采用 AdamW (配合 weight_decay=1e-4)
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    
    # 学习率策略改为余弦退火
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    best_val_loss = float('inf')
    loss_hist_train, loss_hist_val = [], []

    delta_mean = dataset.delta_mean
    delta_std  = dataset.delta_std

    start_time = time.time()
    for epoch in range(1, EPOCHS + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion)
        val_loss = validate(model, val_loader, criterion)
        
        # CosineAnnealingLR 直接 step() 即可
        scheduler.step()
        
        current_lr = optimizer.param_groups[0]['lr']

        loss_hist_train.append(train_loss)
        loss_hist_val.append(val_loss)

        print(f"Epoch {epoch:3d}/{EPOCHS} | LR: {current_lr:.2e} | Train Loss: {train_loss:.6e} | Val Loss: {val_loss:.6e}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), MODEL_PATH)

        if epoch % 100 == 0:
            plot_predictions_fixed_file(model, dataset, delta_mean, delta_std, epoch, DEVICE, FIXED_VIS_FILE)

        if epoch % 100 == 0:
            save_path = os.path.join(RESULT_DIR, f"model_epoch_{epoch}.pth")
            torch.save(model.state_dict(), save_path)

    print(f"训练完成！耗时: {(time.time() - start_time) / 60:.2f} min. 最佳验证损失: {best_val_loss:.6e}")

    # 绘制损失曲线
    plt.figure()
    plt.plot(loss_hist_train, label='Train Loss')
    plt.plot(loss_hist_val, label='Val Loss')
    plt.yscale('log')
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend()
    plt.title('Training and Validation Loss (ΔP)')
    plt.savefig(os.path.join(RESULT_DIR, 'loss_curve.png'))
    plt.close()

if __name__ == "__main__":
    main()