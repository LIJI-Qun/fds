// ======================================================================
// 文件名: cnn2CRPed.cpp
// 功能:   Fortran (FDS) 与 Python (PyTorch) 之间的桥接 DLL
// 说明:
//   - 嵌入 Python 解释器，调用 cnn1pythonRPred.py 中的 CNN 模型
//   - 利用 FPUShield (RAII) 临时屏蔽 CPU 浮点异常，避免 Fortran
//     严格模式下 PyTorch/NumPy 的正常运算导致程序崩溃
//   - 使用标准 C++ <cfenv> 和 SSE intrinsic，兼容 MSVC 和 MinGW
// ======================================================================

#include <pybind11/embed.h>
#include <pybind11/numpy.h>
#include <iostream>
#include <cstring>
#include <cstdint>
#include <cfenv>          // std::feholdexcept, std::fesetenv, fenv_t
#include <xmmintrin.h>    // _MM_SET_EXCEPTION_MASK, _MM_GET_EXCEPTION_MASK

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
        // 屏蔽 x87 浮点异常 (标准 C++ 方法)
        std::feholdexcept(&old_fenv);   // 保存当前环境并设置非停止模式

        // 屏蔽 SSE/AVX 浮点异常 (核心，解决 64 位程序崩溃)
        old_sse = _MM_GET_EXCEPTION_MASK();
        _MM_SET_EXCEPTION_MASK(_MM_MASK_MASK);
    }

    ~FPUShield() {
        // 恢复 x87 浮点环境
        std::fesetenv(&old_fenv);
        // 恢复 SSE 异常掩码
        _MM_SET_EXCEPTION_MASK(old_sse);
    }
};

// ----------------------------------------------------------------------
// 3. 全局状态
// ----------------------------------------------------------------------
namespace py = pybind11;

static bool python_init_ok = false;   // Python 是否成功初始化
static py::function predict_fn;       // 预测函数对象

// ----------------------------------------------------------------------
// 4. 供 Fortran 调用的接口函数 (C 链接)
// ----------------------------------------------------------------------
extern "C" {

// 初始化 Python 解释器并加载模型 (仅执行一次)
DLL_EXPORT void cnn_initialize() {
    static bool tried_init = false;
    if (tried_init) {
        if (python_init_ok) return;
        std::cerr << "[C++ WARNING] Previous Python init failed, not retrying." << std::endl;
        return;
    }
    tried_init = true;

    // 初始化过程中 PyTorch 加载等操作可能触发浮点异常
    FPUShield shield;

    std::cout << "[C++] Initializing Python Interpreter..." << std::endl;
    try {
        py::initialize_interpreter();

        std::cout << "[C++ DEBUG] Importing 'cnn1pythonRPred'..." << std::endl;
        py::module mod = py::module::import("cnn1pythonRPred");
        predict_fn = mod.attr("predict_from_array");

        python_init_ok = true;
        std::cout << "[C++] Python Environment Ready!" << std::endl;
    } catch (py::error_already_set &e) {
        std::cerr << "[C++ ERROR] Python Init Failed: " << e.what() << std::endl;
    } catch (const std::exception &e) {
        std::cerr << "[C++ ERROR] C++ exception during init: " << e.what() << std::endl;
    }
}

// 执行 CNN 预测
DLL_EXPORT void cnn_predict(float *in, float *out, int B, int C, int H, int W) {
    if (!python_init_ok) {
        cnn_initialize();
        if (!python_init_ok) {
            std::memset(out, 0, B * 1 * H * W * sizeof(float));
            return;
        }
    }

    // 护盾：每次预测均屏蔽浮点异常
    FPUShield shield;

    try {
        // 将输入指针包装为多维 NumPy 数组 (零拷贝)
        py::array_t<float> arr({B, C, H, W}, in);

        // 调用 Python 预测函数
        py::array_t<float> res = predict_fn(arr);

        // 验证输出尺寸
        if (res.size() != static_cast<py::ssize_t>(B) * 1 * H * W) {
            std::cerr << "[C++ ERROR] Output dimension mismatch! Expected: "
                      << B * 1 * H * W << " Got: " << res.size() << std::endl;
            std::memset(out, 0, B * 1 * H * W * sizeof(float));
            return;
        }

        // 拷贝结果
        const float* res_data = res.data();
        std::memcpy(out, res_data, B * 1 * H * W * sizeof(float));

    } catch (py::error_already_set &e) {
        std::cerr << "[C++ ERROR] Python Inference Failed: " << e.what() << std::endl;
        std::memset(out, 0, B * 1 * H * W * sizeof(float));
    } catch (const std::exception &e) {
        std::cerr << "[C++ ERROR] C++ exception during inference: " << e.what() << std::endl;
        std::memset(out, 0, B * 1 * H * W * sizeof(float));
    }
}

} // extern "C"