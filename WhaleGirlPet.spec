# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets/skins', 'assets/skins'), ('assets/expressions', 'assets/expressions'), ('assets/actions', 'assets/actions'), ('assets/loli', 'assets/loli'), ('assets/ui', 'assets/ui')]
binaries = []
hiddenimports = ['PySide6.QtMultimedia', 'edge_tts', 'skills', 'secscan', 'local_llm', 'voice_cmd', 'tasks', 'hwinfo', 'sysvol', 'pycaw', 'comtypes', 'gpu_guard', 'psutil', 'ambient', 'awareness', 'voice_profile', 'theme',
                 'tkinter']   # v2.9.6：原生 Splash 需要 tcl90.dll/tk90.dll，靠 tkinter 的 hook 收进来
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aiohttp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tabulate')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('certifi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app/main.py'],
    pathex=['app'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# v3.0.1：去掉 PyInstaller 原生启动图。
# 原生 Splash 是 Tk 窗口，只能显示一张不透明方块图，做不出「纯人物透明背景」；
# 用户要求启动画面 = 大肥鱼本人在动、没有任何背景板，所以冷启动那几个窗口空白
# 交给 app/splash.py 的透明浮层来表现（它一出来就是透明的人物动画）。
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WhaleGirlPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/ui/pet.ico'],
)
