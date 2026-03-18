# KabuSys

日本株自動売買プラットフォーム向けライブラリ（モジュール群）。データ取得（J-Quants）、DuckDB ベースのデータパイプライン、特徴量計算、研究用ユーティリティ、ニュース収集、品質チェック、監査ログなどを提供します。

## 主な概要
- データレイヤ（Raw / Processed / Feature / Execution）を DuckDB に格納し、冪等的に更新・保存できる ETL パイプラインを備えます。
- J-Quants API クライアント（ページネーション／レート制御／リトライ／トークン自動リフレッシュ）を実装。
- ニュース（RSS）収集・前処理・銘柄抽出・DB保存機能（SSRF 対策・サイズ制限・XML セーフパース）。
- 戦略・リサーチ用のファクター計算（モメンタム・ボラティリティ・バリュー等）、IC 計算、Zスコア正規化。
- データ品質チェック（欠損・スパイク・重複・日付不整合）と監査ログスキーマ（発注〜約定のトレース）。

## 機能一覧
- 環境設定読み込み（.env / .env.local、自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存、冪等）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（カレンダー補正・バックフィル・品質チェック込み）
- DuckDB スキーマ定義・初期化
  - init_schema(db_path) / get_connection(db_path)
  - 監査ログ用: init_audit_schema / init_audit_db
- ニュース収集
  - fetch_rss / save_raw_news / run_news_collection（銘柄抽出と news_symbols 保存）
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats から）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks

## セットアップ手順（開発環境）
前提: Python 3.10 以上（型ヒントに | 演算子を使用しているため）

1. リポジトリをクローン（既にソースがある場合は不要）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   Linux / macOS:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール
   - 本コードベースで想定される依存パッケージ:
     - duckdb
     - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトが pip パッケージ化されている場合は `pip install -e .`）

4. 環境変数を用意
   プロジェクトルートの `.env` / `.env.local` に設定するか、OS 環境変数で指定します。主なキー:
   - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>（必須）
   - KABU_API_PASSWORD = <kabuステーション API パスワード>（必須）
   - KABU_API_BASE_URL = （任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN = <Slack Bot トークン>（必須）
   - SLACK_CHANNEL_ID = <Slack チャンネル ID>（必須）
   - DUCKDB_PATH = data/kabusys.duckdb（任意、デフォルト）
   - SQLITE_PATH = data/monitoring.db（任意、デフォルト）
   - KABUSYS_ENV = development | paper_trading | live（任意、デフォルト: development）
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL（任意、デフォルト: INFO）

   自動環境変数ロード:
   - モジュール初期化時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順にロード（OS 環境変数優先）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

## 使い方（主要な操作例）
以下は Python REPL / スクリプト内での使用例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作成
  # またはインメモリ:
  # conn = init_schema(":memory:")
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 今日を対象に実行
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 5))
  # records は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
  ```

- IC 計算／Zスコア正規化
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, rank
  from kabusys.data.stats import zscore_normalize

  # forward_returns = calc_forward_returns(conn, date(...))
  # factor_records = calc_momentum(...) 等
  # ic = calc_ic(factor_records, forward_returns, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 監査ログスキーマ初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数・設定管理 (.env ロード等)
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（fetch/save）
      - news_collector.py       — RSS 収集・前処理・DB 保存
      - schema.py               — DuckDB スキーマ定義 / init_schema
      - stats.py                — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - features.py             — 特徴量ユーティリティの公開インターフェース
      - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
      - audit.py                — 監査ログ（signal/order/execution）スキーマと初期化
      - etl.py                  — ETLResult 再エクスポート
      - quality.py              — データ品質チェック
    - research/
      - __init__.py
      - feature_exploration.py  — 将来リターン / IC / summary / rank
      - factor_research.py      — momentum/value/volatility 計算
    - strategy/                 — 戦略層（空の __init__ が含まれる）
    - execution/                — 発注実行層（空の __init__ が含まれる）
    - monitoring/               — 監視用モジュール（プレースホルダ）
- pyproject.toml / setup.cfg 等（プロジェクトルートに配置する想定）

## 注意点 / 設計上のポイント
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を原則としています。
- J-Quants API にはレート制御（120 req/min）とリトライ・トークン自動更新が組み込まれています。
- news_collector は SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限を行っています。
- カレンダー情報がない場合のフォールバック: 曜日ベース（土日休）で判定しますが、market_calendar がある場合はそれを優先します。
- 環境変数の必須チェックは Settings クラスで行われ、未設定時は ValueError が発生します。

## トラブルシューティング
- .env が読み込まれない／テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の接続や SQL 実行でエラーが出た場合は、スキーマ初期化（init_schema）を実行してテーブルが作成されているか確認してください。
- J-Quants の 401 エラーが出る場合、config の JQUANTS_REFRESH_TOKEN が正しいか、ネットワークアクセスが可能か確認してください。

---

必要であれば、README にサンプル .env.example、より詳しい API ドキュメント（各関数の引数/戻り値）や CI / デプロイ手順を追記します。どの情報を拡張したいか教えてください。