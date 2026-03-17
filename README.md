KabuSys
=======

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。  
J-Quants API や RSS フィードからのデータ収集、DuckDB ベースのデータ管理、ETL パイプライン、データ品質チェック、監査ログなどを提供します。

主な目的
- 市場データ（株価、財務、マーケットカレンダー）を安全かつ冪等に収集・保存する
- ニュース（RSS）を収集して記事と銘柄の紐付けを行う
- ETL（差分取得・バックフィル）と品質チェックを自動化する
- 発注〜約定の監査トレースを保持するためのスキーマを提供する

機能一覧
- 環境変数／.env の自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務、マーケットカレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応
  - データ取得時刻（fetched_at）の記録で Look-ahead Bias を防止
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 冪等なテーブル初期化（CREATE IF NOT EXISTS 等）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）と backfill 対応
  - 市場カレンダー先読み（lookahead）
  - 品質チェックの実行（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、gzip 解凍制限
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- 監査ログ（audit）
  - signal_events / order_requests / executions など監査用テーブル
  - UUID ベースのトレーサビリティ設計
- カレンダー管理（営業日判定, next/prev/get_trading_days, calendar_update_job）

セットアップ手順（開発環境）
- 推奨 Python バージョン: 3.10+
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで動く部分も多いですが、実運用では requests 等を追加する場合あり）

例（仮想環境作成とインストール）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（最低限）
   - python -m pip install --upgrade pip
   - python -m pip install duckdb defusedxml

3. リポジトリを開発モードでインストール（pyproject.toml / setup.py がある場合）
   - python -m pip install -e .

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）

その他の任意／デフォルト環境変数
- KABUSYS_ENV : development | paper_trading | live （デフォルト development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）

.env 自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数として設定してください（テスト等で利用）。

例: .env
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（サンプルコード）
- DuckDB スキーマ初期化
  ```
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 単体で株価 ETL を実行する
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched} saved={saved}")
  ```

- RSS ニュース収集の実行
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")

  # known_codes が渡されると本文から銘柄コード抽出して news_symbols に紐付けする
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間バッチ更新ジョブ
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- 監査ログスキーマ初期化（監査専用 DB）
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

注意点・実運用での留意事項
- J-Quants のレート制限（120 req/min）に従うため、API クライアントは内部でスロットリングを行います。
- get_id_token の自動リフレッシュや HTTP リトライ（指数バックオフ）を組み込んでいますが、API エラーはアプリケーション側で適切にログ・監視してください。
- news_collector は SSRF や XML Bomb、gzip 解凍爆弾などを考慮した防御処理を実装していますが、外部入力に対するセキュリティベストプラクティスを継続してください。
- DuckDB はマルチプロセスでの排他など挙動に注意が必要です。複数プロセスからの同時書き込みや共有には運用上の検討を行ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み、Settings 定義
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py      — RSS ニュース収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー管理（営業日判定・calendar_update_job）
    - audit.py               — 監査ログ（order_requests / executions 等）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層用プレースホルダ
  - execution/
    - __init__.py            — 発注実行層用プレースホルダ
  - monitoring/
    - __init__.py            — 監視・メトリクス用プレースホルダ

開発・拡張ポイント
- strategy / execution / monitoring パッケージはプレースホルダとして用意しています。ここに戦略ロジック、ブローカー接続、運用監視コードを実装してください。
- ETL の品質チェックやニュース抽出ロジックは拡張可能です（例: NLP による銘柄関連度スコアの追加）。
- DuckDB スキーマは DataPlatform.md を参照して設計されています。必要に応じてテーブル追加・インデックス追加を検討してください。

ライセンス / 貢献
- リポジトリルートの LICENSE を参照してください（本 README には含まれていません）。  
- バグ報告・機能提案は Issue を立ててください。プルリクエスト歓迎します。

---
README はここまでです。追加で「サンプル .env.example」のテンプレートや、より詳しい運用手順（cron/CI での ETL 実行、バックアップ等）を作成したい場合は教えてください。