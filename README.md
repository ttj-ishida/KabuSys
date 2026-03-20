KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買プラットフォーム向けライブラリで、データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査／実行レイヤまでを想定したモジュール群を含みます。  
このリポジトリは主に以下の目的を持ちます。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存する ETL
- 研究用ファクター計算（momentum / volatility / value 等）
- クロスセクション正規化・特徴量（features）作成
- features と AI スコアを統合した売買シグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB スキーマ定義・初期化、監査ログ定義

主な機能
--------
- 環境変数ベースの設定管理（自動 .env ロード機能、必要変数チェック）
- J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ対応）
- DuckDB スキーマ定義と init_schema による初期化（冪等）
- ETL パイプライン（差分取得、バックフィル、品質チェック統合）
- ファクター計算モジュール（モメンタム／ボラティリティ／バリュー）
- 特徴量正規化（Z スコア）と features テーブルへの保存
- シグナル生成（コンポーネントスコア計算、Bear レジーム抑制、BUY/SELL 書き込み）
- ニュース収集（RSS → raw_news、記事ID 正規化、銘柄抽出）
- 監査（signal_events / order_requests / executions 等・UTC タイムスタンプ）

必須・推奨環境
--------------
- Python >= 3.10（typing の | 記法、TypedDict 等を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- J-Quants API アクセスのためのリフレッシュトークン等（環境変数参照）

セットアップ手順
----------------

1. リポジトリをクローン / 取得

   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（config モジュールの自動ロード）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携を行う場合、必須）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

   オプション（デフォルトあり）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 .env（プロジェクトルート）:
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

使い方（簡単な例）
-----------------

以下は主要な API を使った最小動作例です。実際の運用ではログ設定やエラーハンドリングを適切に行ってください。

1. DuckDB スキーマの初期化

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成されテーブルが作られる

2. 日次 ETL（J-Quants からデータ取得 → 保存 → 品質チェック）

   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定しなければ本日が対象
   print(result.to_dict())

3. 特徴量作成（features のビルド）

   from datetime import date
   from kabusys.strategy import build_features

   n = build_features(conn, date(2024, 1, 31))
   print(f"build_features: {n} 銘柄処理")

4. シグナル生成

   from datetime import date
   from kabusys.strategy import generate_signals

   num_signals = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
   print(f"generate_signals: {num_signals} シグナル生成（BUY+SELL）")

5. ニュース収集ジョブ（RSS）

   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット（抽出に使用）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)

主要モジュールと API（抜粋）
----------------------------
- kabusys.config
  - settings: 環境変数をラップする Settings インスタンス（settings.jquants_refresh_token 等）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       -- 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py             -- J-Quants API クライアント + 保存ロジック
  - news_collector.py             -- RSS 取得・保存・銘柄抽出
  - pipeline.py                   -- ETL パイプライン
  - schema.py                     -- DuckDB スキーマ定義・初期化
  - stats.py                      -- Z スコア正規化など統計ユーティリティ
  - features.py                   -- zscore_normalize の再エクスポート
  - calendar_management.py        -- 市場カレンダー管理
  - audit.py                      -- 監査ログ DDL（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py            -- momentum / volatility / value の計算
  - feature_exploration.py        -- 将来リターン・IC・サマリー等
- strategy/
  - __init__.py
  - feature_engineering.py        -- 特徴量生成と features テーブル挿入
  - signal_generator.py           -- final_score 計算と signals 挿入
- execution/                       -- 発注・約定管理（プレースホルダー／拡張想定）
- monitoring/                      -- 監視・アラート関連（プレースホルダー）

設計上のポイント（短記）
------------------------
- 冪等性: DB 保存は ON CONFLICT / UPSERT を用いて冪等に実装
- Look-ahead バイアス防止: target_date 時点のデータのみを参照する方針を各モジュールで採用
- エラーハンドリング: ETL や各ジョブは部分的失敗を許容し、呼び出し元が最終判断する設計
- セキュリティ: RSS 取得で SSRF 対策、XML パースで defusedxml を使用、J-Quants でレートリミット・リトライ制御

運用上の注意
--------------
- 本コードは発注レイヤ（実際のブローカ接続）と結びつける前に十分なテストが必要です。paper_trading モードでの検証を推奨します（KABUSYS_ENV=paper_trading）。
- 環境変数や API トークンは安全に管理してください（.env をバージョン管理しない、シークレット管理を利用する等）。
- DuckDB ファイルへのアクセスは排他制御やバックアップ方法を検討してください（複数プロセスからの同時書き込み等）。

貢献・拡張
-----------
- execution/ や monitoring/ 以下にブローカー別コネクタ、オーダー送信・状態同期機能を追加できます。
- AI スコア連携や Slack 通知などは既存の ai_scores / slack 用設定を利用して統合してください。

補足
----
- この README はソースコードの内容を元にした概要です。各関数の詳細な仕様や戻り値はモジュール内 docstring を参照してください。疑問点や拡張要望があれば issue を立ててください。

--- 
以上。必要なら「セットアップ用の requirements.txt」や「具体的な運用ワークフロー（cron / Airflow 例）」のテンプレートも作成できます。どの情報を追加したいか教えてください。