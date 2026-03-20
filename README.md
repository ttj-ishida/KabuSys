# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、DuckDB スキーマ／監査ログなどを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制御・リトライ）
  - 株価日足・財務データ・市場カレンダーの取得 / DuckDB への冪等保存
- ETL パイプライン
  - 差分取得（最終取得日を基に差分・バックフィル）
  - 日次 ETL 実行（calendar / prices / financials + 品質チェック）
- データ層（DuckDB）スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル作成とインデックス
  - スキーマ初期化：init_schema()
- ニュース収集
  - RSS フィード取得（SSRF対策・gzip対応・サイズ制限・XML サニタイズ）
  - 記事正規化・ID生成（URLノイズ除去）・raw_news/ news_symbols への保存
- 研究（research）ユーティリティ
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Spearman）やファクター統計
  - Z スコア正規化ユーティリティ
- 戦略層
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）: final_score 計算、BUY/SELL 生成、SELL 優先ポリシー
- 監査・トレーサビリティ設計（監査用 DDL が含まれる）

---

## 動作要件

- Python 3.10 以上（| 型注釈や型演算子を使用）
- 主要依存（例）
  - duckdb
  - defusedxml
- （プロジェクト外の依存を固定している場合は pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone ... またはアーカイブを展開

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（最小）:
     - pip install duckdb defusedxml

   - パッケージ開発インストール（プロジェクトで setuptools/poetry を利用している場合）:
     - pip install -e .

4. 環境変数の設定
   - .env または環境変数で設定します（自動ロード機構あり、後述）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: sqlite（監視DB等）のパス（デフォルト: data/monitoring.db）

   - 自動 .env ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml を基準） を探し、`.env` と `.env.local` を自動読み込みします。
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB が使えます（テスト用途）。

---

## 使い方（基本例）

以下は最小限の利用例（Python）です。

- DuckDB の初期化と接続:
  - from kabusys.data.schema import init_schema, get_connection
  - conn = init_schema("data/kabusys.duckdb")  # テーブル作成と接続返却
  - # 既存 DB に接続する場合:
  - conn = get_connection("data/kabusys.duckdb")

- 日次 ETL の実行:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を省略すると今日の営業日を基準に処理
  - print(result.to_dict())

- 特徴量構築（戦略用 features テーブルを作成）:
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 31))
  - print(f"upserted features: {n}")

- シグナル生成:
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, date(2024, 1, 31))
  - print(f"generated signals: {total}")

- J-Quants データ取得・保存（低レベル）:
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - saved = jq.save_daily_quotes(conn, records)

- RSS ニュース収集:
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  - print(results)

---

## 主要 API の説明（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id などをプロパティ経由で参照できます。
  - KABUSYS_ENV の有効値: "development", "paper_trading", "live"

- データベース / スキーマ
  - init_schema(db_path) -> DuckDB 接続（テーブルを作成）
  - get_connection(db_path) -> 既存 DB に接続

- ETL / Pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ

- J-Quants クライアント
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar

- ニュース収集
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[source -> saved_count]

- 研究 / 戦略
  - research.calc_momentum/ calc_volatility/ calc_value
  - strategy.build_features(conn, target_date) -> upsert count
  - strategy.generate_signals(conn, target_date, threshold=0.6, weights=None) -> total signals written

---

## ディレクトリ構成（主要ファイル）

例: src/kabusys 以下の主要モジュール構成

- src/kabusys/
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
  - monitoring/  (パッケージ名は __all__ に含むが実装は別に存在する可能性があります)

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): monitoring 用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL (任意): ログレベル（DEBUG/INFO/...）

自動 .env 読み込みの仕組み:
- プロジェクトルート（.git または pyproject.toml）を起点に `.env` および `.env.local` を読み込みます。
- OS の環境変数が優先され、`.env.local` は上書きが有効です。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 注意事項 / 運用上のポイント

- ルックアヘッドバイアス対策:
  - research / strategy 層は target_date 時点までの情報のみを用いる設計です。データの fetched_at や market_calendar を用いた営業日調整に注意してください。
- DuckDB スキーマは冪等に作成されますが、初回は init_schema を確実に呼んでください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部で固定間隔スロットリングとリトライを行います。
- ニュース収集では SSRF 対策や XML の安全パースを実装していますが、外部ソースの取り扱いには注意してください。
- KABUSYS_ENV を "live" に設定すると本番向け挙動（フラグ）を返すプロパティが True になります。実運用時は設定ミスに注意。

---

## 開発・テスト

- 単体テスト用に DuckDB の ":memory:" を使用できます（schema.init_schema(":memory:")）。
- jquants_client._urlopen / news_collector._urlopen 等はモック可能に設計されています。
- CI / 自動化では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、テスト用の環境変数注入を行ってください。

---

必要に応じて README のサンプルコードや具体的な DB スキーマのドキュメント（DataSchema.md）、戦略モデル仕様（StrategyModel.md）、データプラットフォーム仕様（DataPlatform.md）を生成できます。追加でそのようなドキュメントを希望する場合は教えてください。