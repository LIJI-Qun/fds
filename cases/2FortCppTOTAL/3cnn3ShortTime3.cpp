// ======================================================================
// cnn3ShortTime3.cpp (纯 ONNX Runtime C++ 终极桥接版本)
//
// ★ 融合方案：双线性插值 + 统计量双向重映射
//   1. 解决空间分辨率不匹配（20x20 ↔ 40x40 插值）
//   2. 解决特征分布协变量偏移（20x20 ↔ 40x40 均值/方差映射）
//   3. 绕过 EndToEnd 模型的残差黑盒，提取出绝对准确的物理 P_new
// ======================================================================

#include <onnxruntime_cxx_api.h>
#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <algorithm>
#include <windows.h>

#ifdef _WIN32
    #define DLL_EXPORT __declspec(dllexport)
#else
    #define DLL_EXPORT
#endif

// ================== 配置 ==================
#define ORT_NUM_THREADS 4
#define MODEL_H 40
#define MODEL_W 40
#define MODEL_C 6

// ================== 统计量硬编码区域 ==================
// ！！！ 提取的 npz 真实数值填入此处 ！！！

// STATS20 统计量
static const float STATS20_feat_mean[6] = {0.00500000f, 0.00025000f, 0.00500000f, 0.00000000f, 0.00000001f, 0.00000000f};
static const float STATS20_feat_std[6]  = {0.00288314f, 0.00000000f, 0.00288314f, 0.01098418f, 80.46357727f, 0.00013410f};
static const float STATS20_delta_mean = 0.00000000f;
static const float STATS20_delta_std  = 0.00000000f;

// STATS40 统计量
static const float STATS40_feat_mean[6] = {0.00500000f, 0.00012500f, 0.00500000f, 0.00000000f, -0.00000003f, -0.00000000f};
static const float STATS40_feat_std[6]  = {0.00288585f, 0.00000000f, 0.00288585f, 0.01111327f, 115.88004303f, 0.00013599f};
static const float STATS40_delta_mean = 0.00000000f;
static const float STATS40_delta_std  = 0.00000000f;
// ======================================================

static Ort::Env* ort_env = nullptr;
static Ort::Session* ort_session = nullptr;
static Ort::MemoryInfo* memory_info = nullptr;

static bool is_initialized = false;
static bool bridge_mode_warned = false;
static uint64_t total_calls = 0;
static double total_ms_infer = 0.0;

// 预计算的映射系数
static float scale_feat[6];
static float bias_feat[6];
static float scale_delta_inv; // 用于反向解包
static float bias_delta_inv;

static void init_stats_mapping() {
    const float eps = 1e-8f;
    for (int c = 0; c < 6; c++) {
        float s20 = STATS20_feat_std[c];
        float s40 = STATS40_feat_std[c];
        if (s20 < eps || s40 < eps) {
            scale_feat[c] = 1.0f;
            bias_feat[c] = 0.0f;
            std::cout << "[C++] Feature channel " << c << " has near-zero std, skip mapping.\n";
        } else {
            scale_feat[c] = s40 / s20;
            bias_feat[c] = STATS40_feat_mean[c] - STATS20_feat_mean[c] * scale_feat[c];
        }
    }
    if (STATS20_delta_std < eps || STATS40_delta_std < eps) {
        scale_delta_inv = 1.0f;
        bias_delta_inv = 0.0f;
        std::cout << "[C++] Delta std too small, skip delta remapping.\n";
    } else {
        scale_delta_inv = STATS20_delta_std / STATS40_delta_std;
        bias_delta_inv = STATS20_delta_mean - STATS40_delta_mean * scale_delta_inv;
    }
}


// 辅助函数：双线性插值上采样
static void upsample_bilinear(const float* src, float* dst, int C, int H, int W) {
    for (int c = 0; c < C; c++) {
        const float* src_c = src + c * H * W;
        float* dst_c = dst + c * MODEL_H * MODEL_W;
        for (int mh = 0; mh < MODEL_H; mh++) {
            for (int mw = 0; mw < MODEL_W; mw++) {
                float h_orig = mh * (float)(H - 1) / (MODEL_H - 1);
                float w_orig = mw * (float)(W - 1) / (MODEL_W - 1);
                int h0 = (int)h_orig;
                int h1 = std::min(h0 + 1, H - 1);
                int w0 = (int)w_orig;
                int w1 = std::min(w0 + 1, W - 1);
                float h_diff = h_orig - h0;
                float w_diff = w_orig - w0;
                float p00 = src_c[h0 * W + w0];
                float p01 = src_c[h0 * W + w1];
                float p10 = src_c[h1 * W + w0];
                float p11 = src_c[h1 * W + w1];
                dst_c[mh * MODEL_W + mw] = p00 * (1.0f - h_diff) * (1.0f - w_diff) +
                                           p01 * (1.0f - h_diff) * w_diff +
                                           p10 * h_diff * (1.0f - w_diff) +
                                           p11 * h_diff * w_diff;
            }
        }
    }
}

