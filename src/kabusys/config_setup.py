# src/kabusys/config_setup.py
"""環境設定ウィザード CLI。

.env の初期作成・更新を対話式で支援する。

使い方:
    python -m kabusys.config_setup
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"

# 拡張機能トグルのキーとデフォルト値。_ITEMS と _write_env の両方がここを参照する。
# 新しいトグルを追加する場合はここだけ編集すればよい。
_TOGGLE_DEFAULTS: dict[str, str] = {
    "LINE_NOTIFY_ENABLED": "false",
    "ENABLE_AI_SENTIMENT": "false",
    "ENABLE_TDNET": "false",
    "ENABLE_EDINET": "false",
    "ENABLE_YAHOONEWS": "false",
    "JQUANTS_ENABLE_DIVIDENDS": "false",
}

# ---------------------------------------------------------------------------
# 設定項目定義
# ---------------------------------------------------------------------------

_ITEMS: list[dict] = [
    {
        "key": "KABUSYS_ENV",
        "label": "実行環境",
        "choices": ["development", "paper_trading", "live"],
        "default": "development",
        "description": (
            "  development  : ローカル開発・テスト用（発注なし）\n"
            "  paper_trading: ペーパートレード（仮想発注）\n"
            "  live         : 本番（実際に発注が行われます）"
        ),
    },
    {
        "key": "JQUANTS_BULK_API_KEY",
        "label": "J-Quants API キー",
        "secret": True,
        "description": (
            "  J-Quants v2 認証に使用する API キー（必須）\n"
            "  J-Quants ダッシュボード → 設定 → API キー から取得\n"
            "  https://jpx-jquants.com/"
        ),
    },
    {
        "key": "KABU_API_PASSWORD",
        "label": "kabuステーション API パスワード",
        "secret": True,
        "description": "  kabuステーション API パスワード（必須）",
    },
    {
        "key": "KABU_API_BASE_URL",
        "label": "kabuステーション API ベース URL",
        "default": "http://localhost:18080/kabusapi",
        "description": "  通常はデフォルトのままで可",
    },
    {
        "key": "KABU_USE_SANDBOX",
        "label": "kabuステーション検証環境（ポート 18081）の使用",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  true かつ KABUSYS_ENV=paper_trading のとき検証環境（18081）に接続する\n"
            "  false の場合 MockBrokerClient を使用してシミュレーションする"
        ),
    },
    {
        "key": "KABU_SANDBOX_API_PASSWORD",
        "label": "kabuステーション検証環境 API パスワード（任意）",
        "secret": True,
        "optional": True,
        "description": (
            "  KABU_USE_SANDBOX=true の場合に使用する検証環境用 API パスワード\n"
            "  未設定時は KABU_API_PASSWORD を流用する"
        ),
    },
    {
        "key": "KABU_TRADE_PASSWORD",
        "label": "kabuステーション 取引パスワード（任意）",
        "secret": True,
        "optional": True,
        "description": (
            "  kabuステーション 取引パスワード（空欄時は API パスワードを流用）\n"
            "  APIパスワードと同一の場合は空欄でよい"
        ),
    },
    {
        "key": "DUCKDB_PATH",
        "label": "DuckDB ファイルパス",
        "default": "data/kabusys.duckdb",
        "description": "  分析用 DuckDB データベースのパス",
    },
    {
        "key": "SQLITE_PATH",
        "label": "SQLite ファイルパス（監視 DB）",
        "default": "data/monitoring.db",
        "description": "  監視・注文履歴用 SQLite データベースのパス",
    },
    {
        "key": "LINE_CHANNEL_ACCESS_TOKEN",
        "label": "LINE チャンネルアクセストークン（任意）",
        "secret": True,
        "optional": True,
        "description": "  アラート通知用 LINE Messaging API トークン（空欄でスキップ）",
    },
    {
        "key": "LINE_USER_ID",
        "label": "LINE ユーザー ID（任意）",
        "optional": True,
        "description": "  アラート送信先 LINE ユーザー ID（空欄でスキップ）",
    },
    {
        "key": "LINE_NOTIFY_ENABLED",
        "label": "LINE 通知の有効化",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  LINE Messaging API でアラートを通知する（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が必要）\n"
            "  false の場合 NullNotifier が使われ Core 機能に影響しない"
        ),
    },
    {
        "key": "ENABLE_AI_SENTIMENT",
        "label": "AI センチメント分析の有効化",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  Yahoo ニュースを OpenAI で分析し売買判断に加味する（OPENAI_API_KEY が別途必要・有料）\n"
            "  false の場合 news_nlp / regime_detector はスキップされ Core 機能に影響しない"
        ),
    },
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API キー（AI Co-Pilot / AI センチメント分析用）",
        "secret": True,
        "optional": True,
        "description": (
            "  Strategy Lab の AI Co-Pilot チャット、および ENABLE_AI_SENTIMENT=true 時のニュース分析で使用\n"
            "  未設定の場合 AI Co-Pilot タブは使用不可（Core 機能には影響しない）\n"
            "  https://platform.openai.com/api-keys から取得"
        ),
    },
    {
        "key": "ENABLE_TDNET",
        "label": "TDnet 適時開示収集の有効化",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  TDnet から当日の開示一覧を収集・分類する（無料）\n"
            "  false の場合 tdnet_collection / disclosure_classification ジョブはスキップされる"
        ),
    },
    {
        "key": "ENABLE_EDINET",
        "label": "EDINET 法定開示収集の有効化",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  EDINET API から有報・四半期報・大量保有報告等を収集する（無料・APIキー要）\n"
            "  false の場合 edinet_collection ジョブはスキップされる"
        ),
    },
    {
        "key": "EDINET_API_KEY",
        "label": "EDINET API サブスクリプションキー",
        "secret": True,
        "description": (
            "  EDINET API v2 の利用に必要（ENABLE_EDINET=true の場合のみ使用）\n"
            "  https://disclosure2.edinet-fsa.go.jp/ から無料取得"
        ),
    },
    {
        "key": "ENABLE_YAHOONEWS",
        "label": "Yahoo News RSS 収集の有効化",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  Yahoo News RSS から当日ニュースを収集し raw_news テーブルへ保存する（無料）\n"
            "  false の場合 yahoonews_collection ジョブはスキップされる\n"
            "  ニュース AI スコアリングには別途 ENABLE_AI_SENTIMENT=true が必要"
        ),
    },
    {
        "key": "JQUANTS_ENABLE_DIVIDENDS",
        "label": "配当データ ETL の有効化",
        "choices": ["true", "false"],
        "default": "false",
        "description": (
            "  J-Quants の /fins/dividend エンドポイントを使って配当データを取得する\n"
            "  Standard プランでは HTTP 403 となるため false を設定すること\n"
            "  true にすると div_yield 特徴量が更新される（Premium プラン以上が必要）"
        ),
    },
    {
        "key": "PAPER_TRADING_INITIAL_CASH",
        "label": "ペーパートレード用初期資金（円）",
        "default": "10000000",
        "description": (
            "  KABUSYS_ENV=paper_trading 時の MockBrokerClient 初期現金残高（円）\n"
            "  デフォルト: 10,000,000 円（1,000 万円）"
        ),
    },
    {
        "key": "LOG_LEVEL",
        "label": "ログレベル",
        "choices": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "default": "INFO",
        "description": "  ログ出力レベル",
    },
    {
        "key": "KILL_FLAG_CLEAR_ON_START",
        "label": "起動時に Kill Flag を自動クリアする",
        "choices": ["0", "1"],
        "default": "0",
        "description": "  0=クリアしない（本番推奨）/ 1=自動クリア（開発用）",
    },
]


# ---------------------------------------------------------------------------
# .env ファイル読み書き
# ---------------------------------------------------------------------------


def _read_env(path: Path) -> dict[str, str]:
    """既存の .env ファイルを読み込む。存在しない場合は空 dict。"""
    if not path.exists():
        return {}
    existing: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, sep, value = line.partition("=")
        if sep:
            existing[key.strip()] = value.strip().strip('"').strip("'")
    return existing


def _write_env(path: Path, values: dict[str, str]) -> None:
    """values を .env ファイルに書き込む。"""
    lines = [
        "# =============================================================",
        "# KabuSys 環境変数設定ファイル",
        "# このファイルは config_setup.py で生成されました",
        "# .env は絶対に Git にコミットしないこと",
        "# =============================================================",
        "",
        "# --- J-Quants API ---",
        f"JQUANTS_BULK_API_KEY={values.get('JQUANTS_BULK_API_KEY', '')}",
        "",
        "# --- kabuステーション API ---",
        f"KABU_API_PASSWORD={values.get('KABU_API_PASSWORD', '')}",
        f"KABU_API_BASE_URL={values.get('KABU_API_BASE_URL', 'http://localhost:18080/kabusapi')}",
        f"KABU_TRADE_PASSWORD={values.get('KABU_TRADE_PASSWORD', '')}",
        f"KABU_USE_SANDBOX={values.get('KABU_USE_SANDBOX', 'false')}",
        f"KABU_SANDBOX_API_PASSWORD={values.get('KABU_SANDBOX_API_PASSWORD', '')}",
        "",
        "# --- LINE Messaging API (アラート通知用) ---",
        f"LINE_CHANNEL_ACCESS_TOKEN={values.get('LINE_CHANNEL_ACCESS_TOKEN', '')}",
        f"LINE_USER_ID={values.get('LINE_USER_ID', '')}",
        "",
        "# --- データベース ---",
        f"DUCKDB_PATH={values.get('DUCKDB_PATH', 'data/kabusys.duckdb')}",
        f"SQLITE_PATH={values.get('SQLITE_PATH', 'data/monitoring.db')}",
        "",
        "# --- OpenAI (AI Co-Pilot / AI センチメント分析) ---",
        f"OPENAI_API_KEY={values.get('OPENAI_API_KEY', '')}",
        "",
        "# --- ペーパートレード設定 ---",
        f"PAPER_TRADING_INITIAL_CASH={values.get('PAPER_TRADING_INITIAL_CASH', '10000000')}",
        "",
        "# --- システム設定 ---",
        f"KABUSYS_ENV={values.get('KABUSYS_ENV', 'development')}",
        f"LOG_LEVEL={values.get('LOG_LEVEL', 'INFO')}",
        "",
        "# --- 拡張機能トグル ---",
        *[f"{k}={values.get(k, v)}" for k, v in _TOGGLE_DEFAULTS.items()],
        "",
        "# --- Kill Switch ---",
        f"KILL_FLAG_CLEAR_ON_START={values.get('KILL_FLAG_CLEAR_ON_START', '0')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 対話ループ
# ---------------------------------------------------------------------------


def _prompt(item: dict, existing: dict[str, str]) -> str | None:
    """1項目を対話式に入力してもらう。スキップ時は None を返す。"""
    key = item["key"]
    label = item["label"]
    current = existing.get(key, item.get("default", ""))
    choices = item.get("choices")
    is_secret = item.get("secret", False)
    print(f"\n{'─' * 60}")
    print(f"  {label} [{key}]")
    if item.get("description"):
        print(item["description"])

    if choices:
        print(f"  選択肢: {' / '.join(choices)}")

    # 現在値の表示（シークレットはマスク）
    if current:
        display = "****" if is_secret else current
        hint = f"Enter でそのまま使用 ({display})"
    else:
        default = item.get("default", "")
        hint = f"Enter でデフォルト ({default})" if default else "入力してください"

    try:
        answer = input(f"  → {hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n中断されました。")
        raise

    if answer == "":
        # Enter → 既存値またはデフォルトを使用
        return current or item.get("default", "")

    # 選択肢チェック
    if choices and answer not in choices:
        print(f"  ※ 無効な値です。選択肢から選んでください: {choices}")
        return _prompt(item, existing)  # 再入力

    return answer


def run_wizard(env_path: Path = _ENV_PATH) -> dict[str, str]:
    """ウィザードを実行し、設定値 dict を返す。"""
    existing = _read_env(env_path)
    values: dict[str, str] = dict(existing)

    print("=" * 60)
    print("  KabuSys 環境設定ウィザード")
    print(f"  設定ファイル: {env_path}")
    if existing:
        print("  ※ 既存の .env を読み込みました。Enter で現在値を再利用できます。")
    print("=" * 60)

    for item in _ITEMS:
        try:
            result = _prompt(item, values)
            if result is not None:
                values[item["key"]] = result
        except (EOFError, KeyboardInterrupt):
            return values  # 途中キャンセル時は現在値を返す

    return values


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="KabuSys 環境設定ウィザード（.env の作成・更新）")
    parser.add_argument(
        "--env-file",
        default=str(_ENV_PATH),
        help=f".env ファイルのパス（デフォルト: {_ENV_PATH}）",
    )
    args = parser.parse_args(argv)
    env_path = Path(args.env_file)

    try:
        values = run_wizard(env_path=env_path)
    except (EOFError, KeyboardInterrupt):
        print("\n設定ウィザードを中断しました。変更は保存されていません。")
        return 1

    print(f"\n{'─' * 60}")
    print("  設定内容の確認")
    print(f"{'─' * 60}")
    for item in _ITEMS:
        key = item["key"]
        val = values.get(key, "")
        display = "****" if item.get("secret") and val else (val or "(未設定)")
        print(f"  {key}: {display}")

    print(f"{'─' * 60}")
    try:
        confirm = input("\n  .env ファイルに保存しますか？ [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n中断しました。変更は保存されていません。")
        return 1

    if confirm != "y":
        print("保存をキャンセルしました。")
        return 0

    _write_env(env_path, values)
    print(f"\n✓ .env を保存しました: {env_path}")
    print("  次のステップ: python -m kabusys.validate_config で設定を検証してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
