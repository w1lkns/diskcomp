# -*- mode: python ; coding: utf-8 -*-

# diskcomp PyInstaller spec file
# Optimized for size and cross-platform compatibility

import sys
from pathlib import Path

# Build configuration
block_cipher = None
project_root = Path(".")

a = Analysis(
    ['diskcomp/cli.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Ensure these modules are included
        'diskcomp.types',
        'diskcomp.scanner', 
        'diskcomp.hasher',
        'diskcomp.reporter',
        'diskcomp.ui',
        'diskcomp.health',
        'diskcomp.drive_picker',
        'diskcomp.deletion',
        'diskcomp.benchmarker',
        'diskcomp.ansi_codes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
        'pytest',
        'unittest',
        'doctest',
        'pdb',
        'profile',
        'pstats',
        'sqlite3',  # Not used by diskcomp
        'email',    # Not used
        'ftplib',
        'smtplib',
        'poplib',
        'imaplib',
    ],
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
    name='diskcomp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols to reduce size
    upx=True,    # Compress with UPX if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version=None,
)