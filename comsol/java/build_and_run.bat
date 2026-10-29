@echo off
rem ==========================================================================
rem Driver B wrapper (Windows).  Usage:
rem   build_and_run.bat [build|run|all] [core|full]
rem     build : comsolcompile + comsolbatch BuildPinPeltier  -> comsol\models\*.mph
rem     run   : comsolcompile + comsolbatch RunVariants      -> results\<variant>\*.csv
rem     all   : both (default);   second argument = variant set (default core)
rem COMSOL is located from %COMSOL63_PATH%, then install_path in
rem config\user_env.yaml, then the standard COMSOL 6.3 folders.
rem ==========================================================================
setlocal EnableDelayedExpansion
set "HERE=%~dp0"
pushd "%HERE%..\.."
set "PIN_PELTIER_ROOT=%CD%"
popd
set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"
set "PIN_SET=%~2"
if "%PIN_SET%"=="" set "PIN_SET=core"

set "CROOT="
if defined COMSOL63_PATH set "CROOT=%COMSOL63_PATH%"
if not defined CROOT (
  for /f "tokens=1,* delims=:" %%a in ('findstr /r /c:"^  install_path:" "%PIN_PELTIER_ROOT%\config\user_env.yaml"') do set "CFGPATH=%%b"
  if defined CFGPATH (
    set "CFGPATH=!CFGPATH:'=!"
    set "CFGPATH=!CFGPATH:"=!"
    for /f "tokens=* delims= " %%c in ("!CFGPATH!") do set "CFGPATH=%%c"
    if /i not "!CFGPATH!"=="null" set "CROOT=!CFGPATH!"
  )
)
if not defined CROOT if exist "C:\Program Files\COMSOL\COMSOL63\Multiphysics\bin" set "CROOT=C:\Program Files\COMSOL\COMSOL63\Multiphysics"
if not defined CROOT if exist "C:\COMSOL\COMSOL63\Multiphysics\bin" set "CROOT=C:\COMSOL\COMSOL63\Multiphysics"
if not defined CROOT (
  echo [pin_peltier] COMSOL 6.3 not found. Set COMSOL63_PATH or install_path in config\user_env.yaml.
  exit /b 1
)
set "BIN=%CROOT%\bin\win64"
echo [pin_peltier] COMSOL: %CROOT%
echo [pin_peltier] project: %PIN_PELTIER_ROOT%
if not exist "%PIN_PELTIER_ROOT%\comsol\models" mkdir "%PIN_PELTIER_ROOT%\comsol\models"
pushd "%HERE%"

if /i "%MODE%"=="run" goto run
"%BIN%\comsolcompile.exe" BuildPinPeltier.java || goto fail
"%BIN%\comsolbatch.exe" -inputfile BuildPinPeltier.class -outputfile "%PIN_PELTIER_ROOT%\comsol\models\pin_peltier_base.mph" -batchlog "%PIN_PELTIER_ROOT%\comsol\models\build_batch.log" || goto fail
if /i "%MODE%"=="build" goto done

:run
"%BIN%\comsolcompile.exe" RunVariants.java || goto fail
"%BIN%\comsolbatch.exe" -inputfile RunVariants.class -nosave -batchlog "%PIN_PELTIER_ROOT%\results\run_batch.log" || goto fail

:done
popd
echo [pin_peltier] done.
exit /b 0
:fail
popd
echo [pin_peltier] FAILED -- see the batch log and docs\VERIFY_API_NAMES.md
exit /b 1
