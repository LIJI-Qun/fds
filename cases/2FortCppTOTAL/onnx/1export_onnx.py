# export_onnx.py
# ============================================================================
# 40x40 网格版 ONNX 导出脚本
# 严格对齐 train_PT040Cmesh2.py 的数据流
#
# 关键对齐点（与训练脚本 train_PT040Cmesh2.py 逐项核对）：
#   1. 网格尺寸:   I_MAX=K_MAX=40
#   2. Padding:    PAD_DIMS=(4,4,4,4) → 40→48 (48 能被 8 整除，满足 UNet 3 次下采样)
#   3. Crop:       4:-4 → 48→40 (与 padding 对称)
#   4. 标准化:     (inputs - mean) / (std + 1e-8)  ← 标准化在 padding 之前
#   5. 反标准化:   delta * std + mean
#   6. 残差相加:   P_new = P_old + ΔP
#   7. 统计量:     delta_stats_cache_40x40.npz
#   8. 权重:       best_pressure_delta_40x40_base24.pth
#   9. 模型:       ModifiedUNet(in_channels=6, out_channels=1, base=32)
# ============================================================================
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import os

# 导入训练所用的网络结构
from unet_model_pressure import ModifiedUNet

# ================== 配置（与 train_PT040Cmesh2.py 100% 对齐）==================
GRID_SIZE = 40          # I_MAX = K_MAX = 40
PAD = 4                 # PAD_DIMS = (4,4,4,4)，每侧补 4，40→48

# 统计量文件搜索路径
# 训练脚本和 compute_stats_40x40.py 都把缓存存在 CSV 目录下
CSV_DIR = "./dataT40C"
STATS_FILE_CANDIDATES = [
    "delta_stats_cache_40x40.npz",                        # 当前目录
    os.path.join(CSV_DIR, "delta_stats_cache_40x40.npz"), # CSV 数据目录
]

MODEL_WEIGHT = "best_pressure_delta_40x40_base24.pth"
OUTPUT_ONNX = "unet_cfd_engine.onnx"


def find_stats_file():
    """在候选路径中搜索统计量文件"""
    for path in STATS_FILE_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# ================== 端到端 ONNX 模型 ==================
# 将所有数据预处理（标准化、Padding）和后处理（反标准化、裁剪、加回原压力）
# 全部打包进计算图，C++ 侧无需重复任何操作
class EndToEndONNXModel(nn.Module):
    def __init__(self, core_unet, feat_mean, feat_std, delta_mean, delta_std):
        super().__init__()
        self.unet = core_unet

        # 将统计量注册为 Buffer，这样它们会被固化在 ONNX 模型内部
        self.register_buffer('f_mean', torch.from_numpy(feat_mean).float())
        self.register_buffer('f_std', torch.from_numpy(feat_std).float())
        self.register_buffer('d_mean', torch.from_numpy(delta_mean).float())
        self.register_buffer('d_std', torch.from_numpy(delta_std).float())

    def forward(self, x_phys):
        # 1. 提取原始绝对压力 P_old (用于最后残差相加计算 P_new)
        # 此时 x_phys 维度: (Batch, 6, 40, 40)
        p_old_raw = x_phys[:, 5:6, :, :]

        # 2. 严格对齐训练：先对 40x40 的输入进行全局标准化
        #    对应训练脚本：inputs = (inputs - self.input_mean) / (self.input_std + 1e-8)
        #    注意：标准化必须在 padding 之前，与训练脚本顺序一致
        x_norm = (x_phys - self.f_mean) / self.f_std

        # 3. 对标准化后的特征进行 replicate Padding (40 -> 48)
        #    对应训练脚本：PAD_DIMS = (4, 4, 4, 4)
        #    训练代码用 unsqueeze(0)+squeeze(0) 保证 replicate 在 4D 下工作
        #    ONNX 导出时 x_norm 已经是 4D (B,C,H,W)，直接 pad 即可
        #    48 能被 8 整除 (48/8=6)，满足 UNet 3 次下采样要求
        x_pad = F.pad(x_norm, (PAD, PAD, PAD, PAD), mode='replicate')

        # 4. UNet 核心网络推理
        delta_norm = self.unet(x_pad)

        # 5. 反标准化 (将网络输出恢复为真实的压力增量 ΔP)
        delta_phys = delta_norm * self.d_std + self.d_mean

        # 6. 裁剪多余 Padding (48 -> 40) 并加回绝对 P_old
        #    训练时 pad 了 4，所以这里 crop 4:-4
        delta_cropped = delta_phys[:, :, PAD:-PAD, PAD:-PAD]
        p_new = p_old_raw + delta_cropped

        return p_new

