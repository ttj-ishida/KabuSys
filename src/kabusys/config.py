"""
環境変数・設定管理モジュール

.env ファイルまたは環境変数から設定値を読み込む。
使用例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
"""

import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """シンプルな .env パーサー（python-dotenv 非依存）。"""
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# プロジェクトルートの .env を自動ロード
_project_root = Path(__file__).resolve().parents[2]
_load_env_file(_project_root / ".env")


def _require(key: str) -> str:
    """必須の環境変数を取得。未設定時は ValueError を送出。"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(
            f"環境変数 '{key}' が設定されていません。"
            f".env.example を参考に .env を作成してください。"
        )
    return value


class Settings:
    """アプリケーション設定。環境変数から値を取得する。"""

    # --- J-Quants API ---
    @property
    def jquants_refresh_token(self) -> str:
        return _require("JQUANTS_REFRESH_TOKEN")

    # --- kabuステーション API ---
    @property
    def kabu_api_password(self) -> str:
        return _require("KABU_API_PASSWORD")

    @property
    def kabu_api_base_url(self) -> str:
        return os.environ.get("KABU_API_BASE_URL", "http://localhost:18080/kabusapi")

    # --- Slack ---
    @property
    def slack_bot_token(self) -> str:
        return _require("SLACK_BOT_TOKEN")

    @property
    def slack_channel_id(self) -> str:
        return _require("SLACK_CHANNEL_ID")

    # --- データベース ---
    @property
    def duckdb_path(self) -> Path:
        return Path(os.environ.get("DUCKDB_PATH", "data/kabusys.duckdb"))

    @property
    def sqlite_path(self) -> Path:
        return Path(os.environ.get("SQLITE_PATH", "data/monitoring.db"))

    # --- システム設定 ---
    @property
    def env(self) -> str:
        return os.environ.get("KABUSYS_ENV", "development")

    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO")

    @property
    def is_live(self) -> bool:
        return self.env == "live"


settings = Settings()
