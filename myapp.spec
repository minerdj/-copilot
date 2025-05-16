import sys
import os
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

# Збираємо і додаємо hook/хуки бінарники.
# Збираємо інформацію про проект
a = Analysis(
    ['main.py'],  # Основний скрипт програми
    pathex=[os.getcwd()],  # Використовуємо поточну робочу директорію
    binaries=[
        ('selenium_stealth', './selenium_stealth'),
    ],
    datas=[
        ('server_start_time.py', '.'),
        ('parser.py', '.'),  # Додайте інші файли
        ('demo.py', '.'),
        ('app.py', '.'),
        ('html_to_docx.py', '.')
    ],
    hiddenimports=collect_submodules('app'),  # Включаємо модулі з 'app', якщо вони є
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False
)

# Створюємо архів PYZ
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Налаштовуємо виконуваний файл EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Встановіть False, якщо це графічний додаток
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Збираємо всі частини разом
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main'
)
