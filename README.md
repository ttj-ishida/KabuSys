# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（ライブラリ層）。  
本リポジトリはデータ取得・ETL、特徴量計算、シグナル生成、監査ログなどの基盤機能を提供します。

- Python >= 3.10 を想定（PEP 604 の `X | Y` 記法、`from __future__ import annotations` を使用）
- 内部DBに DuckDB を使用
- 外部パッケージ例: duckdb, defusedxml（RSS パース用）、標準ライブラリの urllib 等

---

## 概要

KabuSys は次のレイヤーで構成されます。

- Data layer: J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）、RSS ニュース収集、DuckDB スキーマ定義・初期化、ETL パイプライン。
- Research layer: ファクター計算（モメンタム / ボラティリティ / バリュー）と統計解析（IC / forward returns / summary）。
- Strategy layer: 特徴量を組み合わせて正規化・統合し、最終スコアから売買シグナル（BUY/SELL）を生成。
- Execution / Audit: 発注・約定・ポジション管理のためのスキーマ、監査ログ設計（order_request / executions 等）。  
  （execution 層の具体的な証券会社連携は本コードベースでは抽象化されています）

設計上のポイント:
- 冪等性（DB保存は ON CONFLICT やトランザクションで保証）
- ルックアヘッドバイアス対策（target_date 時点のデータのみ参照）
- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants クライアント）
- RSS 収集における SSRF 防止・XML の安全パース（defusedxml）などセキュリティ考慮

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須キーの検査、KABUSYS_ENV / LOG_LEVEL 等
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制御、再試行、トークン自動更新
  - fetch / save の idempotent な実装（daily_quotes / financials / market_calendar）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / 個別 ETL（prices / financials / calendar）
  - 差分更新・バックフィル・品質チェック呼び出し
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news 保存、銘柄コード抽出と紐付け
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev trading day、更新ジョブ
- ファクター計算（kabusys.research.factor_research）
  - Momentum / Volatility / Value
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - ファクター統合・Zスコア正規化・ユニバースフィルタ・features テーブルの UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - コンポーネントスコア計算、重み合成、Bear レジーム抑制、BUY/SELL の判定、signals テーブルへ保存
- 統計ユーティリティ（kabusys.data.stats, research.feature_exploration）
  - Z スコア正規化、forward returns、IC（Spearman）、summaries
- 監査ログ関連 DDL（kabusys.data.audit）
  - signal_events / order_requests / executions 等

---

## セットアップ手順

以下はローカルで開発・利用するための基本手順例です。

1. リポジトリをクローンしてワークディレクトリへ移動

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   開発インストール（パッケージ化されている場合）:
   pip install -e .

4. 環境変数設定（.env ファイルをプロジェクトルートに作成）

   必須環境変数例:
   - JQUANTS_REFRESH_TOKEN=...     # J-Quants リフレッシュトークン
   - KABU_API_PASSWORD=...         # kabu API パスワード（発注連携時）
   - SLACK_BOT_TOKEN=...           # 通知用 Slack Bot トークン
   - SLACK_CHANNEL_ID=...          # 通知先 Slack チャンネル ID

   任意 / デフォルト:
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development | paper_trading | live
   - LOG_LEVEL=INFO

   ※ パッケージの config モジュールはプロジェクトルート（.git or pyproject.toml を元に）から .env/.env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB スキーマ初期化

   Python REPL またはスクリプトで:

   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   conn.close()

   デバッグ用にメモリ DB を使う場合:
   conn = init_schema(":memory:")

---

## 使い方（主要な利用例）

以下は主要なAPIの利用例（概略）。各関数は DuckDB 接続と target_date を受け取る設計です。

- DB 初期化（上記参照）

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）

   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

- 特徴量構築（features テーブルへの書き込み）

   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 3, 1))
   print(f"features upserted: {n}")

- シグナル生成（signals テーブルへの書き込み）

   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 3, 1))
   print(f"signals written: {total}")

   - weights をカスタマイズする場合:
     generate_signals(conn, date(2025,3,1), weights={"momentum":0.5, "value":0.2, "volatility":0.15, "liquidity":0.15, "news":0.0})

- ニュース収集（RSS → raw_news、news_symbols 紐付け）

   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 銘柄コードセット（抽出用）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)

- カレンダー更新ジョブ

   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")

- J-Quants クライアント（低レベル）

   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

   token = get_id_token()  # settings.jquants_refresh_token を使用
   records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))

注意点:
- 全ての DB 書き込み関数は冪等性を考慮しています（ON CONFLICT / トランザクション）。
- generate_signals / build_features は target_date 時点のデータのみを参照するため、ルックアヘッドの危険がありません。
- J-Quants API 呼び出しはレート制限・リトライを内部で実装していますが、API クォータ・認証情報は各自管理してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード（発注連携用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - stats.py
  - features.py
  - calendar_management.py
  - audit.py
  - (その他: quality.py 等が想定される)
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
- monitoring/   # __all__ で公開されているが実装は別ファイルにある想定

各モジュールの役割は上記「主な機能一覧」を参照してください。

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上を推奨
- DuckDB ファイルはデフォルトで data/ 以下に保存されます。バックアップ・ローテーションを検討してください。
- 本プロジェクトは実際の発注を行うための機能（execution 層）を含みます。実運用時は十分なテストとリスク管理（paper_trading フラグ、stop_loss など）を行ってください。
- シークレット情報は Git 管理対象にしないこと（.env は .gitignore に追加すること）。
- ETL / calendar_update_job / news collection 等を定期実行する場合はジョブのスケジューラ（cron / Airflow 等）で監視と再試行を設計してください。

---

## 参考（設計ドキュメント参照）
コード内に多数のコメントで設計方針・参照すべき設計資料（DataPlatform.md, StrategyModel.md 等）が記載されています。実装の詳細やパラメータ調整はこれらの設計資料を参照してください。

---

もし README に追加してほしい具体的な実行スクリプト例、CI / テスト手順、または環境変数の .env.example を作成するテンプレートが必要であれば教えてください。