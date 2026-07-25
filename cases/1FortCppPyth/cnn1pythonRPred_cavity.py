# cnn1pythonRPred_cavity.py
import sys, os
import time
import numpy as np
import torch
import torch.nn.functional as F

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from unet_model_pressure import ModifiedUNet   # 仅导入实际使用的模型

# ================== 配置 ==================
MODEL_PATH = os.path.join(SCRIPT_DIR, "best_pressure_delta_base24_bn.pth")
STATS_PATH = os.path.join(SCRIPT_DIR, "delta_stats_cache_20x20.npz")
DOWNSAMPLE_FACTOR = 8

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None
feat_mean = None
feat_std = None
delta_mean = None
delta_std = None

# ================== 性能统计 ==================
_timings = {
    'type_check': [],
    'nan_check': [],
    'to_tensor': [],
    'extract_p_old': [],
    'normalize': [],
    'pad': [],
    'model_forward': [],
    'denormalize': [],
    'crop_delta': [],
    'add': [],
    'to_numpy': [],
    'total': []
}
_call_count = 0
_PRINT_EVERY = 2000

def _print_stage_stats(call_id):
    """输出最近 PRINT_EVERY 次调用的各步骤耗时统计"""
    n = min(_PRINT_EVERY, len(_timings['total']))
    start_idx = len(_timings['total']) - n
    total_vals = _timings['total'][start_idx:]
    total_sum = np.sum(total_vals)
    total_avg = np.mean(total_vals)

    print(f"\n[Python Timing] 预测 #{call_id-n+1} ～ #{call_id} 统计 (共 {n} 次, 单位: ms)", flush=True)
    print(f"{'步骤':20s} {'总耗时':>9s}  {'均值':>9s}  {'占比':>6s}", flush=True)
    print("-" * 50, flush=True)

    for key in _timings:
        if key == 'total':
            continue
        vals = _timings[key][start_idx:]
        s = np.sum(vals)
        avg = np.mean(vals)
        pct = (avg / total_avg * 100) if total_avg > 0 else 0
        print(f"{key:20s}: {s:8.3f}  {avg:8.4f}  ({pct:5.1f}%)", flush=True)

    print("-" * 50, flush=True)
    print(f"{'TOTAL':20s}: {total_sum:8.3f}  {total_avg:8.4f}", flush=True)

def print_summary():
    """供 C++ 在模拟结束时调用的外部接口，输出完整累积统计"""
    n = len(_timings['total'])
    if n == 0:
        return
    total_avg = np.mean(_timings['total'])
    print(f"\n==== Python 最终耗时统计 (总调用次数: {n}, 单位: ms) ====", flush=True)
    print(f"{'步骤':20s} {'均值':>8s}  {'最小值':>8s}   {'占比':>6s}", flush=True)
    print("-" * 60, flush=True)
    for key in _timings:
        if key == 'total':
            continue
        vals = np.array(_timings[key])
        avg = np.mean(vals)
        _min = np.min(vals)
        pct = (avg / total_avg * 100) if total_avg > 0 else 0
        print(f"{key:20s}: {avg:8.4f}  {_min:8.4f}   ({pct:5.1f}%)", flush=True)
    print("-" * 60, flush=True)
    print(f"{'TOTAL':20s}: {total_avg:8.4f}  {np.min(_timings['total']):8.4f} ", flush=True)
    print("=" * 60, flush=True)

