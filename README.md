# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定トレーサビリティ）等の基盤機能を提供します。

## プロジェクト概要
KabuSys は J-Quants 等の外部 API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に階層化されたスキーマで保存することで、戦略・実行層に安定したデータ基盤を提供することを目的としています。ニュース収集やデータ品質チェック、監査ログ（発注・約定の追跡）など、実運用を考慮した各種ユーティリティを備えています。

設計のポイント:
- データ取得におけるレート制限とリトライ（指数バックオフ）を実装
- 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT）で上書き/重複排除
- ニュース収集では SSRF / XML Bomb 対策やトラッキングパラメータ除去を実施
- データ品質チェックを通じて欠損・重複・スパイク・日付不整合を検出
- 監査ログでシグナル→発注→約定を UUID ベースでトレース可能

## 主な機能一覧
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット管理、リトライ、自動トークンリフレッシュ
  - DuckDB への保存ユーティリティ（冪等保存）
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新・バックフィル、品質チェックの統合実行（run_daily_etl）
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema() / init_audit_db() で初期化
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集、URL 正規化、記事ID生成（SHA-256）、SSRF 対策
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、翌前営業日取得、夜間カレンダー更新ジョブ
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損、スパイク（前日比）、重複、日付不整合チェック
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions を中心とする監査スキーマ

## セットアップ手順

前提
- Python 3.10 以上（コード中の型ヒントに Python 3.10 の構文を使用）
- DuckDB、defusedxml 等の依存パッケージ

1. リポジトリをクローンしてインストール（編集開発用）
   - 開発環境に合わせて pipenv/poetry/venv を使用してください。ここでは pip の例:
     ```
     pip install -e .
     ```
   - 必要なライブラリ（例）
     ```
     pip install duckdb defusedxml
     ```

2. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的にロードされます（src/kabusys/config.py により、OS 環境変数 > .env.local > .env の順で読み込み）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。
   - 必要な環境変数（主要）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack Bot Token（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（省略時: data/monitoring.db）
     - KABUSYS_ENV: 実行環境（development|paper_trading|live、省略時 development）
     - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、省略時 INFO）

   - 例: .env（最低限の必須項目）
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. データベース初期化
   - DuckDB スキーマを作成（ファイル DB または ":memory:"）
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # または既存 DB へ接続だけ: conn = schema.get_connection("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

## 使い方（例）

- J-Quants ID トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックを実行）
  ```python
  from kabusys.data import schema, pipeline
  conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema しておく
  result = pipeline.run_daily_etl(conn)  # デフォルト: target_date=今日
  print(result.to_dict())
  ```

- 株価データのみ差分 ETL 実行
  ```python
  from kabusys.data import schema, pipeline
  conn = schema.get_connection("data/kabusys.duckdb")
  from datetime import date
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使用する有効な4桁銘柄コード集合（省略可）
  known_codes = {"7203", "6758", "9432"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数, ...}
  ```

- マーケットカレンダーの夜間更新ジョブ
  ```python
  from kabusys.data import schema, calendar_management
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  ```

- データ品質チェックの単独実行
  ```python
  from kabusys.data import schema, quality
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点・運用メモ:
- jquants_client は API レート制限（120 req/min）を内部で管理します。頻繁に並列呼び出しする場合は注意してください。
- fetch_rss は SSRF 対策や gzip サイズチェック等の安全対策を含みます。ユニットテスト時は news_collector._urlopen をモックして外部通信を抑制できます。
- .env の自動読み込みは、パッケージ import 時に走るためテストなどで制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## ディレクトリ構成
（ルートに README.md、pyproject.toml 等を想定。実装は src/package レイアウト）

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数 / 設定管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py      -- RSS ニュース収集・保存・銘柄抽出
      - schema.py              -- DuckDB スキーマ定義 & init_schema / get_connection
      - pipeline.py            -- ETL パイプライン（run_daily_etl 他）
      - calendar_management.py -- マーケットカレンダー管理（営業日判定・更新ジョブ）
      - audit.py               -- 監査ログ（signal/order/execution）スキーマ初期化
      - quality.py             -- データ品質チェック（欠損・重複・スパイク等）
    - strategy/
      - __init__.py            -- 戦略層（拡張対象）
    - execution/
      - __init__.py            -- 発注 / 実行層（拡張対象）
    - monitoring/
      - __init__.py            -- 監視 / メトリクス（拡張対象）

## 開発・拡張のヒント
- Strategy / Execution / Monitoring パッケージは拡張ポイントです。各戦略は signal_events / order_requests を経由して監査ログを残す設計になっています。
- DuckDB を利用することでローカル環境でも高速に分析・クエリが可能です。テーブルは冪等に作成されるため何度実行しても安全です。
- ニュース収集での銘柄抽出は単純な4桁数字マッチ（known_codes をフィルタ）です。必要に応じて NLP による紐付け処理を追加してください。
- ETL は各ステップでエラーハンドリングされ、1 ステップ失敗でも他を継続します。運用上の判断（致命的なエラーで停止するか否か）は呼び出し元で行ってください。

## ライセンス / 貢献
- （ここにライセンス情報を記載してください）
- バグ報告・機能改善の PR を歓迎します。テストを添えて送ってください。

---

以上が README の概要です。特定の使用例（CI 実行、cron での日次 ETL、Slack 通知など）について詳細が必要であれば、実際の運用フローに合わせてサンプルを作成します。