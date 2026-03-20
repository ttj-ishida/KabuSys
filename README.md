KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買用ライブラリ群です。  
データ取得（J-Quants）→ DuckDB に保存 → 研究用ファクター計算 → 特徴量作成 → シグナル生成、さらにニュース収集・監査ログ等を含む設計になっています。

主な設計方針
- ルックアヘッドバイアス回避（各処理は target_date 時点のデータのみを使用）
- 冪等性（API保存は ON CONFLICT などで上書き可能）
- テスト性・注入可能性（id_token などを引数で注入可能）
- 外部依存を最小化（pandas 等に依存しない実装を多数採用）

機能一覧
- データ取得（J-Quants API）
  - 株価（OHLCV）、財務データ、JPX カレンダー
  - レート制限・自動トークンリフレッシュ・リトライ（指数バックオフ）
- DuckDB スキーマ管理・初期化（init_schema）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量生成（Zスコア正規化・ユニバースフィルタ適用）
- シグナル生成（最終スコア計算、BUY/SELL 判定、冪等で signals テーブルへ保存）
- ニュース収集（RSS → raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 汎用統計ユーティリティ（zscore_normalize 等）

セットアップ手順（開発者向け）
1. Python バージョン
   - Python 3.10+ を推奨（typing の | 演算子等を使用）

2. リポジトリをクローン
   - git clone <repo>

3. 必要パッケージをインストール
   - requirements.txt がある想定：
     - pip install -r requirements.txt
   - 最低依存例：
     - pip install duckdb defusedxml

4. 環境変数設定（.env）
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必要な環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN=（必須） J-Quants の refresh token
     - KABU_API_PASSWORD=（必須） kabuステーション API パスワード
     - KABU_API_BASE_URL=（任意、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN=（必須） Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID=（必須） Slack チャネル ID
     - DUCKDB_PATH=（任意、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH=（任意、デフォルト: data/monitoring.db）
     - KABUSYS_ENV=（任意、development|paper_trading|live、デフォルト: development）
     - LOG_LEVEL=（任意、DEBUG|INFO|WARNING|ERROR|CRITICAL）

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)
   - :memory: を渡すとインメモリ DB を使えます（テスト用）。

使い方（主要な操作例）
- 日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量ビルド（features テーブルへの保存）
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features
  from datetime import date
  conn = get_connection(settings.duckdb_path)
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {n}")

- シグナル生成（signals テーブルへの保存）
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals
  from datetime import date
  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals written: {total}")

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings
  conn = get_connection(settings.duckdb_path)
  # known_codes: 既知銘柄コードセット（抽出精度向上のため渡す）
  known_codes = {"7203", "6758", ...}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- J-Quants の直接利用（データ取得）
  from kabusys.data import jquants_client as jq
  # トークンは settings.jquants_refresh_token に基づき自動で取得されます
  quotes = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, quotes)

注意点
- 自動環境読み込みは .env / .env.local をプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に探索します。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑止できます（テスト用）。
- 各 ETL / 保存処理は冪等化されているため繰り返し実行しても安全な設計ですが、外部 API の制限やレート制御に注意してください。
- DuckDB の型制約やチェック制約により、データ不整合は例外となることがあります。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得/保存）
    - news_collector.py         -- RSS ニュース収集・前処理・保存
    - schema.py                 -- DuckDB スキーマ定義・初期化
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - features.py               -- データ統計ユーティリティの公開（zscore）
    - calendar_management.py    -- マーケットカレンダー/営業日ユーティリティ
    - audit.py                  -- 監査ログ用 DDL / 初期化補助
    - stats.py                  -- zscore_normalize 等の統計ユーティリティ
    - (その他: quality モジュール 等を想定)
  - research/
    - __init__.py
    - factor_research.py        -- Momentum / Volatility / Value の計算
    - feature_exploration.py    -- IC / forward returns / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py    -- features テーブル作成（正規化・フィルタ）
    - signal_generator.py       -- final_score 計算・BUY/SELL 判定
  - execution/
    - __init__.py               -- 発注/実行層（実装は別途）
  - monitoring/                 -- 監視用コード群（ファイルはここに配置想定）

付録 — よく使う API
- init_schema(db_path) -> DuckDB 接続（スキーマ作成）
- get_connection(db_path) -> DuckDB 接続（既存 DB に接続）
- run_daily_etl(conn, target_date=None, ...) -> ETLResult
- build_features(conn, target_date) -> upsert 件数
- generate_signals(conn, target_date, threshold=..., weights=None) -> シグナル数
- run_news_collection(conn, sources=None, known_codes=None) -> 保存数辞書

お問い合わせ / 開発メモ
- 設定や .env のサンプルは .env.example を参考にしてください（プロジェクトルートに作成）。
- ログ出力レベルは LOG_LEVEL 環境変数で制御できます。
- 本 README はソース内の docstring / コメントに基づいて作成しています。詳細な設計仕様（StrategyModel.md, DataPlatform.md, DataSchema.md 等）が別途あれば合わせて参照してください。

以上。必要ならインストール用の requirements.txt、.env.example のテンプレート、または具体的な運用スクリプト（cron / systemd / Airflow 連携例）も作成します。どれが必要か指示ください。