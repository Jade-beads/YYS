# -*- mode: python ; coding: utf-8 -*-
# 单文件打包配置。PyInstaller 不能交叉编译:要得到 Windows 的 YYS.exe,必须在 Windows 上运行
#   pyinstaller --noconfirm YYS_win.spec
# (上游的 YYS.spec 引用了仓库里不存在的 resources/ 目录,直接用会失败,所以另起一份。)
#
# 游戏模块(yys/yys.py、nsh/nsh.py)是 main.py 运行时用 importlib 从数据目录按源码导入的,
# 所以整个目录作为 datas 打进去即可;它们依赖的库都已被 main.py / action.py 静态引用到。

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('main.ui', '.'),
        ('config.ini', '.'),
        ('yys', 'yys'),
        ('nsh', 'nsh'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
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
    name='YYS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX 压缩 Qt 的 DLL 容易出问题,也更容易被杀毒误报
    runtime_tmpdir=None,
    console=False,          # 窗口程序;注意此时 sys.stderr 为 None,config.ini 里 debug 必须保持 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
