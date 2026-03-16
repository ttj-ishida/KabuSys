# KabuSys

日本株自動売買システムの基盤ライブラリ（KabuSys）。  
データ取得、DuckDBスキーマ定義、監査ログ、データ品質チェックなど自動売買プラットフォームのコア機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下用途を想定した Python パッケージです。

- J-Quants API からの市場データ取得（OHLCV / 四半期財務 / マーケットカレンダー）
- DuckDB を利用したデータスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order → execution）の永続化スキーマと初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 環境設定の自動読み込み（.env / .env.local / OS 環境変数）

設計上のポイント:

- J-Quants API のレート制限（120 req/min）に従うレートリミッタとリトライ実装
- 401 受信時の自動トークンリフレッシュ（1回まで）
- データ取得時に fetched_at を UTC で記録して Look-ahead Bias を防止
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE）
- すべてのタイムスタンプは UTC を推奨

---

## 機能一覧

- data.jquants_client
  - get_id_token(refresh_token=None): J-Quants の ID トークン取得（リフレッシュトークン利用）
  - fetch_daily_quotes(...): 日足（OHLCV）ページネーション対応取得
  - fetch_financial_statements(...): 四半期財務データ取得
  - fetch_market_calendar(...): JPX マーケットカレンダー取得
  - save_daily_quotes(conn, records): raw_prices テーブルへ冪等保存
  - save_financial_statements(conn, records): raw_financials へ冪等保存
  - save_market_calendar(conn, records): market_calendar へ冪等保存

- data.schema
  - init_schema(db_path): DuckDB のスキーマ（全テーブル・インデックス）を初期化して接続を返す
  - get_connection(db_path): 既存 DB へ接続（スキーマ初期化は行わない）

- data.audit
  - init_audit_schema(conn): 監査ログテーブルを既存接続に追加
  - init_audit_db(db_path): 監査ログ専用 DB を初期化して接続を返す

- data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=0.5)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, ...)
  - いずれも QualityIssue オブジェクトのリストを返す（error/warning 分類）

- config
  - Settings クラス: 環境変数から設定を取得（J-Quants / kabuステーション / Slack / DB パス / 環境 etc）
  - 自動でプロジェクトルートの .env / .env.local を読み込む（CWD 依存しない探索）

---

## セットアップ手順

前提:

- Python 3.10 以上（型注釈に `X | Y` を使用）
- pip が使用可能

1. リポジトリをクローン／展開

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール  
   本コードベースで明示されている主な依存は duckdb と標準ライブラリのみ。必要に応じて他の HTTP ライブラリやロギング周りを追加して下さい。

   例:
   pip install duckdb

4. 環境変数の設定  
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuステーション API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視用、省略時: data/monitoring.db）
   - KABUSYS_ENV: environment (development / paper_trading / live)（省略時: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時: INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方

以下は主要なユースケースのサンプルコードです。実際はプロジェクトに合わせてエラーハンドリングやロギング、スケジューリング等を追加してください。

1) DuckDB スキーマ初期化（すべてのテーブルを作成）

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) J-Quants から日足データを取得して保存

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 例: 銘柄コード 7203（トヨタ）の日付レンジ取得
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データ・マーケットカレンダーの取得・保存

```python
from kabusys.data.jquants_client import (
    fetch_financial_statements,
    save_financial_statements,
    fetch_market_calendar,
    save_market_calendar,
)

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログテーブルを追加する（init_schema で作成した conn を拡張）

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で取得した DuckDB 接続
init_audit_schema(conn)
```

5) データ品質チェックの実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)
```

6) 設定値の取得（例: token）

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)  # development / paper_trading / live
```

注意:
- J-Quants API 呼び出しは内部でレートリミット・リトライを行いますが、バッチ処理やページネーションを行う際は適切に設計してください。
- save_* 関数は ON CONFLICT DO UPDATE により冪等です。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数・設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - audit.py                     -- 監査ログ（signal/order/execution）スキーマ
      - quality.py                   -- データ品質チェック
      - (その他: news/audit などの拡張用モジュール)
    - strategy/
      - __init__.py                  -- 戦略関連パッケージ（拡張想定）
    - execution/
      - __init__.py                  -- 発注実行関連（拡張想定）
    - monitoring/
      - __init__.py                  -- 監視・アラート関連（拡張想定）

主要なスキーマ設計（簡略）:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_performance
- 監査ログ: signal_events, order_requests, executions（監査用の別スキーマ）

---

## 注意事項 / 追加情報

- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を基準に行われます。テストや特殊環境で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限は 120 req/min です。内部的に固定間隔のスロットリングで制御しますが、大量データ取得時は留意してください。
- DuckDB の初期化は冪等です。既存テーブルはスキップされ、必要なインデックスも作成されます。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。監査ログを利用したトレーサビリティを確保してください。

---

GitHub / パッケージ配布用の README として必要な追加情報（例: ライセンス、貢献方法、テスト手順など）はプロジェクトポリシーに応じて追記してください。