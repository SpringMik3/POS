# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

project_root = Path.cwd()

datas = []
binaries = []
database_file = project_root / 'pos_database.db'
if database_file.exists():
    # Bundle a starter database into _MEIPASS; app_paths.py copies it next to exe only when missing.
    datas.append((str(database_file), '.'))

tcl_root = Path(sys.base_prefix) / 'tcl'
if (tcl_root / 'tcl8.6').exists():
    datas.append((str(tcl_root / 'tcl8.6'), '_tcl_data'))
if (tcl_root / 'tk8.6').exists():
    datas.append((str(tcl_root / 'tk8.6'), '_tk_data'))

dll_root = Path(sys.base_prefix) / 'DLLs'
for dll_name in ['tcl86t.dll', 'tk86t.dll']:
    dll_path = dll_root / dll_name
    if dll_path.exists():
        binaries.append((str(dll_path), '.'))

tkinter_package = Path(sys.base_prefix) / 'Lib' / 'tkinter'
if tkinter_package.exists():
    for tkinter_file in tkinter_package.glob('*.py'):
        datas.append((str(tkinter_file), 'tkinter'))

font_candidates = [
    Path('C:/Windows/Fonts/arial.ttf'),
    Path('C:/Windows/Fonts/arialbd.ttf'),
    Path('C:/Windows/Fonts/tahoma.ttf'),
    Path('C:/Windows/Fonts/tahomabd.ttf'),
    Path('C:/Windows/Fonts/segoeui.ttf'),
    Path('C:/Windows/Fonts/segoeuib.ttf'),
]
for font_path in font_candidates:
    if font_path.exists():
        datas.append((str(font_path), 'fonts'))

hiddenimports = [
    'tkinter',
    '_tkinter',
    'modules.report_exporter',
    'modules.backup_service',
    'modules.app_logger',
    'fpdf',
    'openpyxl',
    'openpyxl.styles',
    'win32print',
    'win32ui',
    'win32timezone',
    'pywintypes',
    'pythoncom',
]

excluded_modules = [
    'pandas',
    'numpy',
    'scipy',
    'torch',
    'matplotlib',
    'pyarrow',
    'pytest',
]


a = Analysis(
    ['pos_system.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / 'runtime_hooks' / 'tk_env.py')],
    excludes=excluded_modules,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pos_system',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='pos_system',
)