// 辅助函数：平均池化下采样
static void downsample_avg(const float* src, float* dst, int H, int W) {
    int stride_h = MODEL_H / H; 
    int stride_w = MODEL_W / W;
    for (int h = 0; h < H; h++) {
        for (int w = 0; w < W; w++) {
            float sum = 0.0f;
            int count = 0;
            for (int i = 0; i < stride_h; i++) {
                for (int j = 0; j < stride_w; j++) {
                    int mh = h * stride_h + i;
                    int mw = w * stride_w + j;
                    if (mh < MODEL_H && mw < MODEL_W) {
                        sum += src[mh * MODEL_W + mw];
                        count++;
                    }
                }
            }
            dst[h * W + w] = sum / (float)count;
        }
    }
}

extern "C" {

DLL_EXPORT void cnn_initialize() {
    if (is_initialized) return;
    try {
        std::cout << "[C++] Initializing ONNX Runtime Engine..." << std::endl;
        ort_env = new Ort::Env(ORT_LOGGING_LEVEL_WARNING, "FDS_CNN");
        Ort::SessionOptions session_options;
        session_options.SetIntraOpNumThreads(ORT_NUM_THREADS);
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);

        #ifdef _WIN32
        const wchar_t* model_path = L"unet_cfd_engine.onnx";
        #else
        const char* model_path = "unet_cfd_engine.onnx";
        #endif

        ort_session = new Ort::Session(*ort_env, model_path, session_options);
        memory_info = new Ort::MemoryInfo(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault));

        init_stats_mapping(); // 初始化统计量映射系数
        is_initialized = true;

        std::cout << "[C++] ONNX Runtime Ready! (Threads=" << ORT_NUM_THREADS << ")\n";
        std::cout << "[C++] *** ULTIMATE BRIDGE v4.0 (Interpolation + Stats Remap) ***\n";

    } catch (const Ort::Exception& e) {
        std::cerr << "[C++ ERROR] ONNX Init Failed: " << e.what() << std::endl;
        #ifdef _WIN32
        MessageBoxA(NULL, e.what(), "ONNX Init Error", MB_ICONERROR);
        #endif
    }
}

