"""config.yaml を編集するための tkinter GUI。

``python run.py --edit-config`` で起動する。スキーマ (``config_schema.json``)
から入力欄を自動生成するため、項目を追加したときもこのファイルの変更は
不要。保存時は必ずスキーマ検証を行い、違反があれば書き込まない。
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any

try:
    from .editor_model import (
        FieldSpec,
        build_config,
        find_unknown_keys,
        get_value,
        is_hex_color,
        iter_fields,
        load_schema,
        load_yaml_config,
        parse_value,
        save_config,
        validate_config,
    )
    from .loader import ConfigError
except ImportError:  # PyInstaller 配布物では config がトップレベルモジュールになる
    from editor_model import (  # pyright: ignore[reportMissingImports]
        FieldSpec,
        build_config,
        find_unknown_keys,
        get_value,
        is_hex_color,
        iter_fields,
        load_schema,
        load_yaml_config,
        parse_value,
        save_config,
        validate_config,
    )
    from loader import ConfigError  # pyright: ignore[reportMissingImports]

TAB_LABELS = {
    "Camera": "カメラ",
    "Run": "実行",
    "sun_find_west_v2": "解析・表示",
}
GROUP_LABELS = {
    "basic_parameters": "基本パラメータ",
    "transfer_settings": "転送設定",
    "auto_control": "自動制御",
    "image_format": "画像形式",
    "camera_source": "カメラ入力",
    "Analyzer": "角度解析",
    "MIN2ver2": "太陽検出",
    "Visualizer": "画面表示",
}
FILE_TYPES = [
    ("YAML 設定ファイル", "*.yaml *.yml"),
    ("すべてのファイル", "*.*"),
]
MAX_ERRORS_IN_DIALOG = 20


class ConfigEditorApp:
    """設定ファイルを編集するメインウィンドウ。"""

    def __init__(
        self,
        root: tk.Tk,
        config_path: Path | str,
        schema_path: Path | str,
    ) -> None:
        """スキーマを読み込み、入力欄と現在の設定値を組み立てる。"""
        self.root = root
        self.config_path = Path(config_path)
        self.schema_path = Path(schema_path)
        self.schema = load_schema(self.schema_path)
        self.fields = iter_fields(self.schema)
        self.field_specs = {field.path: field for field in self.fields}
        self.variables: dict[tuple[str, ...], tk.Variable] = {}
        self.loaded_data: dict[str, Any] = {}
        self.unknown_keys: list[str] = []
        self._loading = False
        self._dirty = False
        self._read_error: str | None = None

        self.root.title("SUN_watching 設定エディタ")
        self.root.geometry("960x740")
        self.root.minsize(780, 560)

        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.hint_var = tk.StringVar()
        self._read_initial_data()
        self._build_ui()
        self._apply_loaded_data()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        """ウィンドウ全体のレイアウトを作る。"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(14, 12, 14, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="設定ファイル:").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.path_var).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(header, text="開く...", command=self.open_file).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Button(header, text="再読み込み", command=self.reload).grid(
            row=0, column=3, padx=(8, 0)
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10)

        properties = self.schema.get("properties", {})
        for section_name, section_schema in properties.items():
            if section_schema.get("type") != "object":
                continue
            tab = ttk.Frame(self.notebook, padding=2)
            self.notebook.add(
                tab,
                text=TAB_LABELS.get(str(section_name), str(section_name)),
            )
            body = self._make_scrollable(tab)
            self._build_section(body, section_schema, (str(section_name),))

        footer = ttk.Frame(self.root, padding=(14, 6, 14, 12))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(
            footer,
            textvariable=self.hint_var,
            foreground="#4a5568",
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(
            footer,
            textvariable=self.status_var,
            wraplength=900,
            justify="left",
        )
        self.status_label.grid(row=1, column=0, sticky="w", pady=(4, 8))

        buttons = ttk.Frame(footer)
        buttons.grid(row=2, column=0, sticky="e")
        ttk.Button(buttons, text="検証", command=self.validate).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="別名で保存...", command=self.save_as).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(buttons, text="保存", command=self.save).pack(side="left")

    def _make_scrollable(self, parent: ttk.Frame) -> ttk.Frame:
        """縦スクロールできるフレームを作り、中身を入れる領域を返す。"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        body = ttk.Frame(canvas, padding=(6, 6, 10, 10))
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def resize_body(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def update_scroll_region(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_wheel(event: tk.Event) -> None:
            delta = int(getattr(event, "delta", 0))
            canvas.yview_scroll(int(-delta / 120), "units")

        def bind_wheel(_event: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", on_wheel)

        def unbind_wheel(_event: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Configure>", resize_body)
        body.bind("<Configure>", update_scroll_region)
        canvas.bind("<Enter>", bind_wheel)
        canvas.bind("<Leave>", unbind_wheel)
        return body

    def _build_section(
        self,
        parent: ttk.Frame,
        section_schema: dict[str, Any],
        prefix: tuple[str, ...],
    ) -> None:
        """1 つのタブ (トップレベルのセクション) を組み立てる。"""
        properties = section_schema.get("properties", {})
        direct_fields = [
            (name, child) for name, child in properties.items() if child.get("type") != "object"
        ]
        group_names = [name for name, child in properties.items() if child.get("type") == "object"]

        if direct_fields:
            frame = ttk.LabelFrame(parent, text="設定", padding=(12, 8))
            frame.pack(fill="x", padx=4, pady=(4, 8))
            frame.columnconfigure(1, weight=1)
            for row, (name, _child) in enumerate(direct_fields):
                self._add_field(frame, row, (*prefix, str(name)))

        for group_name in group_names:
            group_schema = properties[group_name]
            frame = ttk.LabelFrame(
                parent,
                text=GROUP_LABELS.get(str(group_name), str(group_name)),
                padding=(12, 8),
            )
            frame.pack(fill="x", padx=4, pady=(4, 8))
            frame.columnconfigure(1, weight=1)
            for row, name in enumerate(group_schema.get("properties", {})):
                self._add_field(frame, row, (*prefix, str(group_name), str(name)))

    def _add_field(
        self,
        parent: tk.Widget,
        row: int,
        path: tuple[str, ...],
    ) -> None:
        """1 項目分のラベルと入力ウィジェットを配置する。"""
        field = self.field_specs[path]
        label = ttk.Label(parent, text=field.label)
        label.grid(row=row, column=0, sticky="w", padx=(0, 18), pady=4)
        widget = self._make_widget(parent, field)
        widget.grid(row=row, column=1, sticky="ew", pady=4)

        description = field.description
        if description:
            label.bind(
                "<Enter>",
                lambda _event, text=description: self.hint_var.set(text),
            )
            label.bind("<Leave>", lambda _event: self.hint_var.set(""))
            widget.bind(
                "<Enter>",
                lambda _event, text=description: self.hint_var.set(text),
            )
            widget.bind("<Leave>", lambda _event: self.hint_var.set(""))

    def _make_widget(self, parent: tk.Widget, field: FieldSpec) -> tk.Widget:
        """項目の型に応じた入力ウィジェットを作る。"""
        current = self._current_value_for(field)
        if field.kind == "boolean":
            variable = tk.BooleanVar(value=bool(current))
            self.variables[field.path] = variable
            self._watch(variable)
            return ttk.Checkbutton(parent, variable=variable, text="有効")

        if field.kind == "enum":
            variable = tk.StringVar(value=str(current))
            self.variables[field.path] = variable
            combo = ttk.Combobox(
                parent,
                textvariable=variable,
                values=list(field.enum),
                state="readonly",
                width=24,
            )
            self._watch(variable)
            return combo

        if field.kind in {"integer", "number"}:
            variable = tk.StringVar(value=self._format_value(field, current))
            self.variables[field.path] = variable
            increment = 1 if field.kind == "integer" else 0.1
            spinbox = ttk.Spinbox(
                parent,
                textvariable=variable,
                from_=field.minimum if field.minimum is not None else 0,
                to=field.maximum if field.maximum is not None else 1_000_000_000,
                increment=increment,
                width=24,
            )
            self._watch(variable)
            return spinbox

        variable = tk.StringVar(value=str(current))
        self.variables[field.path] = variable
        self._watch(variable)
        if is_hex_color(field):
            color_frame = ttk.Frame(parent)
            color_frame.columnconfigure(0, weight=1)
            entry = ttk.Entry(color_frame, textvariable=variable)
            entry.grid(row=0, column=0, sticky="ew")
            ttk.Button(
                color_frame,
                text="色...",
                command=lambda var=variable: self._choose_color(var),
            ).grid(row=0, column=1, padx=(6, 0))
            return color_frame
        return ttk.Entry(parent, textvariable=variable)

    def _watch(self, variable: tk.Variable) -> None:
        """入力が変わったら未保存状態にする。"""

        def changed(*_args: object) -> None:
            if self._loading:
                return
            self._dirty = True
            self._update_title()

        variable.trace_add("write", changed)

    def _current_value_for(self, field: FieldSpec) -> Any:  # noqa: ANN401
        """読み込み済みの設定から項目の初期値を返す。"""
        return get_value(self.loaded_data, field)

    @staticmethod
    def _format_value(field: FieldSpec, value: Any) -> str:  # noqa: ANN401
        """設定値を入力欄に表示する文字列にする。"""
        if field.kind == "number":
            try:
                return f"{float(value):g}"
            except (TypeError, ValueError):
                return str(value)
        if field.kind == "integer" and isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _choose_color(self, variable: tk.StringVar) -> None:
        """色選択ダイアログで grid_color を設定する。"""
        initial = variable.get().strip() or "#FFFFFF"
        _rgb, color = colorchooser.askcolor(
            color=initial,
            parent=self.root,
            title="色を選択",
        )
        if color:
            variable.set(str(color).upper())

    # --------------------------------------------------------------- 読み込み

    def _read_initial_data(self) -> None:
        """ウィンドウを作る前に、設定ファイルを検証せずに読む。"""
        if not self.config_path.is_file():
            return
        try:
            self.loaded_data = load_yaml_config(self.config_path)
        except ConfigError as e:
            self._read_error = str(e)

    def _apply_loaded_data(self) -> None:
        """読み込んだ値を入力欄へ反映し、状態表示を更新する。"""
        self._loading = True
        try:
            for field in self.fields:
                value = get_value(self.loaded_data, field)
                variable = self.variables[field.path]
                if isinstance(variable, tk.BooleanVar):
                    variable.set(bool(value))
                else:
                    variable.set(self._format_value(field, value))
        finally:
            self._loading = False

        self.unknown_keys = (
            find_unknown_keys(self.loaded_data, self.schema) if self.loaded_data else []
        )
        self._dirty = False
        self.path_var.set(str(self.config_path))
        self._update_title()

        errors = validate_config(self.loaded_data, self.schema) if self.loaded_data else []
        if self._read_error:
            self._set_status(
                "設定ファイルを読み込めませんでした。空の設定として編集しています。",
                "error",
            )
        elif not self.config_path.is_file():
            self._set_status(
                f"ファイルが無いため、新規設定として開きました: {self.config_path}",
                "warn",
            )
        else:
            message = f"{len(self.fields)} 項目を読み込みました"
            if self.unknown_keys:
                message += f" / スキーマに無いキー: {', '.join(self.unknown_keys)}"
            if errors:
                message += f" / 検証エラー {len(errors)} 件 (保存前に修正してください)"
            self._set_status(message, "warn" if errors or self.unknown_keys else "ok")

        if self._read_error:
            messagebox.showerror(
                "読み込みエラー",
                f"{self._read_error}\n\n"
                "空の設定として編集を続けます。保存すると既存ファイルを上書きします。",
                parent=self.root,
            )
            self._read_error = None

    def _load(self, path: Path) -> None:
        """指定ファイルを読み込み、入力欄へ反映する。"""
        self.config_path = path
        self.loaded_data = {}
        if path.is_file():
            try:
                self.loaded_data = load_yaml_config(path)
            except ConfigError as e:
                self._read_error = str(e)
        self._apply_loaded_data()

    def reload(self) -> None:
        """ファイルを読み込み直す。"""
        if not self._confirm_discard():
            return
        self._load(self.config_path)

    def open_file(self) -> None:
        """別の YAML 設定ファイルを開く。"""
        if not self._confirm_discard():
            return
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="設定ファイルを開く",
            initialdir=str(self.config_path.parent),
            filetypes=FILE_TYPES,
        )
        if filename:
            self._load(Path(filename))

    # --------------------------------------------------------------- 保存

    def config_data(self) -> dict[str, Any]:
        """入力欄の内容を設定 dict に変換する。

        Raises
        ------
        ValueError
            数値欄に数値以外が入力されている場合。
        """
        values: dict[tuple[str, ...], Any] = {}
        for field in self.fields:
            values[field.path] = parse_value(field, self.variables[field.path].get())
        return build_config(self.schema, values)

    def validate(self) -> bool:
        """現在の入力を検証し、結果を表示する。"""
        try:
            data = self.config_data()
        except ValueError as e:
            messagebox.showerror("入力エラー", str(e), parent=self.root)
            self._set_status(str(e), "error")
            return False

        errors = validate_config(data, self.schema)
        if errors:
            detail = "\n".join(f"・{error}" for error in errors[:MAX_ERRORS_IN_DIALOG])
            if len(errors) > MAX_ERRORS_IN_DIALOG:
                detail += f"\n... ほか {len(errors) - MAX_ERRORS_IN_DIALOG} 件"
            messagebox.showerror(
                "設定の検証エラー",
                f"{len(errors)} 件のエラーがあります。\n\n{detail}",
                parent=self.root,
            )
            self._set_status(f"検証エラー {len(errors)} 件", "error")
            return False

        self._set_status("設定は有効です", "ok")
        return True

    def save(self) -> bool:
        """現在の設定を検証して保存する。"""
        try:
            data = self.config_data()
        except ValueError as e:
            messagebox.showerror("入力エラー", str(e), parent=self.root)
            self._set_status(str(e), "error")
            return False

        errors = validate_config(data, self.schema)
        if errors:
            detail = "\n".join(f"・{error}" for error in errors[:MAX_ERRORS_IN_DIALOG])
            if len(errors) > MAX_ERRORS_IN_DIALOG:
                detail += f"\n... ほか {len(errors) - MAX_ERRORS_IN_DIALOG} 件"
            messagebox.showerror(
                "保存できません",
                f"設定がスキーマに違反しています。\n\n{detail}",
                parent=self.root,
            )
            self._set_status(f"未保存: 検証エラー {len(errors)} 件", "error")
            return False

        target = self.config_path
        try:
            save_config(target, data, self.schema)
        except (ConfigError, OSError) as e:
            messagebox.showerror("保存エラー", str(e), parent=self.root)
            self._set_status(f"保存に失敗しました: {e}", "error")
            return False

        self._load(target)
        self._set_status(f"保存しました: {target}", "ok")
        return True

    def save_as(self) -> bool:
        """別のファイル名で保存する。"""
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="別名で保存",
            initialdir=str(self.config_path.parent),
            initialfile=self.config_path.name,
            defaultextension=".yaml",
            filetypes=FILE_TYPES,
        )
        if not filename:
            return False
        previous = self.config_path
        self.config_path = Path(filename)
        if not self.save():
            self.config_path = previous
            return False
        return True

    # --------------------------------------------------------------- 状態

    def _set_status(self, text: str, level: str = "info") -> None:
        """フッターの状態表示と色を更新する。"""
        colors = {
            "info": "#1f2937",
            "ok": "#166534",
            "warn": "#9a3412",
            "error": "#b91c1c",
        }
        self.status_var.set(text)
        self.status_label.configure(foreground=colors.get(level, colors["info"]))

    def _update_title(self) -> None:
        marker = " *" if self._dirty else ""
        self.root.title(f"SUN_watching 設定エディタ - {self.config_path.name}{marker}")

    def _confirm_discard(self) -> bool:
        """未保存の変更を破棄してよいか確認する。"""
        if not self._dirty:
            return True
        answer = messagebox.askyesnocancel(
            "未保存の変更",
            "変更が保存されていません。保存しますか?",
            parent=self.root,
        )
        if answer is None:
            return False
        if answer:
            return self.save()
        return True

    def _on_close(self) -> None:
        if self._confirm_discard():
            self.root.destroy()


def _configure_style(root: tk.Tk) -> None:
    """Windows ではネイティブ風、それ以外では clam テーマを使う。"""
    style = ttk.Style(root)
    themes = style.theme_names()
    for name in ("vista", "clam", "default"):
        if name in themes:
            style.theme_use(name)
            break
    style.configure("TNotebook.Tab", padding=(14, 6))
    root.option_add("*Font", ("Yu Gothic UI", 10))


def run_editor(config_path: Path | str, schema_path: Path | str) -> None:
    """設定エディタを起動する。"""
    try:
        root = tk.Tk()
    except tk.TclError as e:
        raise SystemExit(f"[config.editor] GUI を起動できません: {e}") from e

    try:
        _configure_style(root)
        ConfigEditorApp(root, config_path, schema_path)
        root.mainloop()
    except ConfigError as e:
        messagebox.showerror("設定エディタ", str(e), parent=root)
        raise SystemExit(1) from e
    finally:
        with contextlib.suppress(tk.TclError):
            root.destroy()
