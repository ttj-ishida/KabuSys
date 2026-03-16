# KabuSys

日本株を対象とした自動売買プラットフォーム用のライブラリ群（骨組み）。データ取得・DBスキーマ管理・品質チェック・監査ログ等の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から市場データ（株価日足・財務データ・マーケットカレンダー）を取得するクライアント
- DuckDB を用いた 3 層データレイヤ（Raw / Processed / Feature）および Execution / Audit 用スキーマ定義と初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）初期化ユーティリティ
- 簡易な設定管理（.env 自動ロード、環境変数アクセス）

設計上の特徴：
- J-Quants API はレート制限（120 req/min）とリトライロジック、401 のトークン自動リフレッシュを考慮
- すべてのタイムスタンプは UTC にて記録（fetched_at / created_at 等）
- DuckDB へは冪等（ON CONFLICT DO UPDATE）で保存することを想定

---

## 機能一覧

- 環境・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - マーケットカレンダー（fetch_market_calendar）
  - レートリミッタ、リトライ（指数バックオフ）、401 自動リフレッシュ
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）

- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) で DuckDB を初期化（冪等）
  - get_connection(db_path) で接続取得

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL と初期化関数
  - init_audit_schema(conn) / init_audit_db(db_path)

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出（check_missing_data）
  - スパイク検出（check_spike）
  - 重複チェック（check_duplicates）
  - 日付不整合検出（check_date_consistency）
  - run_all_checks で一括実行、QualityIssue のリストを返却

---

## セットアップ手順

1. リポジトリをクローン（もしくはパッケージを配置）
2. 必要な Python 環境を作成し依存をインストール

推奨: 仮想環境を使用
```
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.venv\Scripts\activate.bat   # Windows
```

依存インストール（例）
```
pip install duckdb
# その他プロジェクト特有の依存があれば requirements.txt を用意して pip install -r requirements.txt
```

3. 環境変数 (.env) を準備

プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` ファイルを置くと自動読み込みされます。読み込み順は OS 環境変数 > .env.local > .env です。

必須の主要環境変数（例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
```

その他オプション:
```
DUCKDB_PATH=data/kabusys.duckdb   # デフォルト
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development|paper_trading|live
LOG_LEVEL=INFO
```

- 自動読み込みを無効化したいとき:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本例）

以下はライブラリを使った典型的な流れ（DuckDB 初期化 → データ取得 → 保存 → 品質チェック）です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) J-Quants から株価日足を取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 認証は内部で settings.jquants_refresh_token を使用して行います
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データやマーケットカレンダーも同様に fetch_* → save_* を使用
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
fins = fetch_financial_statements(code="7203")
save_financial_statements(conn, fins)
```

4) 監査ログスキーマの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

5) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.table, i.severity, i.detail)
    for row in i.rows:
        print(row)
```

6) 直接トークンを取得したい場合:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点:
- J-Quants へのリクエストは内部でレート制御（120 req/min）とリトライを実装しています。短時間で大量リクエストを投げる用途では注意してください。
- API から取得した各レコードには fetched_at を UTC で付与して保存されます（look-ahead bias のトレース用）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得＋DuckDB保存）
    - schema.py              -- DuckDB スキーマ定義と init_schema / get_connection
    - audit.py               -- 監査ログ（signal/events/order_requests/executions）初期化
    - quality.py             -- データ品質チェック（各種チェック関数）
  - strategy/
    - __init__.py            -- 戦略層（未実装のため拡張ポイント）
  - execution/
    - __init__.py            -- 発注実行層（未実装のため拡張ポイント）
  - monitoring/
    - __init__.py            -- 監視・メトリクス（拡張ポイント）

主なスキーマ／テーブル（概要）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 実装上の細かな仕様（要点）

- .env のパーシングはシェル風（export プレフィックス・シングル/ダブルクォート、エスケープ、コメント取り扱い）に対応しています。
- settings（kabusys.config.settings）経由で環境変数をプロパティとして取得できます。必須変数がない場合は ValueError を送出します。
- データ保存関数は冪等性を保つため ON CONFLICT DO UPDATE を使用しています。
- J-Quants クライアント:
  - レート制限のため固定間隔スロットリングを採用（_RateLimiter）
  - リトライ: 最大 3 回、指数バックオフ、408/429/5xx に対応
  - 401 受信時はリフレッシュトークンで id_token を再取得して 1 回だけリトライ
  - ページネーション対応（pagination_key）
- 監査ログ:
  - order_request_id を冪等キーとし、重複発注を防止する設計
  - すべての TIMESTAMP は UTC で保存することを前提（init_audit_schema で TimeZone を UTC に設定）

---

## 参考: よく使うコードスニペット

- DB 初期化（メモリ内）
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

- .env ロードを無効化してテスト実行
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('disabled')"
```

---

## 今後の拡張ポイント（メモ）

- strategy と execution パッケージに実際の取引ロジック・ブローカー連携の実装
- モニタリング（Slack 通知等）やバックテスト機能の統合
- CI 用の DB 初期化/マイグレーションコマンド化

---

以上。必要であれば README に含めるサンプル .env.example、requirements.txt、具体的な CLI コマンドや使い方のサンプルを追加できます。どの内容を優先して追記しますか？