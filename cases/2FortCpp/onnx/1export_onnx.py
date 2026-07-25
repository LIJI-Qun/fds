# export_onnx.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import os

# 导入训练所用的网络结构
from unet_model_pressure import ModifiedUNet

# ================== 1. 工业 ONNX 端到端引擎 ==================
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
        # 此时 x_phys 维度: (Batch, 6, 20, 20)
        p_old_raw = x_phys[:, 5:6, :, :]
        
        # 2. 严格对齐训练：先对 20x20 的输入进行全局标准化
        # 对应训练脚本：inputs = (inputs - self.input_mean) / (self.input_std + 1e-8)
        x_norm_20 = (x_phys - self.f_mean) / self.f_std
        
        # 3. 第二步，对标准化后的特征进行 Padding (20 -> 24)
        # 对应训练脚本：inputs = F.pad(inputs, PAD_DIMS, mode='replicate')
        x_pad_24 = F.pad(x_norm_20, (2, 2, 2, 2), mode='replicate')
        
        # 4. UNet 核心网络推理
        delta_norm = self.unet(x_pad_24)
        
        # 5. 反标准化 (将网络输出恢复为真实的压力增量 ΔP)
        delta_phys = delta_norm * self.d_std + self.d_mean
        
        # 6. 裁剪多余 Padding (24 -> 20) 并加回绝对 P_old
        delta_cropped = delta_phys[:, :, 2:-2, 2:-2]  
        p_new = p_old_raw + delta_cropped                
        
        return p_new

# ================== 2. 执行导出过程 ==================
if __name__ == "__main__":
    print("开始导出 ONNX 模型，与训练流 100% 对齐...")
    device = torch.device("cpu")
    
    # 读取最新缓存
    stats = np.load("delta_stats_cache_20x20.npz")
    feat_mean, feat_std = stats['feat_mean'], stats['feat_std']
    delta_mean, delta_std = stats['delta_mean'], stats['delta_std']
    
    # 防止除零保护 (对应训练脚本中的 + 1e-8)
    feat_std = np.clip(feat_std, a_min=1e-8, a_max=None)
    delta_std = np.clip(delta_std, a_min=1e-8, a_max=None)
    
    # ================= 核心修改区域 =================
    # 1. 强制指定 base=32 匹配你当前的 UNet 架构
    core_model = ModifiedUNet(in_channels=6, out_channels=1, base=32).to(device)
    
    # 2. 确保这里填写的 .pth 文件名是你用当前带 BN 的 base=32 模型训练出来的最新权重！
    # (请根据你实际生成的权重文件名进行修改)
    model_weight_path = "best_pressure_delta_base24_bn.pth"  
    core_model.load_state_dict(torch.load(model_weight_path, map_location=device))
    # ===================================================
    
    # 组装端到端模型
    full_model = EndToEndONNXModel(core_model, feat_mean, feat_std, delta_mean, delta_std)
    
    # 加入了 BatchNorm 层，如果不加 eval()，ONNX 导出时会保留 BN 的训练图（计算当前 batch 的均值方差），导致 CFD 预测彻底崩溃！
    full_model.eval() 
    
    # 制造一个真实的 20x20 假数据用于追踪计算图
    dummy_input = torch.randn(1, 6, 20, 20, dtype=torch.float32)
    
    # 核心：导出为 ONNX 格式，开启常量折叠极致优化
    torch.onnx.export(
        full_model, 
        dummy_input, 
        "unet_cfd_engine.onnx",
        export_params=True,
        opset_version=14,            
        do_constant_folding=True,    
        input_names=['input_mesh'],
        output_names=['p_new']
    )
    print("✅ 成功！高度对齐的 ONNX 引擎文件已生成：unet_cfd_engine.onnx")