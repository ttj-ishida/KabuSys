# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からのマーケットデータ取得、DuckDB を使ったデータ基盤、ファクター計算、特徴量生成、シグナル生成、RSS ニュース収集、マーケットカレンダー管理、発注／監査用スキーマなどを含むモジュール群を提供します。

主な想定用途：研究環境でのファクター設計・評価、日次ETL の自動化、本番／ペーパー取引におけるシグナル生成のバックエンド実装、ニュース収集と銘柄紐付けなど。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック
  - 実行環境（development / paper_trading / live）判定

- データ取得 / 保存（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ基盤（DuckDB スキーマ）
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - スキーマ初期化ユーティリティ（init_schema）

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得 + backfill）
  - 日次 ETL（calendar / prices / financials）と品質チェック統合

- 研究用ファクター・特徴量
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials）
  - Z スコア正規化ユーティリティ

- 特徴量生成（features）
  - research 側の生ファクターを正規化・合成して features テーブルへ保存

- シグナル生成
  - features と ai_scores を統合して最終スコア算出
  - BUY/SELL シグナルの生成（ベア相場抑制、エグジット判定含む）
  - signals テーブルへの冪等書き込み

- ニュース収集
  - RSS フィードの取得と前処理（URL 除去・正規化）
  - 記事 ID は正規化 URL の SHA-256 先頭 32 文字
  - SSRF / XML Bomb / 大きすぎるレスポンスなどに対する安全対策
  - raw_news / news_symbols への冪等保存

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ
  - カレンダーの夜間更新ジョブ（calendar_update_job）

- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティを保持するテーブル群

---

## セットアップ手順（クイックスタート）

前提：
- Python 3.10+ を推奨（型記法に | を使用）
- duckdb、defusedxml 等の依存パッケージが必要

1. リポジトリをクローン（例）
   git clone https://your-repo/kabusys.git
   cd kabusys

2. Python 仮想環境の作成と有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール（プロジェクトに requirements.txt / pyproject があればそれを使用）
   pip install duckdb defusedxml

   ※プロジェクトに pyproject.toml があれば
   pip install -e .

4. 環境変数の設定
   プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（CWD に依存せず package 内から探索）。
   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意 / デフォルト:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
   - LOG_LEVEL (DEBUG / INFO / …、デフォルト: INFO)

   自動 .env 読み込みを無効化するには:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でメモリ DB 可

---

## 使い方（主要ワークフローの例）

以下は典型的なバッチワークフロー例（日次処理）。

1) DB 初期化（1回）
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（市場カレンダー・株価・財務の差分取得・保存・品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト

   result.to_dict() で詳細を確認できます。

3) 特徴量作成（features テーブルに書き込み）
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, target_date=date.today())  # 対象日分の features を再生成

4) シグナル生成・保存
   from kabusys.strategy import generate_signals
   from datetime import date
   total_signals = generate_signals(conn, target_date=date.today())
   # generate_signals は signals テーブルへ日付単位の置換で書き込みます

5) ニュース収集（RSS）
   from kabusys.data.news_collector import run_news_collection
   results = run_news_collection(conn, known_codes={"7203","6758"})  # known_codes を指定すると銘柄紐付けも行う

6) カレンダー夜間更新ジョブ
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)

7) J-Quants から直接データ取得・保存（個別）
   from kabusys.data import jquants_client as jq
   records = jq.fetch_daily_quotes(date_from=..., date_to=...)
   jq.save_daily_quotes(conn, records)

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

注意: Settings クラスは必須変数が未設定の場合 ValueError を送出します。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env 自動読み込み、環境変数要件チェック、settings オブジェクトを提供

- kabusys.data.schema
  - DuckDB の DDL を定義し init_schema() でテーブルを全作成

- kabusys.data.jquants_client
  - J-Quants API クライアント（レートリミット、リトライ、トークン管理、保存ユーティリティ）

- kabusys.data.pipeline
  - 差分 ETL / run_daily_etl などの上位 API

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary など研究用ユーティリティ

- kabusys.strategy.feature_engineering
  - build_features: 生ファクターを正規化し features テーブルへ保存

- kabusys.strategy.signal_generator
  - generate_signals: features / ai_scores / positions を参照して BUY/SELL を決定・保存

- kabusys.data.news_collector
  - RSS フェッチ、前処理、raw_news と news_symbols への保存

- kabusys.data.calendar_management
  - market_calendar の管理、営業日判定ユーティリティ

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル/モジュール）

- __init__.py
- config.py — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py — RSS ニュースの収集と保存
  - schema.py — DuckDB スキーマ定義・初期化
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理
  - features.py — data 層の公開インターフェース（zscore 再エクスポート）
  - audit.py — 監査ログ DDL（signal_events, order_requests, executions 等）
  - その他（raw_executions などのDDL関連を含む）
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — 将来リターン計算、IC、summary
- strategy/
  - __init__.py
  - feature_engineering.py — build_features
  - signal_generator.py — generate_signals
- execution/ — 発注に関する実装（空の __init__.py がある）

各ファイルの詳細はソースの docstring に設計方針・処理フローが記載されています。

---

## 実運用上の注意点

- データ取得 API のレート制限・リトライロジックが組み込まれていますが、実行頻度は運用ポリシーに合わせて調整してください。
- DuckDB スキーマは冪等で作成されますが、運用ルール（FK の扱いなど）についてコード内コメントを参照し、削除やマイグレーションは慎重に行ってください。
- RSS 収集は外部の公開フィードを取得します。SSRF や XML 攻撃への対策を実装していますが、追加フィードを登録する際は信頼できるソースを選んでください。
- KABUSYS_ENV を "live" に設定すると is_live フラグが True になり、本番用のガードや外部発注の有効化などで分岐を入れることが想定されています。テスト時は "development" や "paper_trading" を使ってください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。ユニットテストなどでこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

README はここまでです。必要であれば以下の追加を作成します：
- .env.example テンプレート
- 開発者向けセットアップ（pre-commit, linters）
- CLI スクリプト / systemd / cron ジョブ例
- よくあるエラーとトラブルシューティング

どれを追加希望か教えてください。