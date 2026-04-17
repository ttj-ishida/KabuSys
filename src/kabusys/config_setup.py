# src/kabusys/config_setup.py
"""環境設定ウィザード CLI。

.env の初期作成・更新を対話式で支援する。

使い方:
    python -m kabusys.config_setup
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"

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
        "key": "JQUANTS_REFRESH_TOKEN",
        "label": "J-Quants リフレッシュトークン",
        "secret": True,
        "description": "  J-Quants API のリフレッシュトークン（必須）",
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
        f"JQUANTS_REFRESH_TOKEN={values.get('JQUANTS_REFRESH_TOKEN', '')}",
        "",
        "# --- kabuステーション API ---",
        f"KABU_API_PASSWORD={values.get('KABU_API_PASSWORD', '')}",
        f"KABU_API_BASE_URL={values.get('KABU_API_BASE_URL', 'http://localhost:18080/kabusapi')}",
        "",
        "# --- LINE Messaging API (アラート通知用) ---",
        f"LINE_CHANNEL_ACCESS_TOKEN={values.get('LINE_CHANNEL_ACCESS_TOKEN', '')}",
        f"LINE_USER_ID={values.get('LINE_USER_ID', '')}",
        "",
        "# --- データベース ---",
        f"DUCKDB_PATH={values.get('DUCKDB_PATH', 'data/kabusys.duckdb')}",
        f"SQLITE_PATH={values.get('SQLITE_PATH', 'data/monitoring.db')}",
        "",
        "# --- システム設定 ---",
        f"KABUSYS_ENV={values.get('KABUSYS_ENV', 'development')}",
        f"LOG_LEVEL={values.get('LOG_LEVEL', 'INFO')}",
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
    is_optional = item.get("optional", False)

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
        except (EOFError, KeyboardInterrupt):
            return values  # 途中キャンセル時は現在値を返す
        if result is not None:
            # オプション項目で空文字ならキーを削除（書き込み時に空値）
            values[item["key"]] = result

    return values


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="KabuSys 環境設定ウィザード（.env の作成・更新）"
    )
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
