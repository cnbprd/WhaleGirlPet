@echo off
setlocal
cd /d F:\WhaleGirlPet
set "WHALE3D_LONGRUN_SECONDS=86400"
set "WHALE3D_LONGRUN_TAG=soak_24h_sprite_task"
set "WHALE3D_LONGRUN_SAMPLE=30"
set "WHALE3D_LONGRUN_OFFSCREEN=1"
set "WHALE3D_EXE=F:\WhaleGirlPet\3d\whale3d.exe"
"F:\WhaleGirlPet\.venv\Scripts\python.exe" "F:\WhaleGirlPet\3d\tools\emotion_longrun.py" >> "F:\WhaleGirlPet\build\soak_24h_sprite_task_launcher.log" 2>&1
exit /b %errorlevel%
