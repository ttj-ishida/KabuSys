# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
J-Quants や RSS を使ったデータ収集、DuckDB ベースのスキーマ／ETL、ニュース収集・銘柄紐付け、データ品質チェック、監査ログ（トレーサビリティ）などの基盤機能を提供します。

## 特徴（概要）
- J-Quants API からのデータ取得（株価日足、四半期財務、JPX カレンダー）
  - レート制限制御（120 req/min）
  - 再試行（指数バックオフ）、401 時の自動トークンリフレッシュ
  - フェッチ時刻（fetched_at）を UTC で記録して Look-ahead を防止
- DuckDB を使った 3 層データモデル（Raw / Processed / Feature）と実行・監査テーブル
  - 冪等保存（ON CONFLICT）を基本
- RSS ベースのニュース収集（セーフティ対策: SSRF 防止、XML 攻撃対策、受信サイズ制限）
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
  - 銘柄コード抽出・news_symbols への紐付け機能
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 市場カレンダーを先に取得して営業日判定に利用
  - 品質チェック（欠損、重複、スパイク、日付不整合）を集計して返却
- 監査ログ（signal → order_request → executions のトレーサビリティ）
  - 全ての変更を監査テーブルに記録するため追跡可能

---

## 機能一覧
- 環境設定管理（.env 自動読み込み、必須キーチェック）
- J-Quants クライアント
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - DuckDB 保存関数: save_daily_quotes(), save_financial_statements(), save_market_calendar()
- ニュース収集
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
- DuckDB スキーマ管理
  - init_schema(), get_connection()
- ETL パイプライン
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
- マーケットカレンダー管理
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- データ品質チェック
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
- 監査ログ（audit）
  - init_audit_schema(), init_audit_db()

---

## システム要件
- Python 3.10 以上（型アノテーションで | 演算子を使用）
- 主な依存パッケージ:
  - duckdb
  - defusedxml
- 標準ライブラリで HTTP/URL 操作に urllib を使用

推奨インストール方法は次節を参照してください。

---

## セットアップ手順

1. リポジトリをチェックアウト（または pip で配布パッケージをインストール）
   - 開発環境でソースから使う場合:
     ```
     git clone <repo_url>
     cd <repo_root>
     pip install -e .
     ```
     （pyproject.toml / setup があることを前提。無ければ直接必要パッケージを pip install してください）

2. 依存ライブラリをインストール
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（実行に必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
   - 任意／デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト：development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト：INFO）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト：data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト：data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # :memory: も可
     ```
   - 監査ログを別 DB に初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```
   - 既存接続へ監査テーブルを追加したい場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)  # 既に init_schema() で得た conn を渡す
     ```

---

## 使い方（よく使う例）

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する（RSS を取得して raw_news に保存、銘柄紐付け）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー夜間バッチ（先読みで market_calendar を更新）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- J-Quants から生データを直接取得して DuckDB に保存する
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)
  ```

- データ品質チェックのみ実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.quality import run_all_checks

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意:
- ETL 内では J-Quants のトークン管理を行い、自動でリフレッシュします（settings.jquants_refresh_token を使用）。
- run_daily_etl などはエラーを個別にハンドリングし、可能な限り処理を継続します。戻り値の ETLResult から問題の有無を確認してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py               — DuckDB スキーマ定義 / init_schema
    - jquants_client.py       — J-Quants API クライアント／保存関数
    - pipeline.py             — ETL パイプライン（差分取得・品質チェック）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ（signal / order_request / executions）
  - strategy/
    - __init__.py             — 戦略層エントリ（拡張用）
  - execution/
    - __init__.py             — 発注実行層のプレースホルダ
  - monitoring/
    - __init__.py             — 監視・メトリクス関連（拡張用）

---

## 注意点・運用上のヒント
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の位置）を探索して行います。テスト等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルのバックアップ・リストアは通常のファイルコピーで可能です。初回は init_schema() で親ディレクトリが自動作成されます。
- ニュース収集では外部 URL を検証し、リダイレクト先のプライベートアドレスや非 http/https スキームを拒否します。外部フィードを追加する際は注意してください。
- J-Quants のレート制限を遵守するために内部でスロットリングとリトライを実装していますが、長時間の連続取得や大規模なバックフィルを行う際は API 利用規約を確認してください。
- ロギングは標準 logging モジュールを利用しています。LOG_LEVEL 環境変数で調整してください。

---

必要に応じてサンプルスクリプトや CI/CD 用のワークフロー（ETL の定期実行、夜間バッチ、監査ログのエクスポート等）のテンプレートも用意できます。どの部分を優先して補足したいかを教えてください。