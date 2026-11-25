# Build WhaleGirlPet.exe (run from whale-girl-pet folder)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$venvPy = Join-Path $root "..\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { $venvPy = "python" }

& $venvPy -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name WhaleGirlPet `
    --icon (Join-Path $root "assets\ui\pet.ico") `
    --paths (Join-Path $root "app") `
    --hidden-import PySide6.QtMultimedia `
    --hidden-import edge_tts `
    --hidden-import skills `
    --hidden-import secscan `
    --hidden-import local_llm `
    --hidden-import voice_cmd `
    --hidden-import tasks `
    --hidden-import hwinfo `
    --hidden-import sysvol `
    --hidden-import pycaw `
    --hidden-import comtypes `
    --hidden-import gpu_guard `
    --hidden-import psutil `
    --hidden-import ambient `
    --hidden-import awareness `
    --hidden-import voice_profile `
    --hidden-import theme `
    --collect-all edge_tts `
    --collect-all aiohttp `
    --collect-all certifi `
    --exclude-module tkinter `
    --exclude-module numpy `
    --exclude-module pandas `
    --exclude-module scipy `
    --exclude-module matplotlib `
    --exclude-module PIL `
    --add-data "assets\skins;assets\skins" `
    --add-data "assets\expressions;assets\expressions" `
    --add-data "assets\actions;assets\actions" `
    --add-data "assets\loli;assets\loli" `
    --add-data "assets\ui;assets\ui" `
    (Join-Path $root "app\main.py")

Write-Host "build done -> dist\WhaleGirlPet.exe"
Write-Host "runtime folder (dafeiyu engine + gguf) must sit next to the exe, not packed."