# ================== 2. 执行导出过程 ==================
if __name__ == "__main__":
    print("开始导出 40x40 ONNX 模型，与 train_PT040Cmesh2.py 100% 对齐...")
    device = torch.device("cpu")

    # 1. 读取 40x40 统计量（自动搜索当前目录和 CSV 目录）
    stats_path = find_stats_file()
    if stats_path is None:
        raise FileNotFoundError(
            f"找不到统计量文件：delta_stats_cache_40x40.npz\n"
            f"已搜索以下路径：{STATS_FILE_CANDIDATES}\n"
            f"请先运行 train_PT040Cmesh2.py 生成统计量，"
            f"或运行 compute_stats_40x40.py 单独计算。"
        )
    print(f"加载统计量：{stats_path}")
    stats = np.load(stats_path)
    feat_mean, feat_std = stats['feat_mean'], stats['feat_std']
    delta_mean, delta_std = stats['delta_mean'], stats['delta_std']

    # 防止除零保护 (对应训练脚本中的 + 1e-8)
    # np.clip(std, min=1e-8) 与训练中 /(std + 1e-8) 数学等价
    feat_std = np.clip(feat_std, a_min=1e-8, a_max=None)
    delta_std = np.clip(delta_std, a_min=1e-8, a_max=None)

    # 2. 加载 40x40 训练的权重
    if not os.path.exists(MODEL_WEIGHT):
        raise FileNotFoundError(
            f"找不到模型权重：{MODEL_WEIGHT}\n"
            f"请先运行 train_PT040Cmesh2.py 完成训练。"
        )
    core_model = ModifiedUNet(in_channels=6, out_channels=1, base=32).to(device)
    core_model.load_state_dict(torch.load(MODEL_WEIGHT, map_location=device))

    # 组装端到端模型
    full_model = EndToEndONNXModel(core_model, feat_mean, feat_std, delta_mean, delta_std)

    # BatchNorm 层在 train 模式下会计算当前 batch 的均值方差，
    # eval() 模式下 BN 用 running_mean/running_var（训练时学到的固定统计量）
    full_model.eval()

    #3. 制造 40x40 假数据用于追踪计算图
    dummy_input = torch.randn(1, 6, GRID_SIZE, GRID_SIZE, dtype=torch.float32)

    #  4. 验证模型输出尺寸正确
    with torch.no_grad():
        test_output = full_model(dummy_input)
    print(f"输入尺寸: {dummy_input.shape}")
    print(f"输出尺寸: {test_output.shape}")
    assert test_output.shape == (1, 1, GRID_SIZE, GRID_SIZE), \
        f"输出尺寸错误！期望 (1,1,{GRID_SIZE},{GRID_SIZE})，实际 {test_output.shape}"
    print("尺寸验证通过！")

    # 5. 导出为 ONNX 格式，开启常量折叠极致优化
    torch.onnx.export(
        full_model,
        dummy_input,
        OUTPUT_ONNX,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input_mesh'],
        output_names=['p_new']
    )
    print(f" 成功！40x40 ONNX 引擎文件已生成：{OUTPUT_ONNX}")
    print(f"  1. 标准化 (feat_mean/std 来自 {os.path.basename(stats_path)})")
    print(f"  2. replicate padding ({PAD},{PAD},{PAD},{PAD}) → {GRID_SIZE+2*PAD}x{GRID_SIZE+2*PAD}")
    print(f"  4. crop {PAD}:-{PAD} → {GRID_SIZE}x{GRID_SIZE}")

