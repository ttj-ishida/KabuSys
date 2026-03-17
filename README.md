# KabuSys

日本株自動売買プラットフォーム（ライブラリ）KabuSys の README（日本語）

概要
- KabuSys は日本株のデータ収集、ETL、品質チェック、監査ログ、ニュース収集、マーケットカレンダー管理などを備えた自動売買システム向けの共通ライブラリ群です。
- 主に以下を提供します：
  - J-Quants API クライアント（株価、財務、マーケットカレンダーの取得）
  - DuckDB ベースのスキーマ定義・初期化
  - 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
  - RSS ベースのニュース収集と銘柄紐付け
  - マーケットカレンダーの管理（営業日判定・next/prev）
  - 監査ログ（シグナル→発注→約定のトレース）
- パッケージはモジュール化されており、strategy / execution / monitoring 層と連携して利用できます。

主な機能一覧
- データ取得
  - J-Quants API から日次株価（OHLCV）、四半期財務（BS/PL）、JPX カレンダーを取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- ETL / データ保存
  - DuckDB に Raw / Processed / Feature / Execution 層のテーブルを定義・初期化
  - 差分更新（最終取得日から必要分のみ取得）とバックフィル
  - 保存時は冪等（ON CONFLICT DO UPDATE / DO NOTHING）
- 品質管理
  - 欠損値検出、主キー重複、前日比スパイク検出、将来日付 / 非営業日データ検出
  - 問題は QualityIssue オブジェクトで集約（error / warning）
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策・gzip 制限・defusedxml）
  - URL 正規化、トラッキングパラメータ除去、SHA-256 ハッシュベースの記事ID生成
  - raw_news への冪等保存、記事と銘柄コードの紐付け
- マーケットカレンダー
  - market_calendar を用いた営業日判定（DB 優先、未登録日は曜日フォールバック）
  - next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等
- 監査ログ
  - signal_events / order_requests / executions テーブルでシグナルから約定までを UUID 連鎖でトレース
  - すべての TIMESTAMP を UTC で扱う設計

前提・依存関係
- Python 3.10 以上（型注釈に | 演算子を使用）
- 推奨パッケージ（代表）
  - duckdb
  - defusedxml
- そのほか標準ライブラリ（urllib, json, datetime 等）を使用

セットアップ手順（開発向け）
1. リポジトリをクローンし仮想環境を作成
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール
   - 代表的なパッケージ:
     pip install duckdb defusedxml
   - requirements.txt があれば:
     pip install -r requirements.txt

3. 環境変数（.env）の準備
   - 自動ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある .env/.env.local を自動で読み込みます（ただし OS 環境変数が優先されます）。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
   - 必須環境変数（名前と用途）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack 通知先チャネル ID（必須）
   - 任意 / デフォルト
     - KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : 実行環境（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

4. DuckDB スキーマ初期化（例）
   - メインデータベース（デフォルトパスに作成）
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - 監査ログ専用 DB（オプション）
     python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"

基本的な使い方（Python API 例）
- DuckDB 接続の初期化（スキーマ作成）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL の実行（run_daily_etl）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 市場カレンダーの夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)

- RSS ニュース収集（既知銘柄セットを渡して銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- 監査スキーマ初期化（既存接続へ）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

設定と運用のポイント
- 環境変数優先順位: OS 環境変数 > .env.local > .env
- 自動 .env ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用
- J-Quants の API はレート制限（120 req/min）に合わせて内部的にスロットリングがあります。大量のバッチ処理時は待機時間に注意してください。
- ETL は差分更新 + 小さなバックフィル（デフォルト 3 日）で API の後出し修正を吸収します。バックフィル日数は pipeline API の引数で変更可能です。
- DuckDB はファイルベースですが、":memory:" を指定するとインメモリ DB を利用できます（テスト時に便利）。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                : 環境変数・設定管理（.env 自動ロード・Settings）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      : RSS ニュース収集・保存・銘柄抽出
    - schema.py              : DuckDB スキーマ定義・初期化 API
    - pipeline.py            : ETL パイプライン（run_daily_etl など）
    - calendar_management.py : マーケットカレンダー管理（営業日判定、update job）
    - audit.py               : 監査ログ（signal/order/execution）DDL と初期化
    - quality.py             : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/                 : 戦略用モジュール（拡張ポイント）
  - execution/                : 発注 / ブローカー連携用モジュール（拡張ポイント）
  - monitoring/               : 監視・メトリクス用モジュール（拡張ポイント）

運用上の注意
- すべての時刻は設計上 UTC を使うよう配慮しています（監査ログなど）。
- ETL・ニュース収集は外部 API に依存するため、エラーハンドリングは各関数で実施しますが、運用側でリトライやアラートを用意してください（Slack 連携を想定）。
- 監査ログは削除しない前提です。ストレージ管理・アーカイブ計画を立ててください。

開発・拡張
- strategy / execution / monitoring パッケージは空の初期化ファイルがあり、独自戦略やブローカー連携はここに実装して組み合わせます。
- テスト時は settings の自動 .env ロードを無効化して明示的に環境を注入すると再現性が高まります。

ライセンス・貢献
- 本リポジトリに LICENSE ファイルがあればそれに従ってください。貢献方法としては PR を送るか issue を作成してください。

以上が KabuSys の概要と基本的な使い方です。実際の運用では API トークン・取引パラメータ・リスク管理ロジックを十分に精査した上でご利用ください。必要であれば README にサンプル .env.example や CI/デプロイ手順、より詳細な API 利用例を追加できます。どの情報が欲しいか教えてください。