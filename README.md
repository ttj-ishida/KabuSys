# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（kabusys）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、監査テーブルなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下のレイヤーを備えた日本株自動売買基盤用の Python モジュール群です。

- データ取得層（J-Quants API クライアント）
- データストレージ（DuckDB スキーマ定義・初期化）
- ETL パイプライン（差分取得、保存、品質チェックの統合）
- リサーチ／特徴量計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（正規化・フィルタリング・features テーブルへの保存）
- シグナル生成（features + AI スコア統合 → BUY/SELL 判定）
- ニュース収集（RSS フィードの収集・前処理・銘柄紐付け）
- マーケットカレンダー管理（JPX カレンダーの取得・営業日の判定）
- 監査・トレーサビリティ（signal → order → execution のログ）

設計上のポイント:
- ルックアヘッドバイアス防止を重視（target_date 時点のデータのみを使用）
- DuckDB を永続ストレージとして使用、DDL は冪等に実行可能
- API レート／リトライ制御、RSS の SSRF 対策など実運用を想定した堅牢性

---

## 主な機能一覧

- J-Quants API クライアント（取得・保存・トークンリフレッシュ・レート制御）
  - 株価（日足）、財務データ、マーケットカレンダー取得
- DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック統合）
- ファクター計算（momentum / volatility / value 等）
- 特徴量構築（ユニバースフィルタ、Zスコア正規化、features への UPSERT）
- シグナル生成（ファクター合成、AI スコア取込、BUY/SELL 生成、signals テーブルへの保存）
- RSS ニュース収集と銘柄抽出（正規化・トラッキング除去・SSRF/サイズ制限）
- マーケットカレンダー更新・営業日判定ユーティリティ
- 監査ログ（signal_events / order_requests / executions 等）のDDL・初期化

---

## セットアップ手順

1. リポジトリをクローン（例）:
   - git clone <your-repo-url>

2. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（パッケージ化されている場合）:
   - pip install -e .

   または最低限必要な依存を直接インストール:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを利用してください）

4. 環境変数 / .env の準備

   必須環境変数（アプリ起動時に Settings プロパティから参照されます）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等に使用）
   - SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
   - LOG_LEVEL   = DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
   - DUCKDB_PATH = data/kabusys.duckdb (デフォルト)
   - SQLITE_PATH = data/monitoring.db (デフォルト)
   - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 を設定すると .env 自動ロードを無効化

   .env のサンプル例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   実行環境では .env（および .env.local）から自動で読み込まれます（config._find_project_root によりプロジェクトルートを検出）。

---

## 使い方（簡易ガイド）

以下は Python REPL / スクリプトで使う基本例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants からデータ取得 → 保存 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- マーケットカレンダーバッチ更新
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出用の有効コード集合（例: {'7203','6758',...}）
  results = run_news_collection(conn, known_codes=set(), sources=None)
  print(results)
  ```

- ファクター計算 / 特徴量構築
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date(2025, 1, 1))
  print("features upserted:", n)
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date(2025, 1, 1))
  print("signals written:", total)
  ```

- J-Quants の生データ保存（低レベル利用）
  ```python
  from kabusys.data import jquants_client as jq
  # id_token を明示的に取得/指定したい場合
  token = jq.get_id_token()
  records = jq.fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

ログレベルは環境変数 LOG_LEVEL で制御できます。運用環境では KABUSYS_ENV を `live` に設定してください（settings.is_live を利用した制御が可能）。

---

## 推奨ワークフロー（例）

1. 初回: DB 初期化
   - init_schema を実行
2. 夜間バッチ（cron / Airflow 等）:
   - calendar_update_job（カレンダーの先読み）
   - run_daily_etl（ETL：prices / financials / calendar 保存 + 品質チェック）
   - build_features（特長抽出）
   - generate_signals（シグナル生成）
   - signal_queue / execution 層へ引き渡し（発注コンポーネントにより実装）

---

## 注意事項 / 運用上のポイント

- settings は環境変数を参照します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます。
- J-Quants API 呼び出しはレート制限（120 req/min）に合わせた RateLimiter、リトライ、トークン自動リフレッシュロジックが組み込まれています。
- RSS フェッチは SSRF 対策、最大応答サイズ制限、gzip 解凍後のサイズチェックなど安全対策を含みます。
- DuckDB の DDL は冪等（IF NOT EXISTS、ON CONFLICT）を使用しています。スキーマの変更・マイグレーションは別途検討してください。
- 実際の発注（証券会社連携）部分はプロジェクトセットの外部モジュールや execution 層の実装に依存します。本ライブラリはデータ・シグナル生成と監査ログの整備に注力しています。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他: quality.py 等が想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/           (発注・約定処理用の名前空間、実装は外部依存の可能性あり)
  - monitoring/          (監視関連モジュール)
  - (その他ユーティリティ)

この README で示した主要 API:
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client.* (fetch_*, save_*)
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.calendar_management.calendar_update_job / is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- kabusys.research.calc_* / zscore_normalize
- kabusys.strategy.build_features / generate_signals

---

## 貢献 / 開発メモ

- 単体テスト、CI、モック（特に外部 HTTP/DB 呼び出しの差し替え）を推奨します。
- 環境依存部分（J-Quants トークン、kabu API、Slack トークン）は機密情報であり、.env や環境変数で安全に管理してください。
- スキーマ拡張やマイグレーションは DuckDB の仕様を考慮して慎重に行ってください。

---

これで README の概要は終了です。必要であれば、セットアップ手順の Docker 化、サンプル .env.example の追加、CI 用のテストコマンド、より詳細な API リファレンスを追記します。どれを優先しますか？