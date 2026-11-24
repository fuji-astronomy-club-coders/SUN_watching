"""設定エディタで使うスキーマ解析・YAML 入出力・検証の処理。

GUI (``config.editor``) から切り離した純粋な処理だけを置く。tkinter を
import しないため、ヘッドレス環境でもテストできる。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

try:
    from .loader import ConfigError
except ImportError:  # PyInstaller 配布物では config がトップレベルモジュールになる
    from loader import ConfigError  # pyright: ignore[reportMissingImports]

SECTIONS_REQUIRING_OBJECT = ("object",)


@dataclass(frozen=True)
class FieldSpec:
    """スキーマ上の 1 つの入力項目。"""

    path: tuple[str, ...]
    kind: str
    description: str = ""
    minimum: float | None = None
    maximum: float | None = None
    enum: tuple[str, ...] = ()
    pattern: str | None = None

    @property
    def label(self) -> str:
        """設定ファイル上のキー名を返す。"""
        return self.path[-1]

    @property
    def dotted_path(self) -> str:
        """``Camera.basic_parameters.exposure`` 形式のパスを返す。"""
        return ".".join(self.path)


def _schema_type(schema: dict[str, Any]) -> str:
    raw_type = schema.get("type", "string")
    if isinstance(raw_type, list):
        candidates = [item for item in raw_type if item != "null"]
        return str(candidates[0]) if candidates else "string"
    return str(raw_type)


def _field_from_schema(path: tuple[str, ...], schema: dict[str, Any]) -> FieldSpec:
    raw_enum = schema.get("enum") or []
    enum = tuple(str(item) for item in raw_enum)
    raw_type = _schema_type(schema)
    if enum:
        kind = "enum"
    elif raw_type == "boolean":
        kind = "boolean"
    elif raw_type == "integer":
        kind = "integer"
    elif raw_type == "number":
        kind = "number"
    else:
        kind = "string"

    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    return FieldSpec(
        path=path,
        kind=kind,
        description=str(schema.get("description", "")),
        minimum=float(minimum) if isinstance(minimum, int | float) else None,
        maximum=float(maximum) if isinstance(maximum, int | float) else None,
        enum=enum,
        pattern=str(schema["pattern"]) if "pattern" in schema else None,
    )


def iter_fields(schema: dict[str, Any]) -> list[FieldSpec]:
    """スキーマを走査し、編集対象の項目を定義順に返す。

    Parameters
    ----------
    schema : dict[str, Any]
        JSON Schema (Draft 7)。

    Returns
    -------
    list[FieldSpec]
        入れ子の object を展開した末端の項目。
    """

    def walk(
        properties: dict[str, Any],
        prefix: tuple[str, ...],
    ) -> list[FieldSpec]:
        fields: list[FieldSpec] = []
        for name, child in properties.items():
            path = (*prefix, str(name))
            if _schema_type(child) in SECTIONS_REQUIRING_OBJECT:
                fields.extend(walk(child.get("properties", {}), path))
            else:
                fields.append(_field_from_schema(path, child))
        return fields

    return walk(schema.get("properties", {}), ())


def is_hex_color(field: FieldSpec) -> bool:
    """色指定 (``#RRGGBB`` / ``#RGB``) の項目かどうかを返す。"""
    if field.pattern is None:
        return False
    return "A-Fa-f0-9" in field.pattern and "#" in field.pattern


def default_value(field: FieldSpec) -> Any:  # noqa: ANN401
    """項目が設定ファイルに無いときに表示する値を返す。"""
    if field.kind == "boolean":
        return False
    if field.kind == "enum":
        return field.enum[0] if field.enum else ""
    if field.kind in {"integer", "number"}:
        return int(field.minimum) if field.minimum is not None else 0
    if is_hex_color(field):
        return "#FFFFFF"
    return ""


def get_value(data: dict[str, Any], field: FieldSpec) -> Any:  # noqa: ANN401
    """入れ子の dict から項目の値を取り出す。無ければ既定値を返す。"""
    current: Any = data
    for key in field.path:
        if not isinstance(current, dict) or key not in current:
            return default_value(field)
        current = current[key]
    return current


def parse_value(field: FieldSpec, raw: Any) -> Any:  # noqa: ANN401
    """GUI の入力値をスキーマに合う型へ変換する。

    Raises
    ------
    ValueError
        整数・数値として解釈できない場合。
    """
    if field.kind == "boolean":
        return bool(raw)
    if field.kind == "integer":
        text = str(raw).strip()
        try:
            return int(text)
        except ValueError as e:
            msg = f"{field.dotted_path} は整数で入力してください: {text!r}"
            raise ValueError(msg) from e
    if field.kind == "number":
        text = str(raw).strip()
        try:
            return float(text)
        except ValueError as e:
            msg = f"{field.dotted_path} は数値で入力してください: {text!r}"
            raise ValueError(msg) from e
    return str(raw)


def build_config(
    schema: dict[str, Any],
    values: dict[tuple[str, ...], Any],
) -> dict[str, Any]:
    """項目の値から、スキーマと同じ順序の設定 dict を組み立てる。

    Parameters
    ----------
    schema : dict[str, Any]
        JSON Schema (Draft 7)。
    values : dict[tuple[str, ...], Any]
        ``iter_fields`` が返すパスをキーにした値。

    Returns
    -------
    dict[str, Any]
        ネストした設定データ。
    """

    def walk(
        properties: dict[str, Any],
        prefix: tuple[str, ...],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, child in properties.items():
            path = (*prefix, str(name))
            if _schema_type(child) in SECTIONS_REQUIRING_OBJECT:
                result[str(name)] = walk(child.get("properties", {}), path)
            else:
                result[str(name)] = values[path]
        return result

    return walk(schema.get("properties", {}), ())


def find_unknown_keys(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """スキーマに定義されていないキーのパスを返す。"""

    def walk(
        current: dict[str, Any],
        properties: dict[str, Any],
        prefix: tuple[str, ...],
    ) -> list[str]:
        unknown: list[str] = []
        for key, value in current.items():
            path = (*prefix, str(key))
            child = properties.get(key)
            if child is None:
                unknown.append(".".join(path))
            elif isinstance(value, dict) and _schema_type(child) == "object":
                unknown.extend(walk(value, child.get("properties", {}), path))
        return unknown

    return walk(data, schema.get("properties", {}), ())


def load_schema(schema_path: Path | str) -> dict[str, Any]:
    """JSON Schema を読み込み、スキーマ自体の妥当性も確認する。

    Raises
    ------
    ConfigError
        読み込みまたはスキーマ検証に失敗した場合。
    """
    path = Path(schema_path)
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        msg = f"スキーマを読み込めません: {path}: {e}"
        raise ConfigError(msg) from e
    try:
        Draft7Validator.check_schema(schema)
    except Exception as e:
        msg = f"スキーマが JSON Schema (Draft 7) として不正です: {path}: {e}"
        raise ConfigError(msg) from e
    if not isinstance(schema, dict):
        msg = f"スキーマのルートがオブジェクトではありません: {path}"
        raise ConfigError(msg)
    return schema


def load_yaml_config(config_path: Path | str) -> dict[str, Any]:
    """YAML 設定ファイルを検証せずに読み込む。

    エディタは不正な設定を修正するために起動できる必要があるため、
    ここではスキーマ検証を行わない。

    Raises
    ------
    ConfigError
        ファイルが無い、YAML が不正、またはルートがマッピングでない場合。
    """
    path = Path(config_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        msg = f"設定ファイルを読み込めません: {path}: {e}"
        raise ConfigError(msg) from e
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        msg = f"設定ファイルが YAML として不正です: {path}\n{e}"
        raise ConfigError(msg) from e
    if not isinstance(data, dict):
        msg = f"設定ファイルのルートはマッピングである必要があります: {path}"
        raise ConfigError(msg)
    return data


def validate_config(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """設定データをスキーマで検証し、エラーメッセージの一覧を返す。"""
    errors = sorted(
        Draft7Validator(schema).iter_errors(data),
        key=lambda err: [str(part) for part in err.absolute_path],
    )
    messages: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "(root)"
        messages.append(f"{location}: {error.message}")
    return messages


def _dump_section(
    data: dict[str, Any],
    schema: dict[str, Any],
    indent: int,
) -> list[str]:
    lines: list[str] = []
    padding = " " * indent
    properties = schema.get("properties", {})
    for key, value in data.items():
        child = properties.get(str(key), {})
        description = str(child.get("description", ""))
        if description:
            lines.extend(f"{padding}# {line}" for line in description.splitlines())
        if isinstance(value, dict):
            lines.append(f"{padding}{key}:")
            lines.extend(_dump_section(value, child, indent + 2))
        else:
            dumped = yaml.safe_dump(
                {key: value},
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).rstrip("\n")
            lines.extend(f"{padding}{line}" for line in dumped.splitlines())
    return lines


def dump_config(data: dict[str, Any], schema: dict[str, Any]) -> str:
    """設定データを、スキーマの説明をコメントにした YAML 文字列にする。"""
    header = [
        "# SUN_watching sun_find_west_v2 設定ファイル",
        "#",
        "# run.py が起動時に読み込み、config_schema.json で検証する。",
        "# このファイルは設定エディタ (python run.py --edit-config) で保存された。",
        "# コメントは config_schema.json の説明から再生成される。",
        "",
    ]
    lines = header + _dump_section(data, schema, 0)
    return "\n".join(lines) + "\n"


def save_config(
    config_path: Path | str,
    data: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    """設定を検証してから YAML へ安全に書き込む。

    一時ファイルへ書いてから置き換えるため、書き込み途中で失敗しても
    元の設定ファイルは壊れない。

    Raises
    ------
    ConfigError
        スキーマ検証に失敗した場合。
    OSError
        書き込みに失敗した場合。
    """
    path = Path(config_path)
    errors = validate_config(data, schema)
    if errors:
        msg = f"設定がスキーマに違反しています: {path}\n" + "\n".join(
            f"  - {error}" for error in errors
        )
        raise ConfigError(msg)

    text = dump_config(data, schema)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)
