# unet_model_pressure.py
import torch
import torch.nn as nn
import torch.nn.functional as F

# =====================================================================
#                     U-Net (ResidualBlock + BN + GELU)
# =====================================================================
class ResidualBlockBN(nn.Module):
    """带残差连接和 Batch Normalization 的双卷积块"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        # 紧跟 BN 层时，卷积层的 bias 必须设为 False 以节省内存并避免计算冲突
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.act = nn.GELU()
        
        # 如果输入输出通道数不同，用 1x1 卷积调整维度 (同样加 BN 和无 bias)
        if in_channels != out_channels:
            self.skip = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.skip = nn.Identity()

    def forward(self, x):
        identity = self.skip(x)
        
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.act(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        
        out = out + identity          # 残差相加
        out = self.act(out)
        return out

class ModifiedUNet(nn.Module):
    """简单且强大的 U-Net 架构，使用残差块 + BN + GELU"""
    # 默认参数已修改为与当前 CFD 数据流严格一致 (6通道输入, base=32)
    def __init__(self, in_channels=6, out_channels=1, base=32):
        super().__init__()
        # ================= 编码器 =================
        self.enc1 = ResidualBlockBN(in_channels, base)
        self.enc2 = ResidualBlockBN(base, base*2)
        self.enc3 = ResidualBlockBN(base*2, base*4)
        self.pool = nn.MaxPool2d(2, 2)

        # ================= 瓶颈层 =================
        self.bottleneck = ResidualBlockBN(base*4, base*8)

        # ================= 解码器 =================
        # 阶段 3
        self.up3 = nn.ConvTranspose2d(base*8, base*4, kernel_size=2, stride=2)
        self.dec3 = ResidualBlockBN(base*8, base*4) # 拼接后通道数为 base*4 + base*4 = base*8
        
        # 阶段 2
        self.up2 = nn.ConvTranspose2d(base*4, base*2, kernel_size=2, stride=2)
        self.dec2 = ResidualBlockBN(base*4, base*2) # 拼接后通道数为 base*2 + base*2 = base*4
        
        # 阶段 1
        self.up1 = nn.ConvTranspose2d(base*2, base, kernel_size=2, stride=2)
        self.dec1 = ResidualBlockBN(base*2, base)   # 拼接后通道数为 base + base = base*2

        # ================= 输出层 =================
        self.out_conv = nn.Conv2d(base, out_channels, kernel_size=1)

    def forward(self, x):
        # 编码
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        
        # 瓶颈
        b = self.bottleneck(self.pool(e3))
        
        # 解码与跳跃连接
        d3 = self.up3(b)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)
        
        d2 = self.up2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)
        
        d1 = self.up1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)
        
        # 输出
        return self.out_conv(d1)