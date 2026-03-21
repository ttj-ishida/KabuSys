# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム（データ収集・ETL・特徴量生成・シグナル生成・監査用スキーマ）を目的とした Python パッケージです。J-Quants API や RSS フィードからデータを取得して DuckDB に蓄積し、研究→戦略→実行の各層を分離して設計されています。

主な設計方針:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ参照）
- DuckDB を中心に冪等（idempotent）な保存処理を行う
- API のレート制限・リトライ・トークン更新などに対応
- XML/HTTP の安全対策（defusedxml、SSRF 対策等）を実装

---

## 機能一覧

- 環境変数 / 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、無効化フラグあり）
  - 必須項目のバリデーション
- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応）
  - レート制限・リトライ・401 時の自動トークンリフレッシュ
- データ保存（DuckDB）
  - raw / processed / feature / execution 層のスキーマ定義と初期化
  - ON CONFLICT による冪等保存（INSERT ... ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分取得（最終取得日を参照）、バックフィル再取得、品質チェック呼び出し
  - 市場カレンダー ETL / 株価 ETL / 財務 ETL の個別実行
- 研究用モジュール
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略（特徴量・シグナル）
  - features テーブル構築（正規化・ユニバースフィルタ・クリップ）
  - final_score 計算と BUY/SELL シグナル生成（Bear レジーム判定・エグジット判定含む）
- ニュース収集
  - RSS フィードの取得 / 前処理 / raw_news 保存 / 銘柄抽出と紐付け
  - SSRF 対策・サイズ制限・XML 脆弱性対策
- 監査ログスキーマ（signal → order → execution のトレーサビリティ）

---

## 必要条件

- Python 3.10 以上（PEP 604 の union 型 などを利用）
- 推奨ライブラリ（インストール例は次節参照）
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装されている箇所も多いですが、DuckDB / defusedxml は必須です。

---

## セットアップ手順

1. リポジトリをクローン / コピーする
   - 省略

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt を作成している場合は `pip install -r requirements.txt` を使用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
   - 必須環境変数の例（最低限）:

     .env.example:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 必須項目（Settings._require によりチェックされる）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから以下を実行して DB を初期化します:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - デフォルトの DB パスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）

---

## 使い方（簡易ガイド）

ここでは主要なユースケースごとに最小の利用例を示します。実運用ではエラーハンドリングやログ設定を適切に行ってください。

1) スキーマ初期化（1回だけ）
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行してデータを取得・保存する
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())

3) 特徴量（features）を構築する
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   import datetime
   conn = get_connection("data/kabusys.duckdb")
   cnt = build_features(conn, datetime.date(2024, 1, 31))
   print(f"features upserted: {cnt}")

4) シグナルを生成する
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   import datetime
   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, datetime.date(2024, 1, 31))
   print(f"signals generated: {total}")

5) ニュース収集ジョブ（RSS）
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection
   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203","6758", ...}  # あらかじめ用意した銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)

6) 市場カレンダー更新ジョブ
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection
   import datetime
   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

---

## 主要モジュール / API（抜粋）

- kabusys.config
  - settings: アプリ設定（環境変数経由）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で .env の自動読み込みを無効化可

- kabusys.data
  - schema.init_schema(db_path) / get_connection(db_path)
  - jquants_client: fetch_* / save_* 関数（API クライアント）
  - pipeline.run_daily_etl(...)
  - news_collector.run_news_collection(...)
  - calendar_management.*（is_trading_day, next_trading_day など）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

---

## ディレクトリ構成

想定されるソースツリー（抜粋）:

src/
  kabusys/
    __init__.py                 # パッケージ宣言（__version__ = "0.1.0"）
    config.py                   # 環境変数・設定管理
    data/
      __init__.py
      schema.py                 # DuckDB スキーマ定義・init_schema
      jquants_client.py         # J-Quants API クライアント（取得/保存）
      pipeline.py               # ETL パイプライン（run_daily_etl 等）
      news_collector.py         # RSS 収集・保存・銘柄抽出
      calendar_management.py    # 市場カレンダー管理
      stats.py                  # zscore_normalize 等の統計ユーティリティ
      features.py               # data 層の feature ユーティリティ（再エクスポート）
      audit.py                  # 監査ログスキーマ（signal/order/execution）
      execution/                 # 発注関連（プレースホルダ）
    research/
      __init__.py
      factor_research.py        # ファクター計算（mom/vol/value 等）
      feature_exploration.py    # IC / forward returns / summary
    strategy/
      __init__.py
      feature_engineering.py    # features テーブル構築ロジック
      signal_generator.py       # final_score 計算・シグナル生成ロジック
    execution/                   # 発注層（空の __init__ 等）
    monitoring/                  # 監視・メトリクス関連（プレースホルダ）
README.md

---

## 設定（環境変数一覧）

主に以下の環境変数を利用します（全てを列挙しているわけではありません。必須は Settings 内の _require を参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

---

## 開発・貢献

- コードはモジュールごとに責務が分離されています。新機能追加の際は既存の層（data / research / strategy / execution）を尊重してください。
- 単体テスト・統合テストは各モジュールの入出力（DuckDB 接続、id_token 注入、HTTP のモック化等）を注入可能にする設計を活用してください。
- ライセンスや CI 設定はこの README に含まれていません。リポジトリに LICENSE を追加し、CI（lint / pytest / mypy 等）の導入を推奨します。

---

もし README に追加したい内容（例: 実運用のデプロイ手順、cron ジョブ例、Slack 通知例、サンプルデータのロード方法、具体的な .env.example）や、別フォーマット（日本語 + 英語二言語化）があれば教えてください。