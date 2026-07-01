# -*- mode: python ; coding: utf-8 -*-

# 이 spec 파일은 etc 폴더 안에 있으므로, SPECPATH(spec 파일이 있는 폴더)의
# 한 단계 위 폴더를 PROJECT_ROOT로 잡아서 backend/, frontend/ 폴더를 가리킵니다.
import os
PROJECT_ROOT = os.path.dirname(SPECPATH)

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'backend', 'app.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'backend')],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'frontend'), 'frontend'),
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
    name='SolutionmakerWithStock',
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
    icon=[os.path.join(PROJECT_ROOT, 'etc', 'icon2.ico')],
)
