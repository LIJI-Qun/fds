# cnn1pythonRPred_cavity.py
import sys, os
import numpy as np
import torch
import torch.nn.functional as F

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from unet_model_pressure import ModifiedUNet, StandardUNet

# ================== 配置（与训练对齐） ==================
# 训练时保存的权重
MODEL_PATH = os.path.join(SCRIPT_DIR, "best_pressure_delta.pth")
# 训练时生成的增量统计量文件
STATS_PATH = os.path.join(SCRIPT_DIR, "delta_stats_cache_20x20.npz")
# 下采样次数（ModifiedUNet 有 3 次下采样，需保证尺寸能被 2^3=8 整除）
DOWNSAMPLE_FACTOR = 8

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None
# 特征统计量：(6,1,1)
feat_mean = None
feat_std = None
# 增量统计量：(1,1,1)
delta_mean = None
delta_std = None

def init_model():
    global model, feat_mean, feat_std, delta_mean, delta_std
    print("[Python] 初始化方腔压力 CNN 模型（ΔP预测）...", flush=True)

    if not os.path.exists(STATS_PATH):
        raise FileNotFoundError(f"找不到统计文件：{STATS_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"找不到模型权重：{MODEL_PATH}")

    try:
        # 加载统计量（与训练时 PressureDeltaDataset._compute_stats 保存格式一致）
        stats = np.load(STATS_PATH)
        feat_mean = torch.from_numpy(stats['feat_mean']).float().to(device)   # (6,1,1)
        feat_std  = torch.from_numpy(stats['feat_std']).float().to(device)
        delta_mean = torch.from_numpy(stats['delta_mean']).float().to(device) # (1,1,1)
        delta_std  = torch.from_numpy(stats['delta_std']).float().to(device)
        # 防止除零
        feat_std = torch.clamp(feat_std, min=1e-8)
        delta_std = torch.clamp(delta_std, min=1e-8)
        print(f"[Python] 统计量加载成功。特征均值范围: {feat_mean.min().item():.4f} ~ {feat_mean.max().item():.4f}", flush=True)

        # 加载模型（默认使用 ModifiedUNet，与训练默认一致）
        model = ModifiedUNet(in_channels=6, out_channels=1).to(device)
        # 若训练时使用了 StandardUNet，请取消下一行注释并注释上一行：
        # model = StandardUNet(in_channels=6, out_channels=1).to(device)

        state_dict = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict)
        model.eval()
        print(f"[Python] 模型加载成功，设备: {device}", flush=True)

    except Exception as e:
        print(f"[Python ERROR] 初始化失败: {e}", flush=True)
        sys.exit(1)

def predict_pressure(input_array):
    """
    预测物理压力 P_new

    参数:
        input_array: np.ndarray, shape (B, 6, H, W)
                     通道顺序：X, Y, Z, Div, RHS, P_old
                     所有通道均已为物理量（未归一化）
    返回:
        np.ndarray, shape (B, 1, H, W)
            预测的 P_new (Pa)，同一物理网格
    """
    global model, feat_mean, feat_std, delta_mean, delta_std

    # 基本检查
    if not isinstance(input_array, np.ndarray):
        raise TypeError("输入必须是 numpy 数组")
    if input_array.dtype != np.float32:
        input_array = input_array.astype(np.float32)
    if input_array.ndim != 4:
        raise ValueError(f"输入需为 4 维 (B,C,H,W)，实际 {input_array.ndim} 维")

    B, C, H, W = input_array.shape
    if C != 6:
        raise ValueError(f"通道数应为 6，实际 {C}")

    # 清洗非法值
    if np.any(np.isnan(input_array)) or np.any(np.isinf(input_array)):
        print("[Python WARNING] 输入含 NaN/Inf，已替换为 0", flush=True)
        input_array = np.nan_to_num(input_array, nan=0.0, posinf=1e10, neginf=-1e10)

    try:
        # 转换为 torch tensor
        x = torch.from_numpy(input_array).to(device)   # (B,6,H,W)

        # 1. 计算保证下采样倍数所需的 padding
        pad_h = (DOWNSAMPLE_FACTOR - H % DOWNSAMPLE_FACTOR) % DOWNSAMPLE_FACTOR
        pad_w = (DOWNSAMPLE_FACTOR - W % DOWNSAMPLE_FACTOR) % DOWNSAMPLE_FACTOR
        # 两侧均匀分配，若不对称则左侧多补
        pad_top = pad_h // 2
        pad_bottom = pad_h - pad_top
        pad_left = pad_w // 2
        pad_right = pad_w - pad_left

        if pad_h > 0 or pad_w > 0:
            # 使用 replicate 模式，与训练一致
            x = F.pad(x, (pad_left, pad_right, pad_top, pad_bottom), mode='replicate')
            pad_applied = True
        else:
            pad_applied = False

        _, _, H_pad, W_pad = x.shape

        # 2. 输入标准化（6个特征通道分别减去均值除以标准差）
        x = (x - feat_mean) / feat_std

        # 3. 模型前向 → 预测归一化后的增量 ΔP_norm
        with torch.no_grad():
            delta_norm = model(x)   # (B, 1, H_pad, W_pad)

        # 4. 反归一化得到物理增量 ΔP
        delta = delta_norm * delta_std + delta_mean   # (B, 1, H_pad, W_pad)

        # 5. 从输入中取 P_old 通道（索引5），加上增量得到 P_new
        #    注意：输入的 P_old 通道也已被标准化，不能直接用；应使用原始物理量。
        #    我们保留原始输入数组用于提取 P_old。
        p_old_orig = input_array[:, 5:6, :, :].copy()   # (B,1,H,W) 物理值
        p_old_tensor = torch.from_numpy(p_old_orig).to(device)
        # 对 P_old 施加相同的 padding
        if pad_applied:
            p_old_tensor = F.pad(p_old_tensor, (pad_left, pad_right, pad_top, pad_bottom), mode='replicate')

        p_new = p_old_tensor + delta

        # 6. 裁剪回原始尺寸
        if pad_applied:
            p_new = p_new[:, :, pad_top:pad_top+H, pad_left:pad_left+W]

        result = p_new.cpu().numpy().copy()
        return result

    except Exception as e:
        print(f"[Python ERROR] 预测失败: {e}", flush=True)
        # 降级方案：直接返回 P_old
        fallback = input_array[:, 5:6, :, :].copy()
        return fallback

# 自动初始化
init_model()