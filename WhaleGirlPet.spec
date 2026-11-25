# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets/skins', 'assets/skins'), ('assets/expressions', 'assets/expressions'), ('assets/actions', 'assets/actions'), ('assets/loli', 'assets/loli'), ('assets/ui', 'assets/ui')]
binaries = []
# v3.0.17 瘦身：v3.0.1 已删原生 Splash（Tk），这里去掉 tkinter —— 它会把整个
#   tcl90/tk90 数据目录拖进包（未压缩约 15MB）。app 下全项目 0 次 import tkinter。
hiddenimports = ['PySide6.QtMultimedia', 'edge_tts', 'skills', 'secscan', 'local_llm', 'voice_cmd', 'tasks', 'hwinfo', 'sysvol', 'pycaw', 'comtypes', 'gpu_guard', 'psutil', 'ambient', 'awareness', 'voice_profile', 'theme',
                 'asyncio', 'unicodedata']
tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aiohttp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# v3.0.17：tabulate 在 app 下 0 次被 import（实测），collect_all 纯属把它的
#   测试与 metadata 也塞进包，删掉。
tmp_ret = collect_all('certifi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# v3.0.17：venv 里装了但代码 0 次使用的重型库，显式排除（PIL 只在离线工具脚本里用过，
#   桌宠本体不用；numpy/pandas/scipy/matplotlib 从未 import）。
EXCLUDES = ['tkinter', 'numpy', 'pandas', 'scipy', 'matplotlib', 'PIL',
            'pytest', '_pytest', 'IPython', 'notebook']


a = Analysis(
    ['app/main.py'],
    pathex=['app'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,          # v3.0.17：去掉 docstring（全项目 0 处用 __doc__）
)
pyz = PYZ(a.pure)

# v3.0.1：去掉 PyInstaller 原生启动图。
# 原生 Splash 是 Tk 窗口，只能显示一张不透明方块图，做不出「纯人物透明背景」；
# 用户要求启动画面 = 大肥鱼本人在动、没有任何背景板，所以冷启动那几个窗口空白
# 交给 app/splash.py 的透明浮层来表现（它一出来就是透明的人物动画）。
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # v3.0.18：onedir —— 二进制与数据不再塞进 exe
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

# v3.0.18：onefile → onedir。
#   实测 onefile 每次冷启动都要把 64MB 解到 %TEMP%\ (2.1s)，还要多留一个引导进程；
#   onedir 直接就地加载，这段开销为零，常驻内存也少一个进程。
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WhaleGirlPet',
)
