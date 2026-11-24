# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the SUN_watching Windows distribution."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPEC).resolve().parent
PACKAGE = ROOT / "sun_find_west_v2"

CONFIG_DIR = PACKAGE / "config"
CAMERA_BIN_DIR = PACKAGE / "camera" / "bin"
ASI_DLL = CAMERA_BIN_DIR / "ASICamera2.dll"

# 同梱が欠けたまま配布物を作らないよう、ビルド前に必須ファイルを確認する。
# (paths.py は配布物で _internal/config と _internal/camera/bin を参照する)
required_files = [
    CONFIG_DIR / "config.yaml",
    CONFIG_DIR / "config_schema.json",
    ASI_DLL,
]
missing_files = [str(path) for path in required_files if not path.is_file()]
if missing_files:
    raise SystemExit(
        "同梱するデータファイルが見つかりません: " + ", ".join(missing_files)
    )


def pe_machine(path: Path) -> int:
    """PE ファイルの Machine 値を返す (AMD64 は 0x8664)。"""
    data = path.read_bytes()
    pe_offset = int.from_bytes(data[0x3C:0x40], "little")
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise SystemExit(f"PE ファイルではありません: {path}")
    return int.from_bytes(data[pe_offset + 4 : pe_offset + 6], "little")


# 32bit の DLL を混入させると実行時に初期化できないためビルドを止める。
if pe_machine(ASI_DLL) != 0x8664:
    raise SystemExit(f"ASICamera2.dll が 64bit (AMD64) ではありません: {ASI_DLL}")

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
    "config.editor",
    "config.editor_model",
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
