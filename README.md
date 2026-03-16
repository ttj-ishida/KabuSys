# KabuSys

日本株自動売買プラットフォーム用ライブラリ（プロトタイプ）

本リポジトリは、日本株のデータ取得・保存、品質チェック、監査ログ（トレーサビリティ）、および発注系レイヤーの基盤を提供する Python パッケージの一部です。J-Quants API や kabuステーション API と連携し、DuckDB を用いたデータレイヤー（Raw / Processed / Feature / Execution）を提供します。

---

## 主な特徴

- 環境変数ベースの設定管理（.env / .env.local の自動ロード）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の遵守（固定間隔スロットリング）
  - 再試行（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - ページネーション対応
  - データ取得時刻（UTC）を記録し Look-ahead バイアスを防止
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と冪等な初期化
  - インデックス定義、外部キー関係の配慮
- 監査（audit）モジュール
  - シグナル → 発注 → 約定まで UUID によるトレーサビリティを提供
  - 発注要求を冪等キーで管理
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合（未来日付・非営業日）を検出
  - QualityIssue のリストを返却し、呼び出し側が処理（停止/警告）を判断可能
- 発注 / 戦略 / モニタリングのためのベースパッケージ構成（拡張用の空モジュールを含む）

---

## 必要な環境変数

次の環境変数は本パッケージで使用されます。必須のものは実行前に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（1 を設定）
- KABUSYS_API_BASE_URL 等のカスタムは settings 参照（例: KABU_API_BASE_URL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に `.env` と `.env.local` を自動読込します。
- 読込順序: OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 本パッケージをインストール
   - リポジトリルートに setup / pyproject.toml がある前提で:
     - pip install -e .

3. 必要パッケージ（例）
   - duckdb
   - （HTTP クライアント等は標準ライブラリを使用）
   - 実行環境に応じて追加の依存をインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env`（必要なキーを記載）を作成するか、OS 環境変数で設定します。

例: .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

以下は J-Quants から日足を取得し DuckDB に保存する基本的なフロー例です。

初期化とデータ保存:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# DB 初期化（ファイルパスまたは ":memory:" を指定）
conn = init_schema("data/kabusys.duckdb")

# データ取得（特定銘柄や日付を指定可能）
records = fetch_daily_quotes(code="7203")  # 例: トヨタ

# 保存（冪等）
saved = save_daily_quotes(conn, records)
print(f"{saved} 件を保存しました")
```

監査ログ（audit）の初期化（既存 conn に追加）:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを追加
```

品質チェック（Quality）:
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)  # 全件チェック
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

設定取得の例:
```python
from kabusys.config import settings

print(settings.duckdb_path)        # Path('data/kabusys.duckdb')
print(settings.is_live)            # bool
```

注意点:
- J-Quants クライアントは内部でレート制御・リトライ・トークン自動更新を行います。
- save_* 関数は ON CONFLICT DO UPDATE を使い冪等性を保っています。

---

## ディレクトリ構成

主要なファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - schema.py               — DuckDB スキーマ定義と初期化関数（init_schema / get_connection）
    - audit.py                — 監査ログ（signal / order_request / executions）初期化
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py             — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py             — 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・アラート（拡張ポイント）

スキーマ（主なテーブル）:
- Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
- Processed レイヤー: prices_daily, market_calendar, fundamentals, news_*
- Feature レイヤー: features, ai_scores
- Execution レイヤー: signals, signal_queue, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 実運用上の注意

- API レート制限（J-Quants: 120 req/min）を必ず守る設計になっていますが、高頻度で複数プロセスから呼ぶ場合は追加調整が必要です。
- 本実装は UTC タイムゾーンで TIMESTAMP を保存する方針です（監査・fetched_at 等）。
- 本パッケージは基盤部分を提供するものであり、実際の自動売買を行う場合はリスク管理、エラーハンドリング、テストを十分に行ってください。
- KABUSYS_ENV に応じた挙動（paper_trading / live など）を実装拡張することが想定されています。

---

README に記載のない使い方や、追加で欲しいサンプル（例: 発注フロー、Slack 通知、戦略実装テンプレート）があれば教えてください。必要に応じて具体例やチュートリアルを追記します。