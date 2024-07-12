# ftp_screenshots.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['ftp_screenshots.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.ini', '.'),
        ('icon.png', '.'),
        ('icon.icns', '.'),
        ('icon.ico', '.'),
        ('dark_taskbar.png', '.'),
        ('light_taskbar.png', '.')
    ],
    hiddenimports=[],
    hookspath=[],
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
    [],
    exclude_binaries=True,
    name='ftp_screenshots',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False to hide the console window
    icon='icon.ico',  # Path to your icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ftp_screenshots',
)

app = BUNDLE(
    coll,
    name='FTP Screenshots.app',
    icon='icon.icns',  # Path to your icon file
    bundle_identifier='com.ppkantorski.ftp_screenshots',
    info_plist={
        'CFBundleName': 'ftp_screenshots',
        'CFBundleDisplayName': 'FTP Screenshots',
        'CFBundleIdentifier': 'com.ppkantorski.ftp_screenshots',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'LSUIElement': True,
    }
)
