"""パス解決と出力先ディレクトリ作成のテスト。"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from sun_find_west_v2 import paths


def test_source_layout() -> None:
    """ソース実行時はパッケージ内とリポジトリ直下を参照する。"""
    assert paths.resource_dir() == Path(paths.__file__).resolve().parent
    assert paths.config_path().name == "config.yaml"
    assert paths.schema_path().is_file()
    assert paths.dll_path().is_file()


def test_frozen_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """配布物では _MEIPASS 直下の config / camera を参照する。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv(paths.HOME_ENV_VAR, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    assert paths.resource_dir() == tmp_path
    assert paths.config_path() == tmp_path / "config" / "config.yaml"
    assert paths.schema_path() == tmp_path / "config" / "config_schema.json"
    assert paths.dll_path() == tmp_path / "camera" / "bin" / "ASICamera2.dll"
    assert paths.user_home() == tmp_path / "localappdata" / paths.APP_NAME


def _imported_path_names(path: Path) -> set[str]:
    """モジュールが ``paths`` から import している名前を集める。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "paths"
            and (node.level or 0) <= 1
        ):
            names.update(alias.name for alias in node.names)
    return names


def test_paths_exports_every_imported_name() -> None:
    """paths から import する名前が paths.py に実在する。

    PyInstaller 配布物では相対 import が失敗してトップレベル import に
    フォールバックするため、名前の食い違いは配布物の起動時にしか露見しない。
    """
    repo_root = Path(paths.__file__).resolve().parent.parent
    modules = [
        repo_root / "run.py",
        repo_root / "sun_find_west_v2" / "main.py",
        repo_root / "sun_find_west_v2" / "config" / "loader.py",
    ]
    imported = set().union(*(_imported_path_names(module) for module in modules))
    assert imported, "paths からの import が見つかりません"

    missing = {name for name in imported if not hasattr(paths, name)}
    assert not missing, f"paths.py に無い名前を import しています: {sorted(missing)}"


def test_bundled_asi_dll_is_amd64() -> None:
    """同梱する ASICamera2.dll が 64bit (AMD64) である。"""
    dll = Path(paths.__file__).resolve().parent / "camera" / "bin" / paths.DLL_NAME
    data = dll.read_bytes()
    pe_offset = int.from_bytes(data[0x3C:0x40], "little")
    assert data[pe_offset : pe_offset + 4] == b"PE\0\0"
    assert int.from_bytes(data[pe_offset + 4 : pe_offset + 6], "little") == 0x8664


def test_resolve_dll_prefers_bundled_file() -> None:
    """ソース／配布物では同梱 DLL を優先する。"""
    assert paths.resolve_dll_path() == paths.dll_path()


def test_resolve_dll_falls_back_to_system_driver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同梱 DLL が無ければシステム導入されたドライバの DLL を使う。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)
    system_dll = tmp_path / "windows" / "System32" / paths.DLL_NAME
    system_dll.parent.mkdir(parents=True)
    system_dll.write_bytes(b"dummy")
    monkeypatch.setenv("SystemRoot", str(tmp_path / "windows"))

    assert paths.resolve_dll_path() == system_dll


def test_resolve_dll_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同梱もシステムも無い場合は None を返す。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)
    monkeypatch.setenv("SystemRoot", str(tmp_path / "windows"))

    assert paths.resolve_dll_path() is None


def test_home_override_and_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SUN_WATCHING_HOME を上書きして出力先を作成できる。"""
    home = tmp_path / "custom"
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(home))

    paths.ensure_runtime_directories()

    assert paths.user_home() == home
    for directory in ("log", "data", "data/report"):
        assert (home / directory).is_dir()


def test_resolve_report_dir_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """空文字なら既定の data/report を使う。"""
    home = tmp_path / "custom"
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(home))

    assert paths.resolve_report_dir("") == home / "data" / "report"
    assert paths.resolve_report_dir(None) == home / "data" / "report"
    assert paths.resolve_report_dir("   ") == home / "data" / "report"


def test_resolve_report_dir_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """相対パスは出力先ルートからの相対パスとして扱う。"""
    home = tmp_path / "custom"
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(home))

    assert paths.resolve_report_dir("observations") == home / "observations"
    assert (
        paths.resolve_report_dir(Path("nested") / "reports")
        == home / "nested" / "reports"
    )


def test_resolve_report_dir_absolute(tmp_path: Path) -> None:
    """絶対パスはそのまま使う。"""
    absolute = tmp_path / "elsewhere" / "reports"
    assert paths.resolve_report_dir(str(absolute)) == absolute