def init_model():
    global model, feat_mean, feat_std, delta_mean, delta_std
    print("[Python] 初始化方腔压力 CNN 模型（ΔP预测）...", flush=True)

    if not os.path.exists(STATS_PATH):
        raise FileNotFoundError(f"找不到统计文件：{STATS_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"找不到模型权重：{MODEL_PATH}")

    try:
        stats = np.load(STATS_PATH)
        feat_mean = torch.from_numpy(stats['feat_mean']).float().to(device)
        feat_std  = torch.from_numpy(stats['feat_std']).float().to(device)
        delta_mean = torch.from_numpy(stats['delta_mean']).float().to(device)
        delta_std  = torch.from_numpy(stats['delta_std']).float().to(device)
        feat_std = torch.clamp(feat_std, min=1e-8)
        delta_std = torch.clamp(delta_std, min=1e-8)
        print(f"[Python] 统计量加载成功。特征均值范围: {feat_mean.min().item():.4f} ~ {feat_mean.max().item():.4f}", flush=True)

        model = ModifiedUNet(in_channels=6, out_channels=1, base=32).to(device)
        state_dict = torch.load(MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict)
        model.eval()
        print(f"[Python] 模型加载成功，设备: {device}", flush=True)

    except Exception as e:
        print(f"[Python ERROR] 初始化失败: {e}", flush=True)
        sys.exit(1)


def predict_pressure(input_array):
    global model, feat_mean, feat_std, delta_mean, delta_std, _call_count

    #如果模型未加载，自动调用 init_model()
    if model is None:
        init_model()

    _call_count += 1
    t_total_start = time.perf_counter()

    # ---- 1. 类型与维度检查 ----
    t0 = time.perf_counter()
    if not isinstance(input_array, np.ndarray):
        raise TypeError("输入必须是 numpy 数组")
    if input_array.dtype != np.float32:
        input_array = input_array.astype(np.float32)
    if input_array.ndim != 4:
        raise ValueError(f"输入需为 4 维 (B,C,H,W)，实际 {input_array.ndim} 维")
    B, C, H, W = input_array.shape
    if C != 6:
        raise ValueError(f"通道数应为 6，实际 {C}")
    t1 = time.perf_counter()
    _timings['type_check'].append((t1 - t0) * 1000)

    # ---- 2. NaN/Inf 清洗 ----
    t0 = time.perf_counter()
    if np.any(np.isnan(input_array)) or np.any(np.isinf(input_array)):
        print("[Python WARNING] 输入含 NaN/Inf，已替换为 0", flush=True)
        input_array = np.nan_to_num(input_array, nan=0.0, posinf=1e10, neginf=-1e10)
    t1 = time.perf_counter()
    _timings['nan_check'].append((t1 - t0) * 1000)

    try:
        # ---- 3. numpy -> torch ----
        t0 = time.perf_counter()
        x = torch.from_numpy(input_array).to(device)
        t1 = time.perf_counter()
        _timings['to_tensor'].append((t1 - t0) * 1000)

        # ---- 4. 提取 P_old ----
        t0 = time.perf_counter()
        p_old_tensor = x[:, 5:6, :, :].clone()
        t1 = time.perf_counter()
        _timings['extract_p_old'].append((t1 - t0) * 1000)

        # ---- 5. 计算 padding 尺寸 ----
        pad_h = (DOWNSAMPLE_FACTOR - H % DOWNSAMPLE_FACTOR) % DOWNSAMPLE_FACTOR
        pad_w = (DOWNSAMPLE_FACTOR - W % DOWNSAMPLE_FACTOR) % DOWNSAMPLE_FACTOR
        pad_top = pad_h // 2
        pad_bottom = pad_h - pad_top
        pad_left = pad_w // 2
        pad_right = pad_w - pad_left
        pad_applied = (pad_h > 0 or pad_w > 0)

        # ---- 6. 标准化 ----
        t0 = time.perf_counter()
        x = (x - feat_mean) / feat_std
        t1 = time.perf_counter()
        _timings['normalize'].append((t1 - t0) * 1000)

        # ---- 7. padding ----
        t0 = time.perf_counter()
        if pad_applied:
            x = F.pad(x, (pad_left, pad_right, pad_top, pad_bottom), mode='replicate')
        t1 = time.perf_counter()
        _timings['pad'].append((t1 - t0) * 1000)

        # ---- 8. 模型推理 ----
        t0 = time.perf_counter()
        with torch.no_grad():
            delta_norm = model(x)
        t1 = time.perf_counter()
        _timings['model_forward'].append((t1 - t0) * 1000)

        # ---- 9. 反归一化 ----
        t0 = time.perf_counter()
        delta = delta_norm * delta_std + delta_mean
        t1 = time.perf_counter()
        _timings['denormalize'].append((t1 - t0) * 1000)

        # ---- 10. 裁剪回原尺寸 ----
        t0 = time.perf_counter()
        if pad_applied:
            delta = delta[:, :, pad_top:pad_top+H, pad_left:pad_left+W]
        t1 = time.perf_counter()
        _timings['crop_delta'].append((t1 - t0) * 1000)

        # ---- 11. P_new = P_old + ΔP ----
        t0 = time.perf_counter()
        p_new = p_old_tensor + delta 
        t1 = time.perf_counter()
        _timings['add'].append((t1 - t0) * 1000)

        # ---- 12. 转 numpy ----
        t0 = time.perf_counter()
        result = p_new.cpu().numpy()
        #result = delta.cpu().numpy()     # 直接回传微小的增量 delta
        t1 = time.perf_counter()
        _timings['to_numpy'].append((t1 - t0) * 1000)

        t_total_end = time.perf_counter()
        _timings['total'].append((t_total_end - t_total_start) * 1000)

        if _call_count % _PRINT_EVERY == 0:
            _print_stage_stats(_call_count)

        return result

    except Exception as e:
        print(f"[Python ERROR] 预测失败: {e}", flush=True)
        return input_array[:, 5:6, :, :].copy()

