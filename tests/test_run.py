"""run.py のエントリポイントのテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import run


def test_parse_args_check_config() -> None:
    """--check-config を解析できる。"""
    args = run.parse_args(["--check-config"])
    assert args.check_config is True
    assert args.config is None


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
    assert (tmp_path / "log").is_dir()
    assert (tmp_path / "data").is_dir()
