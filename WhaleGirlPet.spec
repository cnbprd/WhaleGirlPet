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

# v2.9.6 原生启动图：onefile 解压那 1.5 秒不再白屏（PyInstaller 6 需以 Splash 对象作为 EXE 参数）
splash_obj = Splash(
    'assets/ui/splash_native.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    text_default='鲸鱼娘加载中',
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash_obj,
    splash_obj.binaries,   # tcl90.dll / tcl9tk90.dll 必须一起进包，否则启动图起不来
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
