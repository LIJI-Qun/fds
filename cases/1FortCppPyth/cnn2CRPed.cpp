// ======================================================================
// cnn2CRPed.cpp
// Fortran (FDS) 与 Python (PyTorch) 之间的桥接 DLL
// 说明:
//   - 嵌入 Python 解释器，调用 cnn1pythonRPred_cavity.py 中的 CNN 模型
//   - 利用 FPUShield (RAII) 临时屏蔽 CPU 浮点异常，避免 Fortran 崩溃
//   - 使用标准 C++ <cfenv> 和 SSE intrinsic，兼容 MSVC 和 MinGW
//   - 集成 std::chrono 实现微秒级的细粒度耗时性能分析 (Profiling)
// ======================================================================

#include <pybind11/embed.h>
#include <pybind11/numpy.h>
#include <iostream>
#include <cstring>
#include <cstdint>
#include <cfenv>          // std::feholdexcept, std::fesetenv, fenv_t
#include <xmmintrin.h>    // _MM_SET_EXCEPTION_MASK, _MM_GET_EXCEPTION_MASK
#include <chrono>         // std::chrono 用于高精度计时

// ----------------------------------------------------------------------
// 1. DLL 导出宏
// ----------------------------------------------------------------------
#ifdef _WIN32
    #define DLL_EXPORT __declspec(dllexport)
#else
    #define DLL_EXPORT
#endif

// ----------------------------------------------------------------------
// 2. 浮点异常护盾类 (RAII 自动恢复)
// ----------------------------------------------------------------------
class FPUShield {
    fenv_t old_fenv;        // 保存 x87 浮点环境
    unsigned int old_sse;   // 保存 SSE 异常掩码
public:
    FPUShield() {
        std::feholdexcept(&old_fenv);   
        old_sse = _MM_GET_EXCEPTION_MASK();
        _MM_SET_EXCEPTION_MASK(_MM_MASK_MASK);
    }
// 析构函数，用于恢复浮点运算单元(FPU)和SIMD的原始异常处理设置
    ~FPUShield() {
    // 恢复之前的浮点环境设置，包括舍入模式、异常掩码等
        std::fesetenv(&old_fenv);
    // 恢复之前的SIMD(流式SIMD扩展)异常掩码设置
        _MM_SET_EXCEPTION_MASK(old_sse);
    }
};

// ----------------------------------------------------------------------
// 3. 全局状态与性能统计变量
// ----------------------------------------------------------------------
namespace py = pybind11;

static bool python_init_ok = false;   
static py::function predict_fn;       

// 用于累加耗时的全局统计变量
static uint64_t total_calls = 0;
static double total_ms_in = 0.0;
static double total_ms_infer = 0.0;
static double total_ms_out = 0.0;

