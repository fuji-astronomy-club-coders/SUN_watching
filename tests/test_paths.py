"""パス解決と出力先ディレクトリ作成のテスト。"""

from __future__ import annotations

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
