// ======================================================================
// cnn3ShortTime2.cpp (纯 ONNX Runtime C++ 插值桥接版本)
//
// ★ 专为验证模型通用性设计：
//   当 FDS 传入 20x20 网格时，自动执行以下物理场桥接：
//   1. 双线性插值上采样: (B, 6, 20, 20) -> (B, 6, 40, 40)
//   2. ONNX 推理:        (B, 6, 40, 40) -> (B, 1, 40, 40) (内含预后处理)
//   3. 平均池化下采样:   (B, 1, 40, 40) -> (B, 1, 20, 20)
//
// ★ 线程数：ONNX Runtime 用 std::thread，不与 FDS 的 Intel OpenMP 冲突
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
#define MODEL_H 40          // ONNX 模型固定的高度
#define MODEL_W 40          // ONNX 模型固定的宽度
#define MODEL_C 6           // 输入通道数

static Ort::Env* ort_env = nullptr;
static Ort::Session* ort_session = nullptr;
static Ort::MemoryInfo* memory_info = nullptr;

static bool is_initialized = false;
static bool bridge_mode_warned = false;
static uint64_t total_calls = 0;
static double total_ms_infer = 0.0;

// ======================================================================
// 核心数学工具 1：双线性插值上采样 (H, W) -> (MODEL_H, MODEL_W)
// 保证物理场特征的平滑过渡，不产生阶跃噪声
// ======================================================================
static void upsample_bilinear(const float* src, float* dst, int C, int H, int W) {
    for (int c = 0; c < C; c++) {
        const float* src_c = src + c * H * W;
        float* dst_c = dst + c * MODEL_H * MODEL_W;

        for (int mh = 0; mh < MODEL_H; mh++) {
            for (int mw = 0; mw < MODEL_W; mw++) {
                // 坐标映射回原图 (H, W)
                float h_orig = mh * (float)(H - 1) / (MODEL_H - 1);
                float w_orig = mw * (float)(W - 1) / (MODEL_W - 1);

                int h0 = (int)h_orig;
                int h1 = std::min(h0 + 1, H - 1);
                int w0 = (int)w_orig;
                int w1 = std::min(w0 + 1, W - 1);

                float h_diff = h_orig - h0;
                float w_diff = w_orig - w0;

                // 提取四个相邻点
                float p00 = src_c[h0 * W + w0];
                float p01 = src_c[h0 * W + w1];
                float p10 = src_c[h1 * W + w0];
                float p11 = src_c[h1 * W + w1];

                // 双线性加权
                dst_c[mh * MODEL_W + mw] = 
                    p00 * (1.0f - h_diff) * (1.0f - w_diff) +
                    p01 * (1.0f - h_diff) * w_diff +
                    p10 * h_diff * (1.0f - w_diff) +
                    p11 * h_diff * w_diff;
            }
        }
    }
}

// ======================================================================
// 核心数学工具 2：平均池化下采样 (MODEL_H, MODEL_W) -> (H, W)
// 防止最大池化或直接抽样带来的高频压力震荡
// ======================================================================
static void downsample_avg(const float* src, float* dst, int H, int W) {
    int stride_h = MODEL_H / H; // 对 20x20 而言 stride 是 2
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

        is_initialized = true;
        std::cout << "[C++] ONNX Runtime Ready! (Threads=" << ORT_NUM_THREADS << ")\n";
        std::cout << "[C++] *** INTERPOLATION BRIDGE BUILD v3.0 *** (Bilinear Up / Avg Down)\n";

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
        std::cout << "[C++] cnn_predict: B=" << B << " C=" << C << " H=" << H << " W=" << W 
                  << " | Model: " << MODEL_H << "x" << MODEL_W 
                  << " | Path: " << ((H == MODEL_H && W == MODEL_W) ? "FAST (Zero-Copy)" : "INTERPOLATION BRIDGE")
                  << std::endl;
    }

    using namespace std::chrono;
    auto t_start = high_resolution_clock::now();

    try {
        if (H == MODEL_H && W == MODEL_W && B == 1) {
            // ===== 快速路径：尺寸完全匹配，零拷贝 =====
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
            // ===== 插值桥接路径：20x20 -> 双线性 40x40 -> 推理 -> 平均池化 20x20 =====
            if (!bridge_mode_warned && rank == 0) {
                std::cout << "\n>>> [CNN Adapter] Activating 20x20 to 40x40 Interpolation Bridge." << std::endl;
                std::cout << ">>> [WARNING] Physical dissipation expected due to interpolation." << std::endl;
                bridge_mode_warned = true;
            }

            // 预分配缓冲区
            std::vector<float> upsampled_in(C * MODEL_H * MODEL_W);
            std::vector<float> model_out(1 * MODEL_H * MODEL_W);

            for (int b = 0; b < B; b++) {
                // 1. 双线性上采样
                const float* sample_in = in + b * C * H * W;
                upsample_bilinear(sample_in, upsampled_in.data(), C, H, W);

                // 2. 构造 40x40 Tensor 推理
                std::vector<int64_t> in_shape = {1, C, MODEL_H, MODEL_W};
                Ort::Value in_tensor = Ort::Value::CreateTensor<float>(
                    *memory_info, upsampled_in.data(), C * MODEL_H * MODEL_W,
                    in_shape.data(), in_shape.size());

                std::vector<int64_t> out_shape = {1, 1, MODEL_H, MODEL_W};
                Ort::Value out_tensor = Ort::Value::CreateTensor<float>(
                    *memory_info, model_out.data(), 1 * MODEL_H * MODEL_W,
                    out_shape.data(), out_shape.size());

                const char* input_names[] = {"input_mesh"};
                const char* output_names[] = {"p_new"};

                ort_session->Run(Ort::RunOptions{nullptr}, input_names, &in_tensor, 1, output_names, &out_tensor, 1);

                // 3. 平均池化下采样
                float* sample_out = out + b * 1 * H * W;
                downsample_avg(model_out.data(), sample_out, H, W);
            }
        } else {
            // 兜底保护：不支持的网格尺寸
            if (rank == 0) std::cerr << "[C++ ERROR] Unsupported grid size for interpolation: " << H << "x" << W << std::endl;
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