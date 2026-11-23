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
