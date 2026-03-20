# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、カレンダー管理、監査（オーダー／約定トレーサビリティ）、DuckDB スキーマ管理などを包含します。本 README はコードベース（src/kabusys/*）の概要、セットアップ、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的: J-Quants 等から市場データを取得して DuckDB に保存し、研究→本番へつなげる自動売買ワークフローを構築する。
- 主な特徴:
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - DuckDB ベースの3層データ設計（Raw / Processed / Feature / Execution）
  - ETL パイプライン（差分更新・バックフィル・品質チェック）
  - 特徴量計算（momentum / volatility / value 等）と Z スコア正規化
  - シグナル生成ロジック（コンポーネントスコア、重み付け、Bear レジーム抑止、エグジット判定）
  - ニュース収集（RSS → raw_news、URL 正規化・SSRF 対策・トラッキングパラメータ除去）
  - 市場カレンダー管理（JPX カレンダーの取得・営業日判定ユーティリティ）
  - 監査テーブル群（signal_events / order_requests / executions 等）

---

## 機能一覧（概要）

- 環境/設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` をロード（無効化可能）
  - settings オブジェクト経由で必須設定を取得

- データ取得 / 保存（kabusys.data.jquants_client）
  - 日足 / 財務 / カレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ（指数バックオフ）、401 のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィル・品質チェック（quality モジュール）
  - 日次 ETL エントリ（run_daily_etl）

- DuckDB スキーマ管理（kabusys.data.schema）
  - 全テーブル定義と初期化（init_schema）
  - インデックス作成、実運用に必要なテーブル設計

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の安全パース、記事ID の一意化、raw_news 保存と銘柄紐付け
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

- 研究・ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等

- 特徴量・シグナル生成（kabusys.strategy）
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=?, weights=?)

- 監査・実行レイヤ（schema 内にテーブル定義）
  - signal_events, order_requests, executions, orders, trades, positions 等

---

## 前提・依存関係

- Python >= 3.10（型注釈に `X | None` を使用）
- 主要 Python パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリを多用（urllib, datetime, logging, json 等）

必要な依存パッケージはプロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください。最小例:

pip install duckdb defusedxml

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値があると無効）
- KABUSYS_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

※ `.env` をプロジェクトルートに置くと自動で読み込まれます（.git または pyproject.toml を探索してプロジェクトルートを判定）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml/requirements.txt があれば pip install -r requirements.txt や pip install -e . を実行）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成する（例は下記）
     .env.example:
       JQUANTS_REFRESH_TOKEN=your_refresh_token
       KABU_API_PASSWORD=your_kabu_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       KABUSYS_ENV=development
5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - または in-memory:
     conn = init_schema(":memory:")

---

## 使い方（基本例）

以下は Python スクリプト／REPL での利用例です。conn は duckdb の接続オブジェクト（kabusys.data.schema.init_schema の戻り値）です。

- DB の初期化（1回だけ）
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量の構築（研究モジュールで算出したファクターを正規化・保存）
  from kabusys.strategy import build_features
  from datetime import date
  cnt = build_features(conn, target_date=date(2024, 1, 5))
  print(f"upserted features: {cnt}")

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, target_date=date(2024, 1, 5))
  print(f"signals written: {total_signals}")

- ニュース収集ジョブ実行
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  # known_codes は抽出対象の有効銘柄セット（例: 全コードの set）
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(results)

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- J-Quants から日足を直接フェッチして保存
  from kabusys.data import jquants_client as jq
  rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
  saved = jq.save_daily_quotes(conn, rows)

注意:
- すべての DB 書き込み関数は冪等性（ON CONFLICT）を念頭において実装されています。
- シグナル生成・特徴量構築は target_date 時点のデータのみを使用し、ルックアヘッドバイアスを排除する設計です。

---

## .env の例

例（プロジェクトルートに `.env` を作成）:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## ディレクトリ構成（src/kabusys）

主要ファイル・モジュールの要約:

- __init__.py
  - パッケージエクスポート定義

- config.py
  - 環境変数読み込み・settings オブジェクト

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / rate limit / retry）
  - news_collector.py — RSS 収集・前処理・DB 保存
  - schema.py — DuckDB テーブル定義・init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - calendar_management.py — カレンダー管理／ジョブ
  - audit.py — 監査ログ用テーブル定義（signal_events, order_requests, executions など）
  - features.py — data.stats の再エクスポート

- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

- strategy/
  - __init__.py — build_features, generate_signals を公開
  - feature_engineering.py — ファクター統合／正規化→features テーブル書き込み
  - signal_generator.py — final_score 計算、BUY/SELL シグナル生成、signals テーブル書き込み

- execution/ (空の __init__.py が存在し、実行レイヤの実装を想定)

- monitoring/（README の要求に含めるがコード中は SQLite 用 path; 実装ファイルは別途配置想定）

---

## 補足・運用上の注意

- Python のバージョン要件に注意（3.10 以上）。
- J-Quants API レート制限や認証の取り扱い（トークン更新）に注意すること。
- DuckDB のバックアップやファイル配置（DUCKDB_PATH）は運用環境に合わせて設定してください。
- 本コードには paper_trading / live 切替ロジックのフラグがあり、KABUSYS_ENV により挙動を切り替えられます。実運用前に十分な確認を行ってください。
- セキュリティ: .env に機密情報が含まれるため、適切に管理してください。

---

必要であれば、README に含めるコマンド例（unit test、CI、より具体的な env.example、運用手順書）や各モジュールの詳細ドキュメント（API 引数・戻り値の完全表記）を追記します。どの情報を優先して追加しますか？