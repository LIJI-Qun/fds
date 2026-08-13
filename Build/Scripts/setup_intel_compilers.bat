@echo off

IF  X%SETVARS_COMPLETED% == X1 GOTO intel_envexist

  set "ONEAPIDIR=C:\Program Files (x86)\Intel\oneAPI"
  IF DEFINED ONEAPI_ROOT set "ONEAPIDIR=%ONEAPI_ROOT%"
  IF NOT EXIST "%ONEAPIDIR%\setvars.bat" goto intel_notexist

  echo Defining Intel compiler environment
  call "%ONEAPIDIR%\setvars" intel64

  IF  X%SETVARS_COMPLETED% == X1 GOTO intel_envexist

:intel_notexist
  echo ***error: Intel compiler environment is not setup
  goto :eof

:intel_envexist
  :: Intel setvars.bat may rebuild PATH. Restore GNU Make afterwards so all
  :: Windows FDS build targets can find make.exe.
  set "GNUMAKE_BIN=G:\Program Files (x86)\GnuWin32\bin"
  IF EXIST "%GNUMAKE_BIN%\make.exe" (
    set "PATH=%GNUMAKE_BIN%;%PATH%"
  ) ELSE (
    echo ***error: GNU Make was not found at "%GNUMAKE_BIN%\make.exe"
  )
:eof