DLL_EXPORT void cnn_predict(float *in, float *out, int B, int C, int H, int W, int rank) {
    if (!is_initialized) {
        cnn_initialize();
        if (!is_initialized) {
            std::memset(out, 0, B * 1 * H * W * sizeof(float));
            return;
        }
    }

    if (total_calls < 5 && rank == 0) {
        std::cout << "[C++] cnn_predict: B=" << B << " C=" << C << " H=" << H << " W=" << W << " | Path: " 
                  << ((H == MODEL_H && W == MODEL_W) ? "FAST" : "ULTIMATE BRIDGE") << std::endl;
    }

    using namespace std::chrono;
    auto t_start = high_resolution_clock::now();

    try {
        if (H == MODEL_H && W == MODEL_W && B == 1) {
            //已经是 40x40 ===
            std::vector<int64_t> input_shape = {1, C, H, W};
            Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
                *memory_info, in, C * H * W, input_shape.data(), input_shape.size());
            std::vector<int64_t> output_shape = {1, 1, H, W};
            Ort::Value output_tensor = Ort::Value::CreateTensor<float>(
                *memory_info, out, 1 * H * W, output_shape.data(), output_shape.size());

            const char* input_names[] = {"input_mesh"};
            const char* output_names[] = {"p_new"};
            ort_session->Run(Ort::RunOptions{nullptr}, input_names, &input_tensor, 1, output_names, &output_tensor, 1);

        } else if (H == 20 && W == 20) {
            // === 桥接路径：20x20 -> 映射 -> 插值 -> 推理 -> 下采样 -> 逆映射 ===
            if (!bridge_mode_warned && rank == 0) {
                std::cout << "\n>>> [CNN Adapter] Activating Interpolation + Stats Remapping Bridge." << std::endl;
                bridge_mode_warned = true;
            }

            std::vector<float> mapped_in(C * H * W);
            std::vector<float> upsampled_in(C * MODEL_H * MODEL_W);
            std::vector<float> model_out(1 * MODEL_H * MODEL_W);
            std::vector<float> downsampled_out(1 * H * W);

            for (int b = 0; b < B; b++) {
                const float* sample_in = in + b * C * H * W;
                
                // 1. 正向统计量映射 (X_real_20 -> X_fake_20)
                for (int c = 0; c < C; c++) {
                    const float* src_c = sample_in + c * H * W;
                    float* dst_c = mapped_in.data() + c * H * W;
                    float s = scale_feat[c], bias = bias_feat[c];
                    for (int i = 0; i < H * W; i++) dst_c[i] = src_c[i] * s + bias;
                }

                // 2. 空间插值 (X_fake_20 -> X_fake_40)
                upsample_bilinear(mapped_in.data(), upsampled_in.data(), C, H, W);

                // 3. 推理 (ONNX 输出 P_new_fake_40 = P_old_fake_40 + Delta_fake_40)
                std::vector<int64_t> in_shape = {1, C, MODEL_H, MODEL_W};
                Ort::Value in_tensor = Ort::Value::CreateTensor<float>(
                    *memory_info, upsampled_in.data(), C * MODEL_H * MODEL_W, in_shape.data(), in_shape.size());
                std::vector<int64_t> out_shape = {1, 1, MODEL_H, MODEL_W};
                Ort::Value out_tensor = Ort::Value::CreateTensor<float>(
                    *memory_info, model_out.data(), 1 * MODEL_H * MODEL_W, out_shape.data(), out_shape.size());

                const char* input_names[] = {"input_mesh"};
                const char* output_names[] = {"p_new"};
                ort_session->Run(Ort::RunOptions{nullptr}, input_names, &in_tensor, 1, output_names, &out_tensor, 1);

                // 4. 下采样 (P_new_fake_40 -> P_new_fake_20)
                downsample_avg(model_out.data(), downsampled_out.data(), H, W);

                // 5. 逆向解包与真实值重建
                const float* p_old_fake_20 = mapped_in.data() + 5 * H * W; // 第 6 个通道
                const float* p_old_real_20 = sample_in + 5 * H * W;        // 原始 P_old
                float* sample_out = out + b * 1 * H * W;

                for (int i = 0; i < H * W; i++) {
                    // a. 提取伪造的增量
                    float delta_fake = downsampled_out[i] - p_old_fake_20[i];
                    // b. 逆映射回真实 20x20 增量
                    float delta_real = delta_fake * scale_delta_inv + bias_delta_inv;
                    // c. 计算真正的物理 P_new
                    sample_out[i] = p_old_real_20[i] + delta_real;
                }
            }
        } else {
            std::memset(out, 0, B * 1 * H * W * sizeof(float)); 
        }
    } catch (const Ort::Exception& e) {
        std::cerr << "[C++ ERROR] predict failed: " << e.what() << std::endl;
        std::memset(out, 0, B * 1 * H * W * sizeof(float));
    }

    auto t_end = high_resolution_clock::now();
    double ms = duration<double, std::milli>(t_end - t_start).count();
    total_calls++;
    total_ms_infer += ms;

    if (rank == 0 && total_calls % 2000 == 0) {
        std::cout << "[ONNX Profiler] Calls: " << total_calls << " | Avg: " << total_ms_infer / total_calls << " ms\n";
    }
}

DLL_EXPORT void cnn_print_summary(int rank) {
    if (rank == 0 && total_calls > 0) {
        std::cout << "\n==================================================\n"
                  << "[Final ONNX Runtime C++ Summary | Calls: " << total_calls << "]\n"
                  << "  Threads: " << ORT_NUM_THREADS << " (std::thread, no OpenMP conflict)\n"
                  << "  Model size: " << MODEL_H << "x" << MODEL_W << "\n"
                  << "  -> Total Time : " << total_ms_infer << " ms\n"
                  << "  -> Avg Time   : " << total_ms_infer / total_calls << " ms\n"
                  << "==================================================\n\n";
    }
}

} // extern "C"