@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [x] 没找到项目自带的 .venv，见 PROJECT.md 第一节。
  pause
  exit /b 1
)
echo 带控制台启动，报错会显示在这里。
".venv\Scripts\python.exe" "app\main.py"
echo.
echo 进程已退出。
pause
