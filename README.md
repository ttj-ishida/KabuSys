# KabuSys

日本株向けの自動売買システム用ライブラリ。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを包含したモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つ Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー等のデータ取得（RateLimit・リトライ・トークン自動リフレッシュ対応）
- DuckDB ベースのデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究（research）用のファクター計算・特徴量探索ユーティリティ
- 戦略（strategy）用の特徴量合成とシグナル生成（BUY/SELL判定、エグジット判定を含む）
- ニュース収集（RSS）とテキスト前処理・銘柄抽出
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 発注・監査用テーブル定義（監査ログ、order_requests、executions 等）

設計方針として、
- ルックアヘッドバイアスの排除（target_date 時点のデータのみを使用）、
- 冪等性（DB へは ON CONFLICT / ON CONFLICT DO UPDATE / DO NOTHING を利用）、
- 本番 API への不要な依存を持たない（研究用関数は DB の prices_daily/raw_financials のみ参照）、
- ネットワーク保護（SSRF 対策、受信サイズ制限、XML の安全パーサ使用）、
を重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数チェック
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限、リトライ、トークン自動リフレッシュ、ページネーション対応
  - データ保存（raw_prices, raw_financials, market_calendar）用の冪等保存関数
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新、自動バックフィル機能
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、記事ID生成、raw_news 保存、銘柄抽出と news_symbols への紐付け
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 研究用（kabusys.research）
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索）
- 戦略（kabusys.strategy）
  - build_features: 生ファクターの正規化・ユニバースフィルタ適用・features テーブルへの書込み
  - generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブル定義・初期化ロジック

---

## 前提 / 依存関係

- Python 3.10+（| 型アノテーション等を使用）
- 必要なライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, typing など

（プロジェクトに requirements.txt があればそれを使用してください。上記はコードから読み取れる主要な依存です）

---

## セットアップ手順

1. リポジトリをクローン／コピーする

2. 仮想環境を作成して有効化
   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール
   - 最小例:
     pip install duckdb defusedxml
   - 開発中はプロジェクトルートに setup.py / pyproject.toml があれば:
     pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（kabusys.config.Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development/paper_trading/live。デフォルト: development)
     - LOG_LEVEL (DEBUG/INFO/...)

   例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. データベーススキーマ初期化
   - Python から DuckDB のスキーマを作成します。デフォルトの DB パスを使う場合は settings.duckdb_path を参照して init_schema を呼び出すと便利。

   例:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

---

## 使い方（簡単なサンプル）

以下は代表的な操作の例です。実運用ではログ設定や例外処理、スケジューラ（cron / Airflow 等）と組み合わせてください。

- DB 初期化（1回）
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー取得→株価/財務取得→品質チェック）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema で作成した接続
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量構築（features テーブルへ書き込み）
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルへ書き込み）
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS から raw_news を保存し、既知コードで news_symbols を紐付け）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は有効な銘柄コードの集合（例: {"7203","6758",...}）
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

- マーケットカレンダーの夜間更新
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- J-Quants から日足を直接取得して保存（テストなど）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, recs)

注意: 上記の多くの関数は DuckDB の接続を直接受け取ります（kabusys.data.schema.get_connection / init_schema で接続を作成して渡してください）。

---

## 実装上のポイント / 注意事項

- ルックアヘッドバイアス回避のため、戦略や特徴量構築関数は target_date 時点までの情報のみを参照する設計になっています。
- ETL は差分取得・バックフィルを行い、冪等に保存する（ON CONFLICT を使用）。再実行しても重複挿入されません。
- J-Quants API 呼び出しは固定インターバルの RateLimiter とリトライロジックを備えています。401 はリフレッシュトークンで自動更新されます。
- ニュース収集では SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ制限を実装しています。
- DuckDB スキーマは外部キーやチェック制約を定義していますが、DuckDB のバージョンによってサポート状況が異なるため README の実行環境に応じて確認してください。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
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
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (モニタリング関連モジュール - 本コードベースでは placeholder)

上記の各モジュールにはモジュール docstring と詳細な関数単位の docstring が付与されており、内部仕様（設計方針、処理フロー、注意点）を明記しています。API の利用方法は各モジュールの docstring を参照してください。

---

## テスト / 開発

- 自動環境変数ロードを無効化して単体テストしやすくするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対しては ":memory:" を指定してインメモリでテスト可能です（init_schema(":memory:")）。
- ネットワーク呼び出しを伴う関数は id_token の注入や HTTP 用のオープナーをモックしてテスト可能な設計になっています（例: news_collector._urlopen をモックなど）。

---

## 補足

- ロギングは各モジュールで logging.getLogger(__name__) を用いて行っています。運用環境では適切にハンドラとレベルを設定してください。
- 本 README はコードベースの現状（主要モジュール・関数）を要約したものです。さらに詳細な仕様（StrategyModel.md、DataPlatform.md 等）がプロジェクト内にあればそちらも参照してください。

ご要望があれば、使い始めのワークフロー（最小構成での ETL → feature → signal の実行スクリプト例）や各モジュールの API リファレンス的なセクションを追加で作成します。どの情報が必要か教えてください。