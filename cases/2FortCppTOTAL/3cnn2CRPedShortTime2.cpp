// ======================================================================
// 3cnn2CRPedShortTime2 (纯 ONNX Runtime C++ 版本)
// 特点：0 Python开销、0 内存拷贝、完美兼容 MinGW g++、原生避免 ABI 冲突
// ======================================================================

#include <onnxruntime_cxx_api.h>
#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <windows.h>

#ifdef _WIN32
    #define DLL_EXPORT __declspec(dllexport)
#else
    #define DLL_EXPORT
#endif

// 全局 ORT 引擎变量
static Ort::Env* ort_env = nullptr;
static Ort::Session* ort_session = nullptr;
static Ort::MemoryInfo* memory_info = nullptr;

static bool is_initialized = false;
static uint64_t total_calls = 0;
static double total_ms_infer = 0.0;

extern "C" {

DLL_EXPORT void cnn_initialize() {
    if (is_initialized) return;
    
    try {
        std::cout << "[C++] Initializing ONNX Runtime Engine..." << std::endl;
        
        // 1. 初始化环境
        ort_env = new Ort::Env(ORT_LOGGING_LEVEL_WARNING, "FDS_CNN");
        
        // 2. 配置极致优化与单线程（防止与 FDS 的 OpenMP 冲突）
        Ort::SessionOptions session_options;
        session_options.SetIntraOpNumThreads(1); 
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);

        // 3. 加载刚才导出的 ONNX 模型 (Windows 下必须用宽字符 L"...")
        #ifdef _WIN32
        const wchar_t* model_path = L"unet_cfd_engine.onnx";
        #else
        const char* model_path = "unet_cfd_engine.onnx";
        #endif

        ort_session = new Ort::Session(*ort_env, model_path, session_options);
        
        // 4. 配置内存分配器（用于稍后的零拷贝）
        memory_info = new Ort::MemoryInfo(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault));

        is_initialized = true;
        std::cout << "[C++] ONNX Runtime Engine Ready! (Pure C++, No Python)" << std::endl;

    // 在文件顶部加上 #include <windows.h>
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

    using namespace std::chrono;
    auto t_start = high_resolution_clock::now();

    try {
        // --- 零拷贝 (Zero-Copy) ---
        // 直接把 Fortran 传过来的 in 和 out 指针“包裹”成 Tensor 给引擎，
        // 底层完全不进行任何内存搬运！
        
        std::vector<int64_t> input_shape = {B, C, H, W};
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            *memory_info, in, B * C * H * W, input_shape.data(), input_shape.size());

        std::vector<int64_t> output_shape = {B, 1, H, W};
        Ort::Value output_tensor = Ort::Value::CreateTensor<float>(
            *memory_info, out, B * 1 * H * W, output_shape.data(), output_shape.size());

        // 设置模型的输入输出节点名称（对应 Python 里导出的名称）
        const char* input_names[] = {"input_mesh"};
        const char* output_names[] = {"p_new"};

        // 执行前向传播！(结果自动写进了 out 指针指向的内存)
        ort_session->Run(Ort::RunOptions{nullptr}, 
                         input_names, &input_tensor, 1, 
                         output_names, &output_tensor, 1);

    } catch (const Ort::Exception& e) {
        // 万一计算报错，为了不让 FDS 崩溃，清空输出作为保底
        std::memset(out, 0, B * 1 * H * W * sizeof(float));
    }

    auto t_end = high_resolution_clock::now();
    double ms = duration<double, std::milli>(t_end - t_start).count();

    total_calls++;
    total_ms_infer += ms;

    if (rank == 0 && total_calls % 2000 == 0) {
        std::cout << "[ONNX Profiler] Calls: " << total_calls 
                  << " | Avg: " << total_ms_infer / total_calls << " ms\n";
    }
}

DLL_EXPORT void cnn_print_summary(int rank) {
    if (rank == 0 && total_calls > 0) {
        std::cout << "\n==================================================\n"
                  << "[Final ONNX Runtime C++ Summary | Calls: " << total_calls << "]\n"
                  << "     -> Total Time : " << total_ms_infer << " ms\n"
                  << "     -> Avg Time   : " << total_ms_infer / total_calls << " ms\n"
                  << "==================================================\n\n";
    }
}

} // extern "C"