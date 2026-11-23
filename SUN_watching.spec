# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the SUN_watching Windows distribution."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPEC).resolve().parent
PACKAGE = ROOT / "sun_find_west_v2"

CONFIG_DIR = PACKAGE / "config"
CAMERA_BIN_DIR = PACKAGE / "camera" / "bin"

# 同梱が欠けたまま配布物を作らないよう、ビルド前に必須ファイルを確認する。
# (paths.py は配布物で _internal/config と _internal/camera/bin を参照する)
required_files = [
    CONFIG_DIR / "config.yaml",
    CONFIG_DIR / "config_schema.json",
    CAMERA_BIN_DIR / "ASICamera2.dll",
]
missing_files = [str(path) for path in required_files if not path.is_file()]
if missing_files:
    raise SystemExit(
        "同梱するデータファイルが見つかりません: " + ", ".join(missing_files)
    )

# PyInstaller 配布物では config / camera / main などがトップレベルモジュールとして
# 読み込まれるため、データファイルも同じ階層に配置する。
# config は将来ファイルが増えても取りこぼさないようディレクトリごと同梱する。
datas = [
    (str(CONFIG_DIR), "config"),
    (str(CAMERA_BIN_DIR), "camera/bin"),
]
binaries = []
hiddenimports = [
    "main",
    "qt_visualizer",
    "camera.controller",
    "camera.vid_dummy",
    "config.loader",
    "paths",
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
