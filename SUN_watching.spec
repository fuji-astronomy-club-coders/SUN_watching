# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the SUN_watching Windows distribution."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPEC).resolve().parent
PACKAGE = ROOT / "sun_find_west_v2"

# matplotlib / scikit-learn rely on package data and dynamic imports.
datas = [
    (str(PACKAGE / "config" / "config.yaml"), "sun_find_west_v2/config"),
    (str(PACKAGE / "config" / "config_schema.json"), "sun_find_west_v2/config"),
    (str(PACKAGE / "camera" / "bin" / "ASICamera2.dll"), "sun_find_west_v2/camera/bin"),
]
binaries = []
hiddenimports = [
    "main",
    "qt_visualizer",
    "camera.controller",
    "camera.vid_dummy",
    "config.loader",
    "core.MIN2ver2",
    "core.RANSAC",
    "core.drawer",
]

for package in ("matplotlib", "sklearn"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# zwoasi is optional at source level, but is included in the Windows build when
# available so the same executable supports both dummy-video and ASI cameras.
try:
    package_datas, package_binaries, package_hiddenimports = collect_all("zwoasi")
except Exception:
    pass
else:
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports


a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT), str(PACKAGE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="SUN_watching",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="SUN_watching",
)
