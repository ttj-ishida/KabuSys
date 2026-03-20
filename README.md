# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB を中心としたデータレイヤー、J-Quants からのデータ取得クライアント、ファクター計算・特徴量生成、シグナル生成、ニュース収集、カレンダー管理、ETL パイプラインなどを備えたモジュール群を提供します。

---

## プロジェクト概要

KabuSys は次の目的で設計されています。

- J-Quants API からの市場データ・財務データ・カレンダー取得を行い、DuckDB に冪等に保存する（差分 ETL）。
- データを加工して特徴量（features）を作成し、戦略のシグナルを生成する。
- RSS 等からニュースを収集して raw_news に保存し、銘柄との紐付けを行う。
- JPX の市場カレンダーを管理して営業日判定・探索を提供する。
- 監査ログ（audit）を保持してシグナル→発注→約定のトレーサビリティを実現する。

設計上の特徴：
- 冪等性（DB 保存は ON CONFLICT で上書き / スキップ）
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみを使用）
- 外部ライブラリへの依存を最小化（ただし DuckDB, defusedxml など必須）
- ネットワーク周りに堅牢なリトライ・レートリミット・SSRF 対策を持つ

---

## 主な機能一覧

- 環境設定の読み込み・管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可能）
  - 必須環境変数（JQUANTS_REFRESH_TOKEN 等）の取得と検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存ユーティリティ（save_*）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェック呼び出し
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - init_schema() で DB を初期化
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事ID生成（URL 正規化→SHA-256）、raw_news 保存
  - SSRF 対策、gzip 制限、XML パース保護（defusedxml）
  - 銘柄コード抽出と news_symbols への紐付け
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間差分更新
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 戦略モジュール（kabusys.strategy）
  - build_features: 生ファクターを正規化・統合して features テーブルへ保存
  - generate_signals: features と ai_scores を統合し BUY/SELL シグナルを生成
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義

---

## セットアップ手順

前提
- Python 3.9+（型ヒントにUnion演算子や型注釈が使われています）
- DuckDB が必要（Python パッケージ duckdb）
- defusedxml（RSS パース用）
- そのほか標準ライブラリのみで動作する部分が多いですが、実運用では追加パッケージや DB ドライバが必要になる場合があります。

1. リポジトリをクローンして開発環境を準備
   - 例（プロジェクトルートが git リポジトリであることを想定）:
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb defusedxml
     # （パッケージを editable install する場合）
     pip install -e .
     ```

2. 環境変数を設定
   - 必須（実行に必要な値）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト `INFO`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`
   - .env の自動読み込み
     - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動でロードします。
     - OS 環境変数 > .env.local > .env の優先順位
     - 自動ロードを無効化したい場合:
       ```
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

3. DuckDB スキーマ初期化
   - Python REPL などで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)
     ```
   - またはインメモリ DB でテスト:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（基本的なワークフロー）

以下は典型的なデータ取得 → 特徴量生成 → シグナル生成の流れです。

1. DuckDB 接続とスキーマ初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL（市場カレンダー・株価・財務データの差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルへの保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   target = date.today()  # 通常は ETL と同じ trading_day を使う
   count = build_features(conn, target)
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ保存）
   ```python
   from kabusys.strategy import generate_signals

   num_signals = generate_signals(conn, target, threshold=0.6)
   print(f"signals written: {num_signals}")
   ```

5. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection

   # known_codes は extract_stock_codes に使う有効銘柄コードの集合（例: prices_daily から取得）
   known_codes = {"7203", "6758", ...}
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: 新規保存件数}
   ```

6. カレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

補足:
- jquants_client では get_id_token() がトークンの自動取得/リフレッシュを行います。rate limit（120 req/min）やリトライが組み込まれています。
- ニュース収集は SSRF・Gzip Bomb・XML Bomb 等対策を実装しています。
- run_daily_etl の戻り値 ETLResult は品質チェックの結果やエラー情報も保持します。

---

## よく使う API（抜粋）

- 環境設定:
  - kabusys.config.settings
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.slack_bot_token / slack_channel_id
    - settings.duckdb_path / sqlite_path
    - settings.env / settings.is_live / is_paper / is_dev

- データ層:
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl

- ニュース:
  - kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection

- カレンダー:
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day
  - kabusys.data.calendar_management.calendar_update_job

- 研究・戦略:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.strategy.build_features
  - kabusys.strategy.generate_signals

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/
  - kabusys/
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
      - pipeline.py
      - (その他 data 関連モジュール)
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
    - monitoring/  (パッケージは __all__ に含まれる想定だが、実装ファイルは省略)
- pyproject.toml / setup.cfg / README.md（本ファイル）

この README に記載のファイルは実装ソースから主要機能を抽出したものです。各モジュールの詳細な API はソースコードの docstring を参照してください。

---

## 注意点・運用上の留意事項

- 環境変数はセキュリティに注意して管理してください（トークンやパスワード）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップ・権限設定を検討してください。
- J-Quants API の利用規約・レート制限に従ってください。ライブラリ側でも制御していますが、運用側でも注意が必要です。
- 本ライブラリは戦略ロジックの骨組みを提供します。実運用環境での出力（発注など）を行う前に必ずシミュレーション・ペーパートレードで検証してください。

---

問題点の報告・機能追加の提案は Issue を立ててください。README に載せるべき追加の使用例や運用手順があればお知らせください。