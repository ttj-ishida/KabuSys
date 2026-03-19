# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDBスキーマ／監査ログなど、戦略運用に必要な基盤処理を提供します。

---

## 主要な特徴（概要）

- J-Quants API クライアント（レートリミット、リトライ、トークン自動更新、ページネーション対応）
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution 層）と初期化ユーティリティ
- ETL パイプライン（日次差分更新・バックフィル・品質チェック）  
- 研究用ファクター計算（Momentum / Value / Volatility）および特徴量正規化
- 戦略用シグナル生成（複数ファクターの重み付け統合、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS → 前処理 → DB保存、銘柄抽出、SSRF・ファイル攻撃対策）
- 監査ログ／トレーサビリティ用テーブル群
- 設定は環境変数（.env/.env.local）で管理。自動ロード機構あり

---

## 機能一覧（モジュール／主な関数）

- kabusys.config
  - 環境変数の自動ロード（プロジェクトルートの .env/.env.local を探索）
  - Settings（J-Quantsトークン、kabu API パスワード、Slack、DBパス等）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット、リトライ、トークン更新等
- kabusys.data.schema
  - init_schema(db_path) — DuckDB スキーマ作成（冪等）
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl — 日次 ETL の統合エントリポイント（品質チェック含む）
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
  - RSS の正規化、SSRF対策、トラッキングパラメータ削除
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.stats
  - zscore_normalize — クロスセクション Z スコア正規化
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features(conn, target_date) — features テーブルの作成（ユニバースフィルタ、Z スコアクリップ等）
  - generate_signals(conn, target_date, threshold, weights) — signals テーブルへ書き込み

---

## 動作環境 / 依存関係

- Python 3.10+
  - （ソースで型注釈に `Path | None` 等の構文を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- その他: 標準ライブラリの urllib 等を使用

例（開発環境へのインストール）:
- 仮想環境を作る（推奨）:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール:
  - pip install duckdb defusedxml
- パッケージとしてインストール（プロジェクトに setup/pyproject があれば）:
  - pip install -e .

（プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください）

---

## 環境変数（主な必須項目）

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` を自動ロードします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|...（デフォルト: INFO）

注意: Settings のプロパティは未設定時に ValueError を投げます（必須項目）。

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
   - git clone <repo-url>
2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （他に必要なパッケージがあれば pyproject.toml / requirements.txt を参照）
4. 環境変数を用意
   - プロジェクトルートに `.env` を作成（例 `.env.example` を参考に）
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.config import settings
     - from kabusys.data.schema import init_schema
     - conn = init_schema(settings.duckdb_path)
   - これで DB とテーブルが作成されます

---

## 使い方（主要な例）

以下は最小限の運用フローの例です（Python スクリプト／REPL にて実行）。

1) スキーマ初期化（初回）
- 実行例:
  - from kabusys.config import settings
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)

2) 日次 ETL（データ取得 → 保存 → 品質チェック）
- 実行例:
  - from datetime import date
  - from kabusys.data.schema import init_schema
  - from kabusys.data.pipeline import run_daily_etl
  - conn = init_schema(settings.duckdb_path)
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

3) 特徴量構築（strategy.feature_engineering）
- 実行例:
  - from datetime import date
  - from kabusys.data.schema import get_connection
  - from kabusys.strategy import build_features
  - conn = get_connection(settings.duckdb_path)
  - n = build_features(conn, target_date=date.today())
  - print(f"features upserted: {n}")

4) シグナル生成（strategy.signal_generator）
- 実行例:
  - from datetime import date
  - from kabusys.data.schema import get_connection
  - from kabusys.strategy import generate_signals
  - conn = get_connection(settings.duckdb_path)
  - total_signals = generate_signals(conn, target_date=date.today())
  - print(f"signals written: {total_signals}")

5) ニュース収集ジョブ
- 実行例:
  - from kabusys.data.news_collector import run_news_collection
  - from kabusys.data.schema import get_connection
  - conn = get_connection(settings.duckdb_path)
  - known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  - res = run_news_collection(conn, known_codes=known_codes)
  - print(res)

注意点:
- 各関数は DuckDB 接続を受け取る設計なので、コネクションを渡して利用してください。
- run_daily_etl などは内部で例外をキャッチし結果に errors を集約します。戻り値の ETLResult で状態を確認してください。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置）
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
      - audit の DDL 等（監査関連）
      - quality.py (参照あり／品質チェック実装が別途存在)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/  (発注 / execution 層はパッケージ化済み)
    - monitoring/ (監視用のコードがある想定)
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトルートにある場合あり）
- .env, .env.local（プロジェクトルートに配置して環境変数を管理）

---

## 設計上の注意・補足

- 冪等性: 多くの保存処理は ON CONFLICT / INSERT … DO UPDATE や RETURNING を使って冪等に設計されています。
- ルックアヘッドバイアス対策: 特徴量・シグナル生成は target_date 時点で入手可能な情報のみを利用する方針で作られています。
- セキュリティ: RSS の取得には SSRF 対策、XML パーサは defusedxml を採用、レスポンスサイズチェックなどのメモリDoS対策を実装しています。
- エラーハンドリング: ETL などは個別ステップを独立して失敗を許容する設計（全体を止めない）になっています。致命的な失敗はログ・戻り値で通知してください。

---

## 貢献 / 開発時メモ

- テストの実行や CI 設定はリポジトリに準拠してください（ここには含まれていません）。
- 環境変数周りは自動ロード機能が働くため、ユニットテストや一時的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動ロードをスキップします。
- DuckDB のスキーマは init_schema() が冪等に作成するので初回実行時のみ呼ぶことを推奨します。既存 DB を更新する場合はマイグレーション方針を検討してください。

---

必要であれば、README に含める具体的な .env.example、より詳しい API 使用例、運用フロー（cron / Airflow / k8s CronJob 例）やよくあるトラブルシューティングを追記できます。どの情報を優先して追加しますか？