"""run.py のエントリポイントのテスト。"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import run


def test_parse_args_check_config() -> None:
    """--check-config を解析できる。"""
    args = run.parse_args(["--check-config"])
    assert args.check_config is True
    assert args.config is None
    assert args.edit_config is False


def test_parse_args_edit_config() -> None:
    """--edit-config と --config-editor の別名を解析できる。"""
    for flag in ("--edit-config", "--config-editor"):
        args = run.parse_args([flag])
        assert args.edit_config is True
        assert run.edit_config_requested(args) is True


def test_edit_config_can_be_requested_by_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数 SUN_WATCHING_EDIT_CONFIG でもエディタを起動できる。"""
    monkeypatch.setenv("SUN_WATCHING_EDIT_CONFIG", "1")
    args = run.parse_args([])

    assert run.edit_config_requested(args) is True


def test_edit_config_starts_editor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--edit-config が設定エディタへ設定パスを渡す。"""
    calls: dict[str, Path] = {}
    editor = types.ModuleType("config.editor")

    def fake_run_editor(config_path: Path, schema_path: Path) -> None:
        calls["config"] = config_path
        calls["schema"] = schema_path

    editor.run_editor = fake_run_editor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "config.editor", editor)
    monkeypatch.setenv("SUN_WATCHING_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["run.py", "--edit-config"])

    run.main()

    assert calls["config"].name == "config.yaml"
    assert calls["schema"].name == "config_schema.json"


def test_check_config_exits_before_gui(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """設定検証のみで終了し、出力先ディレクトリを用意する。"""
    monkeypatch.setenv("SUN_WATCHING_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["run.py", "--check-config"])

    run.main()

    captured = capsys.readouterr()
    assert "OK: config and schema are valid" in captured.out
    repo_root = Path(run.__file__).resolve().parent
    assert (repo_root / "log").is_dir()
    assert not (tmp_path / "log").exists()
    assert (tmp_path / "data").is_dir()
