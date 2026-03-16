# KabuSys — 日本株自動売買システム

簡単な日本語ドキュメント（README.md）。このリポジトリは日本株向けのデータプラットフォームと自動売買基盤のコア部分（データ取得、ETL、スキーマ、監査ログ、品質チェックなど）を実装します。

> 注: ここにあるコードはライブラリ/モジュール群の抜粋に基づく README です。実行には外部サービス（J‑Quants API、kabuステーション、Slack 等）の認証情報や依存パッケージが必要です。

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J‑Quants API から株価日足・財務データ・マーケットカレンダーを取得
- DuckDB を用いた 3 層データレイヤ（Raw / Processed / Feature）と Execution/Audit テーブルを定義・初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 発注／約定の監査ログ（order_request_id を冪等キーとするトレーサビリティ）

設計上の特徴：
- API レート制限（J‑Quants: 120 req/min）に対応するスロットリングとリトライ（指数バックオフ）を実装
- トークン自動リフレッシュ（401 を検出して 1 回リトライ）
- データ保存は冪等（INSERT ... ON CONFLICT DO UPDATE）
- 取得タイムスタンプ（fetched_at）を UTC で記録し、Look‑ahead Bias の可視化を支援

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes（株価日足）
  - fetch_financial_statements（財務データ）
  - fetch_market_calendar（JPX カレンダー）
  - API リトライ・レート制御・トークン管理・ページネーション対応

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path)
  - get_connection(db_path)
  - 大量のテーブル定義（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, など）

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(conn, ...)：日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
  - 差分更新・バックフィルロジック、品質チェックの呼び出し

- 品質チェック（kabusys.data.quality）
  - check_missing_data（OHLC 欠損）
  - check_spike（前日比スパイク）
  - check_duplicates（主キー重複）
  - check_date_consistency（未来日や非営業日の検出）
  - run_all_checks（まとめ実行）

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) / init_audit_db(db_path)
  - signal_events / order_requests / executions を中心とした監査テーブル群

- 設定管理（kabusys.config）
  - .env（.env.local を優先）自動読み込み（無効化可能）
  - settings オブジェクトから各種必須/任意設定を取得
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証

## セットアップ手順

前提
- Python 3.10 以上（コード中での型 |union| 構文を使用）
- pip または Poetry 等の環境

1. リポジトリをチェックアウトして virtualenv を作成／有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 依存パッケージをインストール

   必須パッケージ例（プロジェクトに requirements.txt がある場合はそれを使用）:
   - duckdb

   例:
   pip install duckdb

   （実運用では HTTP クライアントや Slack SDK、kabu API クライアント等の追加依存が必要になる可能性があります。）

3. 環境変数を設定（.env を作成）

   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただしテスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須環境変数（kabusys.config.Settings に基づく）:
   - JQUANTS_REFRESH_TOKEN    （J‑Quants の refresh token）
   - KABU_API_PASSWORD        （kabuステーション API 用パスワード）
   - SLACK_BOT_TOKEN          （Slack ボットトークン）
   - SLACK_CHANNEL_ID         （Slack 通知先チャンネル ID）

   任意／デフォルト:
   - KABU_API_BASE_URL        （デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH              （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH              （デフォルト: data/monitoring.db）
   - KABUSYS_ENV              （development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL                （DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD （1 にすると .env 自動ロードを無効化）

   .env のサンプル（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化

   - 通常データ（全スキーマ）を作成する:
     Python REPL またはスクリプト内で:

     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)

   - 監査ログテーブルのみ追加（既存接続に対して）:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

   テスト時にはインメモリ DB を使えます:
     conn = init_schema(":memory:")

## 使い方（簡単な例）

以下はライブラリを使って日次 ETL を実行する簡単なコード例です。

1) 日次 ETL 実行（Python）

from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（ファイルがなければ作成）
conn = init_schema(settings.duckdb_path)

# ETL 実行（今日分を取得）
result = run_daily_etl(conn)

# 結果確認
print(result.to_dict())

2) 個別ジョブの実行（例: カレンダーだけ取得）

from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_calendar_etl
from datetime import date

conn = init_schema(settings.duckdb_path)
fetched, saved = run_calendar_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")

3) 監査スキーマ初期化

from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")

4) テスト時の注意点
- ID トークンの自動取得をテストで無効化したい場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することや、pipeline 等に id_token を直接注入してください（pipeline の関数は id_token を引数で受け取れる設計です）。

## 主要モジュールと責務

- kabusys.config
  - 環境変数読み込み、settings オブジェクト提供、.env 自動ロード（プロジェクトルート検出）
- kabusys.data.jquants_client
  - J‑Quants API 呼び出し・ページネーション・リトライ・トークン取得・DuckDB 保存ヘルパー
- kabusys.data.schema
  - DuckDB の DDL 定義とスキーマ初期化ロジック
- kabusys.data.pipeline
  - ETL の差分計算・バックフィル・品質チェック統合
- kabusys.data.quality
  - 各種データ品質チェック（欠損、スパイク、重複、日付不整合）
- kabusys.data.audit
  - 発注〜約定の監査テーブル定義・初期化
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージプレースホルダ（実装は別途）

## ディレクトリ構成

（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

データベースやログファイルはデフォルトで `data/` 配下に置かれます（設定で変更可能）。

## 実運用上の注意

- 認証情報は必ず安全に管理してください（.env をバージョン管理しない、Secrets 管理を利用する等）。
- J‑Quants や証券会社 API の利用規約・レート制限を遵守してください。
- run_daily_etl は複数ステップを実行してもそれぞれのステップで個別に例外処理する設計です。結果の `ETLResult` を確認して異常時の対応を行ってください。
- DuckDB の ACID/並行性の制約やファイルロックに注意してください（複数プロセスで同一 DB を書き込む場合の設計を検討してください）。
- 監査ログは削除しない前提です（FK は ON DELETE RESTRICT）。監査情報の保管方針を確立してください。

## 開発・貢献

- Python >= 3.10 を使用してください。
- 追加の機能やバグ修正は Pull Request を通じてお願いします（この README はコード抜粋に基づくため、実際のレポジトリに合わせて適宜更新してください）。

---

この README はコードベースの現状（モジュール実装の抜粋）に基づいて作成しました。CI／テスト／デプロイ方法や詳細な API 欄（Slack 通知や kabuステーション 実装）は本リポジトリの追加ファイルに応じて追記してください。