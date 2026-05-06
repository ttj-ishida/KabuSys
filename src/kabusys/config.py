"""
環境変数・設定管理モジュール

.env ファイルまたは環境変数から設定値を読み込む。
使用例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
"""

from __future__ import annotations

import os
from pathlib import Path


def _find_project_root() -> Path | None:
    """.git または pyproject.toml を基準にプロジェクトルートを特定する。

    __file__ を起点に親ディレクトリを探索するため、
    CWDに依存せずパッケージ配布後も正しく動作する。
    見つからない場合は None を返す（自動ロードをスキップ）。
    """
    base = Path(__file__).resolve()
    for p in base.parents:
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
    return None


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
    if value and value[0] in ("'", '"'):
        # クォートあり: バックスラッシュエスケープを考慮して対応する閉じクォートを探す
        # 以降（インラインコメント含む）は無視する
        q = value[0]
        i, chars = 1, []
        while i < len(value):
            ch = value[i]
            if ch == "\\" and i + 1 < len(value):
                # エスケープシーケンス: 次の文字をそのまま取り込む
                chars.append(value[i + 1])
                i += 2
            elif ch == q:
                break
            else:
                chars.append(ch)
                i += 1
        value = "".join(chars)
    else:
        # クォートなし: '#' の直前がスペースまたはタブの場合のみコメントと認識
        for i, ch in enumerate(value):
            if ch == "#" and (i == 0 or value[i - 1] in (" ", "\t")):
                value = value[:i].rstrip()
                break
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
    try:
        f_obj = open(path, encoding="utf-8")
    except OSError as e:
        import warnings

        warnings.warn(
            f".env ファイルの読み込みに失敗しました: {path}: {e}", stacklevel=2
        )
        return
    with f_obj as f:
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
# KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できる（テスト等で使用）
# プロジェクトルートが特定できない場合は自動ロードをスキップする
if not os.environ.get("KABUSYS_DISABLE_AUTO_ENV_LOAD"):
    _root = _find_project_root()
    if _root is not None:
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

_BOOL_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _parse_bool_env(key: str, default: bool = False) -> bool:
    """環境変数をブール値として厳格に解釈する（許容リスト方式）。

    "1" / "true" / "yes" / "on"（大文字小文字無視）のみ True とし、
    それ以外（空文字・"off"・"disabled" など）はすべて default を返す。
    """
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in _BOOL_TRUE_VALUES


