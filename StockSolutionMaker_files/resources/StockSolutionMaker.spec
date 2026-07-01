# -*- mode: python ; coding: utf-8 -*-

# 이 spec 파일은 resources 폴더 안에 있으므로, SPECPATH(spec 파일이 있는 폴더)를 기준으로
# python/, frontend/ 폴더에 있는 소스 파일들을 가리키도록 경로를 잡음.
import os
PROJECT_ROOT = os.path.dirname(SPECPATH)

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'python', 'launcher.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'python')],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'frontend', 'templates'), 'templates'),
        (os.path.join(PROJECT_ROOT, 'frontend', 'static'), 'static'),
    ],
    hiddenimports=[],
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
    name='StockSolutionMaker',
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
    icon=[os.path.join(SPECPATH, 'icon.ico')],
)
