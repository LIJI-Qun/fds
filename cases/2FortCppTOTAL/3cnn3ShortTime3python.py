# 3cnn3ShortTime3python.py
import numpy as np

def export_stats(npz_path, name_prefix):
    data = np.load(npz_path)
    feat_mean = data['feat_mean'].flatten()   # length 6
    feat_std  = data['feat_std'].flatten()
    delta_mean = data['delta_mean'].item()
    delta_std  = data['delta_std'].item()
    
    print(f"// {name_prefix} 统计量")
    print(f"static const float {name_prefix}_feat_mean[6] = {{{', '.join(f'{v:.8f}f' for v in feat_mean)}}};")
    print(f"static const float {name_prefix}_feat_std[6]  = {{{', '.join(f'{v:.8f}f' for v in feat_std)}}};")
    print(f"static const float {name_prefix}_delta_mean = {delta_mean:.8f}f;")
    print(f"static const float {name_prefix}_delta_std  = {delta_std:.8f}f;")
    print()

export_stats("delta_stats_cache_20x20.npz", "STATS20")
export_stats("delta_stats_cache_40x40.npz", "STATS40")