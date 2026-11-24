# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets/skins', 'assets/skins'), ('assets/expressions', 'assets/expressions'), ('assets/actions', 'assets/actions'), ('assets/loli', 'assets/loli'), ('assets/ui', 'assets/ui')]
binaries = []
hiddenimports = ['PySide6.QtMultimedia', 'edge_tts', 'skills', 'secscan', 'local_llm', 'voice_cmd', 'tasks', 'hwinfo', 'sysvol', 'pycaw', 'comtypes', 'gpu_guard', 'psutil', 'ambient', 'awareness', 'voice_profile', 'theme']
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aiohttp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tabulate')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('certifi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:/Users/yangmengke/Doubao/chats/2026-11-23/new-chat/whale-girl-pet/app/main.py'],
    pathex=['C:/Users/yangmengke/Doubao/chats/2026-11-23/new-chat/whale-girl-pet/app'],
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
    icon=['C:/Users/yangmengke/Doubao/chats/2026-11-23/new-chat/whale-girl-pet/assets/ui/pet.ico'],
)
