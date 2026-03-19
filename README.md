# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ・監査ログなど、トレーディングシステムのコア機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - レート制限順守、再試行、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等保存（ON CONFLICT / upsert）

- ETL パイプライン
  - 差分更新（バックフィル対応）、市場カレンダー先読み
  - 品質チェックフック（欠損・スパイク等）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（冪等）
  - 監査ログ（signal_events, order_requests, executions など）

- 研究・戦略モジュール
  - ファクター計算（momentum / volatility / value 等）
  - クロスセクション Z スコア正規化ユーティリティ
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）：最終スコア計算、BUY/SELL 判定、SELL 優先ポリシー

- ニュース収集
  - RSS フィード取得、前処理、記事の冪等保存、銘柄コード抽出（日本株 4 桁コード）
  - SSRF 対策、レスポンスサイズ制限、gzip 対応、XML 安全パーシング（defusedxml）

- 設定管理
  - .env ファイル / 環境変数読み込み（プロジェクトルート自動検出）
  - 必須設定は Settings 経由で安全に参照

---

## 機能一覧（モジュール概観）

- kabusys.config
  - 環境設定の読み込み・検証（自動 .env ロード可 / 無効化可）

- kabusys.data
  - jquants_client: API クライアント + 保存ユーティリティ
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・保存・銘柄紐付け
  - calendar_management: 営業日判定 / calendar_update_job
  - stats: zscore_normalize（共通統計ユーティリティ）
  - features: zscore_normalize のエクスポート

- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - feature_engineering.build_features
  - signal_generator.generate_signals

- kabusys.execution / monitoring
  - 発注・監視関連の土台（パッケージ名として存在）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | Y` 構文を使用）
- DuckDB を使用（ローカルファイルに永続化）

1. リポジトリをクローンまたはプロジェクトを取得

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （その他、運用時に必要なライブラリがあれば適宜追加）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマ初期化
   - Python から init_schema を呼ぶことで DB ファイルと全テーブルを作成します（冪等）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```

---

## 基本的な使い方

以下は代表的なワークフローの例です。実行は Python スクリプト / CLI ラッパーから行う想定です。

1. DuckDB の初期化（1 回）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL の実行（市場カレンダー / 株価 / 財務データの差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量の構築（strategy.feature_engineering.build_features）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナル生成（strategy.signal_generator.generate_signals）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   total = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   # known_codes は銘柄抽出に使用する有効銘柄コードセット（省略可）
   results = run_news_collection(conn, known_codes={"7203","6758"})
   print(results)
   ```

6. J-Quants から生データを直接取得して保存（例）
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import get_connection
   from kabusys.config import settings
   from datetime import date

   conn = get_connection(settings.duckdb_path)
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   print(f"saved {saved} rows")
   ```

---

## 設定（環境変数の詳細）

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml のある場所）を基準に `.env` / `.env.local` を読み込みます。
  - 既存の OS 環境変数は保護され、`.env.local` は既存値を上書きできます。
  - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings プロパティ（主要）
  - settings.jquants_refresh_token: J-Quants refresh token（必須）
  - settings.kabu_api_password: kabuステーション API パスワード（必須）
  - settings.kabu_api_base_url: kabu API ベース URL（デフォルトあり）
  - settings.slack_bot_token, settings.slack_channel_id: Slack 通知（必須）
  - settings.duckdb_path: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - settings.sqlite_path: 監視 DB 等（デフォルト: data/monitoring.db）
  - settings.env: KABUSYS_ENV の検証（development / paper_trading / live）
  - settings.log_level: LOG_LEVEL の検証

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルとパッケージ配置（src/ 以下）:

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
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/  (パッケージのみ、発注関連の拡張ポイント)
  - monitoring/ (監視関連の拡張ポイント)

各モジュールは DuckDB 接続を渡す設計（副作用を抑え、テスト容易性を確保）です。

---

## 実運用上の注意点

- トークン・機密情報は環境変数で管理し、ソース管理に含めないでください。
- DuckDB のファイルパスは settings.duckdb_path で指定します。運用環境ではバックアップ戦略を検討してください。
- run_daily_etl や calendar_update_job などは定期ジョブ（cron/CI/etc.）で実行する想定です。エラーハンドリング・監視（Slack 通知等）を組み合わせてください。
- シグナルを実際にブローカーへ送る層（execution）は本 README のコードベースには土台があり、各ブローカー実装に合わせた拡張が必要です。
- ニュース収集では外部 URL を扱うため、ネットワークセキュリティ（プロキシ・ファイアウォール）や RSS ソースの信頼性を考慮してください。

---

## 貢献・拡張ポイント

- execution 層: 証券会社 API との接続／注文の送信・管理
- リスク管理モジュール（ポートフォリオ最適化・資金管理）
- AI スコア算出パイプライン（ai_scores テーブルの自動投入）
- テストカバレッジの拡充（ユニット・統合テスト・モック）

---

README はここまでです。必要であれば、簡単な CLI スクリプト例、より詳細な .env.example、または各モジュールの API 使用例（関数別）を追記します。どの情報を優先して追加しますか？