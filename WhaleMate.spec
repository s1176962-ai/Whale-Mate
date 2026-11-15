# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file build for WhaleMate (run: build_exe.bat)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH)

# Only read-only, distributable resources: never bundle data/users.json,
# data/profiles/ or any other local account/progress data.
datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "data" / "questions"), "data/questions"),
    (str(ROOT / "AI-assistant-icon.png"), "."),
    (str(ROOT / "learning_platform" / "locales"), "learning_platform/locales"),
]
datas += collect_data_files("reportlab")

a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "reportlab.pdfbase._fontdata",
        "reportlab.pdfbase._cidfontdata",
        "reportlab.pdfbase.cidfonts",
        "reportlab.pdfbase.ttfonts",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WhaleMate",
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
)
