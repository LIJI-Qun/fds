# cnn1pythonRPred.py
import sys, os
import numpy as np
import torch
import torch.nn.functional as F

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from unet_model_pressure1 import StandardUNet

# ---- 方腔专用参数 ----
MODEL_PATH = os.path.join(SCRIPT_DIR, "best_pressure_unet.pth")

# 统计量文件放在训练数据目录下，请根据实际情况调整
# CSV_DIR 与脚本同级的 dateT130Ccnn 文件夹
CSV_DIR = os.path.join(SCRIPT_DIR, "dateT130Ccnn")
INPUT_STATS_PATH  = os.path.join(CSV_DIR, "input_stats.npy")   # (2,6,1,1): [mean, std]
DELTA_STATS_PATH  = os.path.join(CSV_DIR, "delta_stats.npy")   # (2,1,1,1): [mean, std]

# =====================================================
# 1. 匹配训练代码的尺寸
# =====================================================
ORIG_H, ORIG_W = 20, 20      # 对应训练代码的 I_MAX = 20, K_MAX = 20
TRAIN_H, TRAIN_W = 32, 32    # 对应 PAD_DIMS = (6, 6, 6, 6) 后的尺寸
PAD = 6

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None
input_mean = None
input_std  = None
delta_mean = None   # ΔP 的均值（标量）
delta_std  = None   # ΔP 的标准差（标量）

def init_model():
    global model, input_mean, input_std, delta_mean, delta_std
    print("[Python] 初始化方腔压力 CNN 模型...", flush=True)

    if not os.path.exists(INPUT_STATS_PATH):
        raise FileNotFoundError(f"找不到输入统计文件：{INPUT_STATS_PATH}")
    if not os.path.exists(DELTA_STATS_PATH):
        raise FileNotFoundError(f"找不到 ΔP 统计文件：{DELTA_STATS_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"找不到模型权重：{MODEL_PATH}")

    try:
        # 加载输入特征的统计量 (6 通道)
        input_stats = np.load(INPUT_STATS_PATH)          # shape (2, 6, 1, 1)
        input_mean = torch.from_numpy(input_stats[0]).float().to(device)   # (6,1,1)
        input_std  = torch.from_numpy(input_stats[1]).float().to(device)
        
        # =====================================================
        # 2. 移除 clamp，采用与训练代码严格一致的 + 1e-8 逻辑
        # =====================================================
        # (已在 predict_from_array 中处理，此处无需额外操作)

        # 加载 ΔP 的统计量 (标量形式保存为 (2,1,1,1))
        delta_stats = np.load(DELTA_STATS_PATH)          # shape (2, 1, 1, 1)
        delta_mean = delta_stats[0].item()               # 标量
        delta_std  = delta_stats[1].item()
        print(f"[Python] ΔP 反归一化参数: mean={delta_mean:.4e}, std={delta_std:.4e}", flush=True)

        # 加载模型
        model = StandardUNet(in_channels=6, out_channels=1).to(device)
        state_dict = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict)
        model.eval()
        print(f"[Python] 模型加载成功，设备: {device}", flush=True)

    except Exception as e:
        print(f"[Python ERROR] 初始化失败: {e}", flush=True)
        sys.exit(1)

init_model()


def predict_from_array(input_array):
    """
    参数:
        input_array: ndarray (B, 6, H, W), 其中通道顺序为 X, Y, Z, Div, RHS, P_old
    返回:
        ndarray (B, 1, H, W) 物理绝对压力 P_new (Pa)
        注意：本函数内部已自动加上 P_old，调用方无需再手动相加。
    """
    global model, input_mean, input_std, delta_mean, delta_std

    # 输入检验
    if not isinstance(input_array, np.ndarray):
        raise TypeError("输入必须是 numpy 数组")
    if input_array.dtype != np.float32:
        input_array = input_array.astype(np.float32)
    if input_array.ndim != 4:
        raise ValueError(f"输入需为4维(B,C,H,W)，实际 {input_array.ndim} 维")

    B, C, H, W = input_array.shape
    if C != 6:
        raise ValueError(f"通道数应为6，实际 {C}")

    # 清除非法值
    if np.any(np.isnan(input_array)) or np.any(np.isinf(input_array)):
        print("[Python WARNING] 输入含 NaN/Inf，已清洗", flush=True)
        input_array = np.nan_to_num(input_array, nan=0.0, posinf=1e10, neginf=-1e10)

    # ---------- 备份旧压力（物理量） ----------
    p_old_phys = input_array[:, 5:6, :, :].copy()   # 形状 (B,1,H,W)

    try:
        inputs = torch.from_numpy(input_array).to(device)

        with torch.no_grad():
            # 标准化：与训练完全一致
            inputs = (inputs - input_mean) / (input_std + 1e-8)

            # 处理 padding
            pad_applied = False
            if H == ORIG_H and W == ORIG_W:
                inputs = F.pad(inputs, (PAD, PAD, PAD, PAD), mode='constant', value=0.0)
                pad_applied = True
            elif H == TRAIN_H and W == TRAIN_W:
                pad_applied = False
            else:
                raise ValueError(f"不支持的输入尺寸 {H}x{W}")

            # 模型前向 → 输出归一化后的 ΔP
            outputs = model(inputs)   # (B, 1, 32, 32) 或 (B, 1, H, W)

            # 反归一化到物理 ΔP
            outputs = outputs * (delta_std) + delta_mean

            # 裁剪回原始尺寸
            if pad_applied:
                outputs = outputs[:, :, PAD:-PAD, PAD:-PAD]   # 恢复为 (B,1,H,W)

            # ---------- 核心修改：加上旧压力，得到绝对压力 ----------
            p_old_tensor = torch.from_numpy(p_old_phys).to(device)
            outputs = outputs + p_old_tensor

        result = outputs.cpu().numpy().copy()
        return result

    except Exception as e:
        print(f"[Python ERROR] 预测失败: {e}", flush=True)
        # 安全回退：返回全零压力（可能导致发散，但已打印错误）
        return np.zeros((B, 1, H, W), dtype=np.float32)

