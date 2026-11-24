"""ソース実行と PyInstaller 配布物で共通して使うパスを提供する。

配布物では設定ファイルや DLL を実行ファイル直属の ``_internal`` 以下に
配置する。一方、ログや解析結果はユーザーが書き込み可能な
``%LOCALAPPDATA%\\SUN_watching`` (または ``SUN_WATCHING_HOME``) に保存する。
これにより PATH の変更や管理者権限なしで起動できる。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "SUN_watching"
HOME_ENV_VAR = "SUN_WATCHING_HOME"
DLL_NAME = "ASICamera2.dll"


def is_frozen() -> bool:
    """PyInstaller の配布物として実行中かどうかを返す。"""
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """設定ファイルと DLL が置かれているディレクトリを返す。

    Returns
    -------
    Path
        ソース実行時は ``sun_find_west_v2`` パッケージのディレクトリ、
        配布物では PyInstaller の展開先ディレクトリ。
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_user_home() -> Path:
    """出力先の既定ルートを返す。

    Returns
    -------
    Path
        配布物では ``%LOCALAPPDATA%\\SUN_watching``、ソース実行時はリポジトリのルート。
    """
    if not is_frozen():
        return Path(__file__).resolve().parent.parent

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def user_home() -> Path:
    """出力先ルートを返す。``SUN_WATCHING_HOME`` で上書きできる。"""
    override = os.environ.get(HOME_ENV_VAR)
    base = Path(override).expanduser() if override else default_user_home()
    return base.resolve()


def config_dir() -> Path:
    """設定ファイルの置き場所を返す。"""
    return resource_dir() / "config"


def config_path() -> Path:
    """既定の YAML 設定ファイルのパスを返す。"""
    return config_dir() / "config.yaml"


def schema_path() -> Path:
    """JSON Schema のパスを返す。"""
    return config_dir() / "config_schema.json"


def dll_path() -> Path:
    """同梱の ASICamera2.dll のパスを返す。"""
    return resource_dir() / "camera" / "bin" / DLL_NAME


def system_dll_path() -> Path | None:
    """ZWO ドライバがシステムへ導入した ASICamera2.dll のパスを返す。

    同梱 DLL が無い場合のフォールバック用。見つからなければ None。
    """
    if sys.platform != "win32":
        return None
    system_root = os.environ.get("SystemRoot")
    if not system_root:
        return None
    candidate = Path(system_root) / "System32" / DLL_NAME
    if candidate.is_file():
        return candidate
    return None


def resolve_dll_path() -> Path | None:
    """実際に使用する ASICamera2.dll を返す。

    同梱の DLL を優先し、無ければシステムにインストールされたドライバの
    DLL を使う。どちらも無ければ None。
    """
    bundled = dll_path()
    if bundled.is_file():
        return bundled
    return system_dll_path()


def log_dir() -> Path:
    """ログの出力先ディレクトリを返す。"""
    return user_home() / "log"


def data_dir() -> Path:
    """解析結果の出力先ディレクトリを返す。"""
    return user_home() / "data"


def report_dir() -> Path:
    """日付別レポートの親ディレクトリを返す。"""
    return data_dir() / "report"


def ensure_runtime_directories() -> None:
    """ログ・データ用ディレクトリを作成する。既存の場合は何もしない。"""
    for directory in (log_dir(), data_dir(), report_dir()):
        directory.mkdir(parents=True, exist_ok=True)


# 後方互換のための定数。実行時の上書きを反映するため、必要なら関数を使う。
CONFIG_DIR = config_dir()
DEFAULT_CONFIG_PATH = config_path()
SCHEMA_PATH = schema_path()
DLL_PATH = dll_path()
