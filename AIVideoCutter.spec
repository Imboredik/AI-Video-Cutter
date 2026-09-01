# AIVideoCutter.spec

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hiddenimports = [
    'soundfile',
    'torch',
    'torchaudio',
    'gigaam',
    'openai',
    'PyQt6',
    'numpy',
    'hydra',
    'omegaconf',
]

# Добавляем файлы конфигурации GigaAM
gigaam_datas = collect_data_files('gigaam')

# Явно добавляем папку с конфигами, если она есть
config_dirs = []
if os.path.exists('GigaAM/gigaam/conf'):
    config_dirs.append(('GigaAM/gigaam/conf', 'gigaam/conf'))
if os.path.exists('GigaAM/conf'):
    config_dirs.append(('GigaAM/conf', 'conf'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=gigaam_datas + config_dirs,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AIVideoCutter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # пока оставляем для отладки
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)