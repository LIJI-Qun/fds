@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
call "C:\Program Files (x86)\Intel\oneAPI\setvars.bat" intel64 vs2019 >nul 2>&1
echo === ifx ===
where ifx 2>nul
ifx --version 2>&1 | findstr /i "version"
echo === link ===
where link 2>nul
echo === make ===
where make 2>nul
echo === COMP_FC check ===
where ifx 2>nul && set COMP_FC=ifx
echo COMP_FC=%COMP_FC%
echo === mpiexec ===
where mpiexec 2>nul