class Settings:
    """アプリケーション設定。環境変数から値を取得する。"""

    # --- J-Quants API ---
    @property
    def jquants_refresh_token(self) -> str:
        return _require("JQUANTS_REFRESH_TOKEN")

    @property
    def jquants_bulk_api_key(self) -> str:
        return _require("JQUANTS_BULK_API_KEY")

    # --- kabuステーション API ---
    @property
    def kabu_api_password(self) -> str:
        return _require("KABU_API_PASSWORD")

    @property
    def kabu_api_base_url(self) -> str:
        return os.environ.get("KABU_API_BASE_URL", "http://localhost:18080/kabusapi")

    @property
    def kabu_trade_password(self) -> str | None:
        return os.environ.get("KABU_TRADE_PASSWORD") or None

    # --- 拡張機能トグル ---
    @property
    def enable_ai_sentiment(self) -> bool:
        """AI センチメント機能の有効フラグ（ENABLE_AI_SENTIMENT、デフォルト: False）。

        "1" / "true" / "yes" / "on" のみ True。空文字や "off" / "disabled" は False。
        False の場合、news_nlp / regime_detector は即座にリターンし Core 機能に影響しない。
        """
        return _parse_bool_env("ENABLE_AI_SENTIMENT", default=False)

    @property
    def enable_tdnet(self) -> bool:
        """TDnet 適時開示収集機能の有効フラグ（ENABLE_TDNET、デフォルト: False）。

        "1" / "true" / "yes" / "on" のみ True。デフォルト無効。
        False の場合、tdnet_collection / disclosure_classification ジョブはスキップされる。
        """
        return _parse_bool_env("ENABLE_TDNET", default=False)

    # --- EDINET ---
    @property
    def enable_edinet(self) -> bool:
        """EDINET 法定開示収集機能の有効フラグ（ENABLE_EDINET、デフォルト: False）。

        "1" / "true" / "yes" / "on" のみ True。デフォルト無効。
        False の場合、edinet_collection ジョブはスキップされる。
        """
        return _parse_bool_env("ENABLE_EDINET", default=False)

    @property
    def edinet_api_key(self) -> str:
        """EDINET API サブスクリプションキー（EDINET_API_KEY）。

        EDINET API v2 の利用に必要。ENABLE_EDINET=true の場合に設定すること。
        """
        return os.environ.get("EDINET_API_KEY", "")

    # --- Yahoo News ---
    @property
    def enable_yahoonews(self) -> bool:
        """Yahoo News RSS 収集機能の有効フラグ（ENABLE_YAHOONEWS、デフォルト: False）。

        "1" / "true" / "yes" / "on" のみ True。デフォルト無効。
        False の場合、yahoonews_collection ジョブはスキップされる。
        """
        return _parse_bool_env("ENABLE_YAHOONEWS", default=False)

    # --- LINE Messaging API ---
    @property
    def line_channel_access_token(self) -> str:
        return os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    @property
    def line_user_id(self) -> str:
        return os.environ.get("LINE_USER_ID", "")

    @property
    def line_notify_enabled(self) -> bool:
        return _parse_bool_env("LINE_NOTIFY_ENABLED", default=False)

    # --- データベース ---
    @property
    def duckdb_path(self) -> Path:
        return Path(os.environ.get("DUCKDB_PATH", "data/kabusys.duckdb")).expanduser()

    @property
    def sqlite_path(self) -> Path:
        return Path(os.environ.get("SQLITE_PATH", "data/monitoring.db")).expanduser()

    @property
    def paper_fill_mode(self) -> str:
        """Paper Trading 時の MockBrokerClient fill_mode。

        環境変数 PAPER_FILL_MODE で設定（デフォルト: "instant"）。
        有効値: "instant" | "partial" | "never" | "reject"
        """
        _valid = frozenset({"instant", "partial", "never", "reject"})
        mode = os.environ.get("PAPER_FILL_MODE", "instant").strip().lower()
        if mode not in _valid:
            raise ValueError(
                f"PAPER_FILL_MODE の値が不正です: '{mode}'. 有効な値: {sorted(_valid)}"
            )
        return mode

    @property
    def paper_sqlite_path(self) -> Path:
        """Paper Trading 用 SQLite DB のパス。

        環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能（デフォルト: data/paper_trading.db）。
        """
        return Path(
            os.environ.get("PAPER_TRADING_SQLITE_PATH", "data/paper_trading.db")
        ).expanduser()

    # --- 監視設定 ---
    @property
    def pid_file_path(self) -> Path:
        return Path(os.environ.get("PID_FILE_PATH", "data/execution.pid")).expanduser()

    @property
    def kill_flag_path(self) -> Path:
        return Path(os.environ.get("KILL_FLAG_PATH", "data/kill.flag")).expanduser()

    @property
    def kill_flag_clear_on_start(self) -> bool:
        return os.environ.get("KILL_FLAG_CLEAR_ON_START", "0") == "1"

    @property
    def cpu_threshold_pct(self) -> float:
        return float(os.environ.get("CPU_THRESHOLD_PCT", "90.0"))

    @property
    def memory_threshold_pct(self) -> float:
        return float(os.environ.get("MEMORY_THRESHOLD_PCT", "85.0"))

    @property
    def disk_threshold_pct(self) -> float:
        return float(os.environ.get("DISK_THRESHOLD_PCT", "90.0"))

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