// ----------------------------------------------------------------------
// 4. 供 Fortran 调用的接口函数 (C 链接)
// ----------------------------------------------------------------------
extern "C" {

DLL_EXPORT void cnn_initialize() {
    static bool tried_init = false;
    if (tried_init) {
        if (python_init_ok) return;
        std::cerr << "[C++ WARNING] Previous Python init failed, not retrying." << std::endl;
        return;
    }
    tried_init = true;

    FPUShield shield;
    std::cout << "[C++] Initializing Python Interpreter..." << std::endl;
    try {
        py::initialize_interpreter();
        std::cout << "[C++] Importing 'cnn1pythonRPred_cavity'..." << std::endl;
        py::module mod = py::module::import("cnn1pythonRPred_cavity");
        predict_fn = mod.attr("predict_pressure");
        python_init_ok = true;
        std::cout << "[C++] Python Environment Ready!" << std::endl;
    } catch (py::error_already_set &e) {
        std::cerr << "[C++ ERROR] Python Init Failed: " << e.what() << std::endl;
    } catch (const std::exception &e) {
        std::cerr << "[C++ ERROR] C++ exception during init: " << e.what() << std::endl;
    }
}

DLL_EXPORT void cnn_predict(float *in, float *out, int B, int C, int H, int W, int rank) {
    if (!python_init_ok) {
        cnn_initialize();
        if (!python_init_ok) {
            std::memset(out, 0, B * 1 * H * W * sizeof(float));
            return;
        }
    }

    FPUShield shield;
    using namespace std::chrono;

    try {
        // --- 1. 数据包装 ---
        auto t_in_start = high_resolution_clock::now();
        py::array_t<float> arr({B, C, H, W}, in);
        auto t_in_end = high_resolution_clock::now();

        // --- 2. 模型推理 ---
        auto t_infer_start = high_resolution_clock::now();
        py::array_t<float> res = predict_fn(arr);
        auto t_infer_end = high_resolution_clock::now();

        // --- 3. 数据回传 ---
        auto t_out_start = high_resolution_clock::now();
        if (res.size() != static_cast<py::ssize_t>(B) * 1 * H * W) {
            std::memset(out, 0, B * 1 * H * W * sizeof(float));
            return;
        }
        const float* res_data = res.data();
        std::memcpy(out, res_data, B * 1 * H * W * sizeof(float));
        auto t_out_end = high_resolution_clock::now();

        // --- 计算并累加耗时 ---
        double ms_in    = duration<double, std::milli>(t_in_end - t_in_start).count();
        double ms_infer = duration<double, std::milli>(t_infer_end - t_infer_start).count();
        double ms_out   = duration<double, std::milli>(t_out_end - t_out_start).count();

        total_calls++;
        total_ms_in += ms_in;
        total_ms_infer += ms_infer;
        total_ms_out += ms_out;

        // 【过程输出】：每 1000 次调用，输出一次总结报告 (降低 I/O 开销)
        if (rank == 0 && total_calls % 4000 == 0) {
            std::cout << "\n[C++ Profiler Summary | CNN Calls: " << total_calls << "]\n"
                      << "     -> Wrap (C++->Py) : Total = " << total_ms_in << " ms | Avg = " << total_ms_in / total_calls << " ms\n"
                      << "     -> Py-Inference   : Total = " << total_ms_infer << " ms | Avg = " << total_ms_infer / total_calls << " ms\n"
                      << "     -> Copy (Py->C++) : Total = " << total_ms_out << " ms | Avg = " << total_ms_out / total_calls << " ms\n"
                      << "--------------------------------------------------\n";
        }

    } catch (py::error_already_set &e) {
        std::memset(out, 0, B * 1 * H * W * sizeof(float));
    } catch (const std::exception &e) {
        std::memset(out, 0, B * 1 * H * W * sizeof(float));
    }
}

// 提供给 Fortran 在模拟彻底结束（如 60s 时）调用的接口
DLL_EXPORT void cnn_print_summary(int rank) {
    if (rank == 0 && total_calls > 0) {
        // 1. 打印 C++ 层的包装耗时统计
        std::cout << "\n==================================================\n"
                  << "[Final C++ Profiler Summary | CNN Calls: " << total_calls << "]\n"
                  << "     -> Wrap (C++->Py) : Total = " << total_ms_in << " ms | Avg = " << total_ms_in / total_calls << " ms\n"
                  << "     -> Py-Inference   : Total = " << total_ms_infer << " ms | Avg = " << total_ms_infer / total_calls << " ms\n"
                  << "     -> Copy (Py->C++) : Total = " << total_ms_out << " ms | Avg = " << total_ms_out / total_calls << " ms\n";

        // 2. 跨语言调用 Python 内部的 14步细分统计打印函数
        if (python_init_ok) {
            FPUShield shield; // 保护浮点环境，防止 Python 退出时抛出异常
            try {
                py::module mod = py::module::import("cnn1pythonRPred_cavity");
                py::function print_summary_fn = mod.attr("print_summary");
                print_summary_fn(); // 执行 Python 中的 _print_summary()
            } catch (const std::exception &e) {
                std::cerr << "[C++ ERROR] Could not call Python print_summary: " << e.what() << std::endl;
            }
        }
        std::cout << "==================================================\n\n";
    }
 }

} // extern "C"