@echo off
chcp 65001 > nul
setlocal
set DEST=%~dp0runtime\models
echo ============================================
echo  鲸鱼娘桌宠 - 导入本地模型（离线也能用）
echo ============================================
echo.
if "%~1"=="" (
  echo 用法：把存放 .gguf 模型的文件夹，直接拖到这个文件上。
  echo 也可以双击后手动输入路径。
  echo.
  set /p SRC=请输入模型文件夹路径（含 .gguf）：
) else (
  set SRC=%~1
)
if not exist "%SRC%" (
  echo [错误] 路径不存在：%SRC%
  pause
  exit /b 1
)
if not exist "%DEST%" mkdir "%DEST%"
echo 正在从 %SRC% 复制 .gguf 到 %DEST% ...
copy /Y "%SRC%\*.gguf" "%DEST%" > nul
if errorlevel 1 (
  echo [提示] 没有找到 .gguf，或复制失败。
) else (
  echo [完成] 模型已就位，重启桌宠即可离线使用。
)
echo.
dir /b "%DEST%\*.gguf" 2>nul
pause
