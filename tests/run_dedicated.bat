@echo off
setlocal
chcp 65001 >nul

pushd "%~dp0.."
python -m file_tree.dedicated
set "exit_code=%errorlevel%"
popd

echo.
echo Dedicated mode finished with exit code: %exit_code%
pause
exit /b %exit_code%
