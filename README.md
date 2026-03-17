# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けデータパイプライン・監査・ユーティリティ群です。本リポジトリは主に以下を提供します。

- J-Quants API 経由での市場データ取得（株価・四半期財務・JPX カレンダー）
- RSS ベースのニュース収集（前処理・SSRF 対策・銘柄抽出・DuckDB 保存）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、夜間更新ジョブ）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

現在、strategy, execution, monitoring パッケージの骨組みがあり、実際の売買ロジックやブローカー連携の実装は拡張可能です。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのデータ取得（株価日足、財務、マーケットカレンダー）
  - レート制限（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動更新
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - fetched_at による取得時刻トレース（Look-ahead Bias 対策）
- data.news_collector
  - RSS フィード取得、XML パース（defusedxml 使用）、SSRF 対策、gzip 対応
  - URL 正規化と SHA-256 ベースの記事 ID、前処理（URL除去・空白正規化）
  - DuckDB への冪等保存（INSERT ... RETURNING）と銘柄紐付け
- data.schema / audit
  - DuckDB における包括的なスキーマ（Raw / Processed / Feature / Execution / Audit）
  - 監査向けテーブル（signal_events, order_requests, executions）とインデックス
- data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェック、カレンダー先読み）
  - ETLResult で実行結果 / 品質問題を返却
- data.calendar_management
  - 営業日判定 / next/prev 営業日取得 / カレンダー更新ジョブ
- data.quality
  - 欠損、スパイク、重複、日付不整合などのチェックを実施

---

## 前提 / 必須環境変数

必須の環境変数（実行前に設定してください）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（将来的な実装向け）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

任意 / デフォルト値:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視系 DB（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

注意: config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動で読み込みます。テストなどで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## インストール / セットアップ手順

推奨 Python バージョン: 3.9+

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須パッケージ: duckdb, defusedxml
   - 例:
     - pip install -e .   （パッケージ化されている場合）
     - または pip install duckdb defusedxml

   （実際の requirements.txt はプロジェクトに合わせて作成してください）

4. 環境変数設定
   - ルートに .env または .env.local を作成して必要なキーを設定してください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから schema.init_schema を呼び出します（デフォルトのパスを使用する場合は settings.duckdb_path）。
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

6. 監査テーブル初期化（必要であれば）
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   - または既存の conn に対して init_audit_schema(conn)

---

## 使い方（代表的な API/ワークフロー例）

以下は Python スクリプトや REPL からの呼び出し例です。

- DuckDB スキーマ初期化（1回）
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場データ取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema しておく
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブ実行
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知銘柄コードのセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

- カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved={saved}")

- 監査ログ初期化（既存 conn に追加）
  from kabusys.data.audit import init_audit_schema
  conn = schema.get_connection("data/kabusys.duckdb")
  init_audit_schema(conn)

- 設定取得（環境変数）
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

ログやエラーは標準的に logging を通じて出力されます。LOG_LEVEL 環境変数で制御してください。

---

## 実装上のポイント / 挙動

- jquants_client は API レート制限（120 req/min）に合わせて内部でスロットリングを行います。
- HTTP エラー時のリトライ（指数バックオフ）、401 でのトークン自動リフレッシュを実装済みです。
- データ保存は基本的に冪等（ON CONFLICT）で行われるため、繰り返し取得でも上書き/重複回避されます。
- news_collector は SSRF/ZIP/XML Bomb 対策（スキーム検証、プライベート IP 拒否、受信サイズ上限、defusedxml）を施して安全性を高めています。
- quality モジュールは Fail-Fast ではなく全チェックを実行し、重大度に応じて呼び出し元が判断する設計です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数／設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py      - RSS ニュース収集・前処理・保存
    - schema.py              - DuckDB スキーマ定義と init_schema
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py - マーケットカレンダー更新 / 営業日判定
    - audit.py               - 監査ログテーブルの定義・初期化
    - quality.py             - データ品質チェック
  - strategy/
    - __init__.py            - 戦略層のパッケージ（拡張用）
  - execution/
    - __init__.py            - 発注・ブローカー連携パッケージ（拡張用）
  - monitoring/
    - __init__.py            - 監視 / メトリクス用パッケージ（拡張用）

---

## 注意事項 / 今後の拡張

- ブローカー連携（発注送信 / 約定取得）は execution パッケージに実装してください（kabuステーション等）。
- strategy パッケージに戦略ロジックを実装し、signal -> audit/order_request -> order のフローを監査テーブルへ記録することを推奨します。
- 運用時は KABUSYS_ENV を適切に設定し（paper_trading/live）、ログ・テスト環境と実取引環境を分離してください。
- .env.example のようなテンプレートをプロジェクトルートに置くと新規環境構築が容易になります（本リポジトリ内には含まれていない場合があるため追加を推奨）。

---

もし README にサンプルスクリプトや CI/CD 実行手順、より詳しい API リファレンス（関数ごとの引数説明や例）を追記してほしい場合は、どの箇所を重点的に拡充するか教えてください。