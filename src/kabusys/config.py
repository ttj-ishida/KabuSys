"""
環境変数・設定管理モジュール

.env ファイルまたは環境変数から設定値を読み込む。
使用例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
"""

import os
from pathlib import Path


def _find_project_root() -> Path:
    """.git または pyproject.toml を基準にプロジェクトルートを特定する。"""
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return cwd


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """1行をパースして (key, value) を返す。無効行は None。"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # export KEY=val 形式に対応
    if line.startswith("export "):
        line = line[7:].lstrip()
    key, sep, value = line.partition("=")
    if not sep:
        return None
    key = key.strip()
    value = value.strip()
    # インラインコメント対応（クォートなしの場合のみ）
    # '#' の直前がスペースまたはタブの場合のみコメントと認識
    if value and value[0] not in ("'", '"'):
        for i, ch in enumerate(value):
            if ch == "#" and (i == 0 or value[i - 1] in (" ", "\t")):
                value = value[:i].rstrip()
                break
    # クォート除去
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    if not key:
        return None
    return key, value


def _load_env_file(
    path: Path,
    override: bool = False,
    protected: frozenset[str] = frozenset(),
) -> None:
    """指定した .env ファイルを読み込む。

    Args:
        path: 読み込む .env ファイルのパス
        override: True の場合、既存の環境変数を上書きする（protected に含まれるキーは除く）
        protected: 上書き禁止のキーセット（OS環境変数を保護するために使用）
    """
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for raw in f:
            result = _parse_env_line(raw)
            if result is None:
                continue
            key, value = result
            if not override:
                # override=False: 未設定のキーのみセット
                if key not in os.environ:
                    os.environ[key] = value
            else:
                # override=True: protected（OS環境変数）以外は上書き
                if key not in protected:
                    os.environ[key] = value


# 読み込み優先順位: OS環境変数 > .env.local > .env
# OS環境変数を protected として保持し、どちらのファイルも上書き不可にする
_root = _find_project_root()
_os_keys = frozenset(os.environ.keys())
_load_env_file(_root / ".env", override=False, protected=_os_keys)
_load_env_file(_root / ".env.local", override=True, protected=_os_keys)


def _require(key: str) -> str:
    """必須の環境変数を取得。未設定時は ValueError を送出。"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(
            f"環境変数 '{key}' が設定されていません。"
            f".env.example を参考に .env を作成してください。"
        )
    return value


_VALID_ENVS = frozenset({"development", "paper_trading", "live"})
_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


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
        return Path(os.environ.get("DUCKDB_PATH", "data/kabusys.duckdb")).expanduser()

    @property
    def sqlite_path(self) -> Path:
        return Path(os.environ.get("SQLITE_PATH", "data/monitoring.db")).expanduser()

    # --- システム設定 ---
    @property
    def env(self) -> str:
        value = os.environ.get("KABUSYS_ENV", "development").lower()
        if value not in _VALID_ENVS:
            raise ValueError(
                f"KABUSYS_ENV の値が不正です: '{value}'. "
                f"有効な値: {sorted(_VALID_ENVS)}"
            )
        return value

    @property
    def log_level(self) -> str:
        value = os.environ.get("LOG_LEVEL", "INFO").upper()
        if value not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"LOG_LEVEL の値が不正です: '{value}'. "
                f"有効な値: {sorted(_VALID_LOG_LEVELS)}"
            )
        return value

    @property
    def is_live(self) -> bool:
        return self.env == "live"

    @property
    def is_paper(self) -> bool:
        return self.env == "paper_trading"

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


settings = Settings()
