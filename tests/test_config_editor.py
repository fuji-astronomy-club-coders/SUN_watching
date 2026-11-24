"""設定エディタのモデル処理と GUI のスモークテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from sun_find_west_v2.config.editor_model import (
    build_config,
    default_value,
    dump_config,
    find_unknown_keys,
    get_value,
    iter_fields,
    load_schema,
    load_yaml_config,
    parse_value,
    save_config,
    validate_config,
)
from sun_find_west_v2.config.loader import (
    DEFAULT_CONFIG_PATH,
    SCHEMA_PATH,
    ConfigError,
    load_config,
)

SCHEMA = load_schema(SCHEMA_PATH)
CONFIG = load_yaml_config(DEFAULT_CONFIG_PATH)


def test_iter_fields_expands_nested_sections() -> None:
    """入れ子の object を末端まで展開する。"""
    fields = iter_fields(SCHEMA)
    paths = {field.dotted_path for field in fields}

    assert "Camera.basic_parameters.exposure" in paths
    assert "Run.camera_source.dummy_camera" in paths
    assert "sun_find_west_v2.Visualizer.grid_color" in paths
    assert "Camera.basic_parameters" not in paths
    assert "Run.output.report_dir" in paths
    assert len(fields) == 25


def test_iter_fields_keeps_schema_order() -> None:
    """入力欄の順序がスキーマの定義順になる。"""
    fields = iter_fields(SCHEMA)

    assert fields[0].dotted_path == "Camera.basic_parameters.exposure"
    assert fields[-1].dotted_path == "sun_find_west_v2.Visualizer.grid_alpha"


def test_get_value_falls_back_to_schema_defaults() -> None:
    """存在しない項目は型に応じた既定値を返す。"""
    fields = {field.dotted_path: field for field in iter_fields(SCHEMA)}

    assert get_value({}, fields["Camera.basic_parameters.exposure"]) == 32
    assert get_value({}, fields["Camera.image_format.img_type"]) == "RAW8"
    assert get_value({}, fields["Run.camera_source.dummy_camera"]) is False
    assert get_value({}, fields["sun_find_west_v2.Visualizer.grid_color"]) == "#FFFFFF"
    assert default_value(fields["sun_find_west_v2.Visualizer.grid_alpha"]) == 0


def test_build_config_round_trips_shipped_config() -> None:
    """読み込んだ値を組み立て直すと元の設定に戻る。"""
    fields = iter_fields(SCHEMA)
    values = {field.path: get_value(CONFIG, field) for field in fields}

    assert build_config(SCHEMA, values) == CONFIG


def test_dump_config_includes_schema_descriptions_and_quotes_color() -> None:
    """YAML には説明コメントが付き、色は引用符で囲まれる。"""
    text = dump_config(CONFIG, SCHEMA)

    assert "# ASI_EXPOSURE: 露出時間 (μs)" in text
    assert "grid_color: '#FFFFFF'" in text
    assert "light_threshod: 50" in text


def test_save_config_is_validated_and_reloadable(tmp_path: Path) -> None:
    """保存した設定をローダーで再検証できる。"""
    target = tmp_path / "config.yaml"

    save_config(target, CONFIG, SCHEMA)
    loaded = load_config(target)

    assert loaded == CONFIG


def test_save_config_rejects_invalid_data(tmp_path: Path) -> None:
    """範囲外の値は書き込まずに ConfigError にする。"""
    broken = {**CONFIG, "Camera": {**CONFIG["Camera"]}}
    broken["Camera"]["basic_parameters"] = {
        **CONFIG["Camera"]["basic_parameters"],
        "exposure": 1,
    }

    with pytest.raises(ConfigError, match="exposure"):
        save_config(tmp_path / "config.yaml", broken, SCHEMA)
    assert not (tmp_path / "config.yaml").exists()


def test_validate_config_reports_all_errors() -> None:
    """複数の違反をまとめて報告する。"""
    broken = {**CONFIG, "Camera": {**CONFIG["Camera"]}}
    broken["Camera"]["basic_parameters"] = {
        **CONFIG["Camera"]["basic_parameters"],
        "exposure": 1,
        "gain": 999,
    }

    errors = validate_config(broken, SCHEMA)

    assert any("exposure" in error for error in errors)
    assert any("gain" in error for error in errors)


def test_find_unknown_keys() -> None:
    """スキーマに無いキーを検出する。"""
    data = {**CONFIG, "Camera": {**CONFIG["Camera"]}}
    data["Camera"]["basic_parameters"] = {
        **CONFIG["Camera"]["basic_parameters"],
        "gian": 0,
    }

    assert find_unknown_keys(data, SCHEMA) == ["Camera.basic_parameters.gian"]


@pytest.mark.parametrize(
    ("path", "raw", "expected"),
    [
        ("Camera.basic_parameters.exposure", "250", 250),
        ("sun_find_west_v2.Visualizer.grid_alpha", "0.25", 0.25),
        ("Run.camera_source.dummy_camera", True, True),
        ("Camera.image_format.img_type", "RAW16", "RAW16"),
    ],
)
def test_parse_value_converts_widget_values(
    path: str,
    raw: object,
    expected: object,
) -> None:
    """入力欄の文字列をスキーマの型へ変換する。"""
    fields = {field.dotted_path: field for field in iter_fields(SCHEMA)}

    assert parse_value(fields[path], raw) == expected


def test_parse_value_rejects_non_numeric_text() -> None:
    """数値欄に文字が入ったら ValueError にする。"""
    fields = {field.dotted_path: field for field in iter_fields(SCHEMA)}

    with pytest.raises(ValueError, match="整数"):
        parse_value(fields["Camera.basic_parameters.exposure"], "abc")


def test_gui_round_trip(tmp_path: Path) -> None:
    """GUI を組み立て、値を変更して保存できる。"""
    tkinter = pytest.importorskip("tkinter")
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip("GUI を起動できない環境")

    root.withdraw()
    try:
        from sun_find_west_v2.config.editor import ConfigEditorApp

        app = ConfigEditorApp(root, DEFAULT_CONFIG_PATH, SCHEMA_PATH)
        assert app.config_data() == CONFIG

        app.variables[("Camera", "basic_parameters", "exposure")].set("250")
        app.variables[("Run", "camera_source", "dummy_camera")].set(False)
        updated = app.config_data()
        assert updated["Camera"]["basic_parameters"]["exposure"] == 250
        assert updated["Run"]["camera_source"]["dummy_camera"] is False

        target = tmp_path / "config.yaml"
        app.config_path = target
        assert app.save() is True
        assert load_config(target)["Camera"]["basic_parameters"]["exposure"] == 250
    finally:
        root.destroy()
