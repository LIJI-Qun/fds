@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
call "C:\Program Files (x86)\Intel\oneAPI\setvars.bat" intel64 vs2019 >nul 2>&1
cd /d F:\2CODE\FDS2026New\fds\Build\impi_intel_win
echo ==== [BUILD START] %date% %time% ====
call make_fds.bat bot
echo ==== [BUILD END] %date% %time% EXITCODE=%ERRORLEVEL% ====
exit /b 0
