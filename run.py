"""SUN_watching sun_find_west_v2 の実行用エントリポイント。

設定ファイル(YAML)の読み込みとスキーマ検証はこのファイルだけが行い、
検証済みの設定を ``main(config)`` に渡して起動する。
ダミーカメラを使うかどうかも設定の ``Run`` > ``camera_source`` > ``dummy_camera`` で決まる
(True ならダミーカメラ、False なら実機ASIカメラ)。

使い方::

    python run.py
    python run.py --config path/to/config.yaml
    SUN_watching.exe --check-config
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = ROOT / "sun_find_west_v2"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """コマンドライン引数を解析する。

    Parameters
    ----------
    argv : list[str] | None
        引数のリスト。None なら sys.argv を使う。

    Returns
    -------
    argparse.Namespace
        ``config`` に設定ファイルのパス(未指定なら None)、
        ``check_config`` に検証のみ行うかどうかを持つ。
    """
    parser = argparse.ArgumentParser(description="sun_find_west_v2 を起動する")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML設定ファイル (省略時は sun_find_west_v2/config/config.yaml)",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="設定とスキーマだけを検証して終了する (配布物の動作確認用)",
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="起動に必要なモジュールを import できるか確認して終了する (配布物の動作確認用)",
    )
    return parser.parse_args(argv)


def main() -> None:
    """設定を読み込んで検証し、main() に渡して起動する。"""
    args = parse_args()

    if str(PACKAGE_DIR) not in sys.path:
        sys.path.insert(0, str(PACKAGE_DIR))

    # main.py 側と同じ import 名(config.*)で読み込む
    from config.loader import (  # pyright: ignore[reportMissingImports]
        DEFAULT_CONFIG_PATH,
        ConfigError,
        load_config,
    )
    from paths import ensure_runtime_directories  # pyright: ignore[reportMissingImports]

    ensure_runtime_directories()

    config_path = args.config or DEFAULT_CONFIG_PATH
    try:
        config = load_config(config_path)
    except ConfigError as e:
        sys.exit(f"[run.py] {e}")
    print(f"[run.py] config={config_path}")

    if args.check_config:
        print("[run.py] OK: config and schema are valid")
        return

    if args.check_imports:
        from main import main as _run_main  # noqa: F401  # pyright: ignore[reportMissingImports]

        print("[run.py] OK: startup modules imported successfully")
        return

    from main import main as run_main  # pyright: ignore[reportMissingImports]

    run_main(config)


if __name__ == "__main__":
    main()
