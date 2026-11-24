@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo [x] 没找到项目自带的 .venv
  echo     先建环境：py -3.14 -m venv .venv
  echo     再装依赖：.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "app\main.py"
exit /b 0
