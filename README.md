KabuSys
=======

KabuSys は日本株向けのデータプラットフォーム兼自動売買（ストラテジー）パイプラインです。
DuckDB をデータ層に使い、J-Quants API から市場データ／財務データ／カレンダーを取得して保存し、
研究（research）→特徴量（features）→シグナル生成（signals）→発注（execution）の流れをサポートします。

本 README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
- 目的: J-Quants 等から収集した市場データを ETL して DuckDB に蓄積し、特徴量計算・シグナル生成までを行う自動売買基盤のコアライブラリ。
- 設計の特徴:
  - DuckDB ベースのローカルデータベース（ファイル）で軽量にデータ管理
  - ETL は差分取得・バックフィル対応、品質チェックフローあり
  - 研究用モジュールと運用（execution）ロジックを分離
  - 冪等性（ON CONFLICT / idempotent save）やルックアヘッドバイアス対策を考慮した実装
  - 外部依存を最小化（標準ライブラリ + 必要最小限の外部モジュール）

主な機能一覧
-------------
- データ取得 / 保存（data/jquants_client.py）
  - J-Quants API クライアント（トークンリフレッシュ・リトライ・レート制御）
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン（data/pipeline.py）
  - 日次 ETL（run_daily_etl）: カレンダー→日足→財務 → 品質チェック
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- スキーマ管理（data/schema.py）
  - DuckDB のテーブル定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層の DDL を定義
- ニュース収集（data/news_collector.py）
  - RSS 取得、前処理、記事の冪等保存、銘柄コード抽出・紐付け
  - SSRF 対策、gzip 上限、XML パースの安全化（defusedxml）
- 統計 / ユーティリティ（data/stats.py）
  - Z スコア正規化等の汎用関数
- 研究モジュール（research/）
  - factor_research: Momentum/Volatility/Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量作成（strategy/feature_engineering.py）
  - research の生ファクターを統合・正規化して features テーブルへ保存
  - ユニバースフィルタ（最低株価、最低売買代金）や Z スコアクリップを実行
- シグナル生成（strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL シグナルの生成、signals テーブルへの保存
- 設定管理（config.py）
  - .env / .env.local / OS 環境変数を自動ロード
  - 必須項目のラッパー（settings.*）

セットアップ手順
----------------

前提:
- Python 3.9+（typing の一部表記に依存）
- DuckDB を使用します。必要に応じてシステムに合わせてインストールしてください。

1. リポジトリをチェックアウト
   - ソースルートに移動してください（README と同階層に pyproject.toml / .git がある構成を想定）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - 必要最小限:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクト固有の extras/requirements があれば pyproject.toml / requirements.txt を参照してインストールしてください）

4. 環境変数設定 (.env)
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN  — J-Quants の refresh token（必須）
     - KABU_API_PASSWORD      — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID       — Slack チャネル ID（必須）
   - オプション（デフォルトが使えます）:
     - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV            — env（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL              — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   - 例 .env（参考）:
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C...
     DUCKDB_PATH=data/kabusys.duckdb

5. データベース初期化
   - Python REPL またはスクリプトで init_schema を呼び出して DuckDB スキーマを作成します。
     例:
       from kabusys.data.schema import init_schema, settings
       conn = init_schema(settings.duckdb_path)

基本的な使い方（例）
-------------------

以下は Python スクリプト / REPL からの利用例です。実運用では cron / systemd / Airflow 等で定期実行します。

1) DuckDB の初期化
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

2) 日次 ETL を実行（市場カレンダー・日足・財務・品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

3) 特徴量の構築（strategy 層）
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, target_date=date.today())
   print(f"{count} 件の features を保存しました")

4) シグナル生成
   from kabusys.strategy import generate_signals
   n = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"{n} 件のシグナルを signals テーブルに書き込みました")

5) ニュース収集ジョブ実行（RSS → raw_news）
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出用の有効コードセット（例: all codes from prices_daily）
   known_codes = set(row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall())
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)

6) カレンダー更新ジョブ（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"saved calendar rows: {saved}")

設定周りの補足
--------------
- .env の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml の存在）を基準に .env と .env.local を自動で読み込みます。
  - 読み込み順は OS 環境変数 > .env.local > .env です。
  - テストや他用途で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

- Settings API:
  - from kabusys.config import settings として settings.jquants_refresh_token 等でアクセスできます。
  - 必須環境変数が未設定の場合は ValueError が発生します。

運用上の推奨ジョブ（例）
---------------------
- 毎晩（夜間）:
  - calendar_update_job（市場カレンダーの先読み）
  - run_daily_etl（当日分の ETL。実行タイミングは市場営業後の適切な時間に）
- 日中 / 営業開始前:
  - build_features（直近データで特徴量更新）
  - generate_signals（売買シグナル生成）
- 頻度:
  - ニュース収集は数分〜数時間ごとに実行（ソース数とレートに応じて）
  - ETL は日次が基本。リアルタイム取引を行う場合は intraday の対応が別途必要。

ディレクトリ構成
-----------------
（主要ファイル・モジュールの一覧）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得＋保存）
    - news_collector.py     — RSS ニュース収集と保存
    - schema.py             — DuckDB スキーマ定義と初期化
    - stats.py              — 統計ユーティリティ（zscore_normalize など）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — data 層の特徴量ユーティリティ（エクスポート）
    - calendar_management.py— カレンダー管理 / 夜間バッチ
    - audit.py              — 監査ログ（signal/order/execution の追跡）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility 計算
    - feature_exploration.py— IC/forward_returns/summary
  - strategy/
    - __init__.py
    - feature_engineering.py— features を構築して features テーブルへ書き込む
    - signal_generator.py   — features + ai_scores → signals
  - execution/              — （発注・ブローカー連携レイヤ。実装ファイルがここに入る想定）
  - monitoring/             — （監視・アラート用モジュール。実装ファイルがここに入る想定）

注意事項 / 開発メモ
-------------------
- 外部 API（J-Quants）へのリクエストはレート制御やリトライ・自動トークンリフレッシュを行いますが、実利用時は API 利用規約・レート制限に従ってください。
- DuckDB のバージョン差異により一部 DDL / 外部キーや ON CONFLICT の挙動が変わる可能性があります（コード内に互換処理の注釈あり）。
- 本リポジトリには運用を想定した堅牢なエラーハンドリング・冪等性・安全対策（SSRF・XML パース安全化等）が多数含まれます。実環境へ導入する際は監査ログ・監視・リスク管理の運用ルールを整備してください。

ライセンス・貢献
----------------
- この README 上はライセンス表記を含めていません。リポジトリの LICENSE ファイルを確認してください。
- バグ修正・機能改善は Pull Request を歓迎します。改修にあたってはテスト追加と動作確認をお願いします。

問い合わせ
----------
- 実装詳細や運用上の質問があれば、このリポジトリの Issue を立ててください。

以上。必要であれば README に含めるサンプルコマンド（systemd / cron 例）や CI/CD / Docker 化手順、開発フローのテンプレートを追加します。どの情報を優先して追記しましょうか？