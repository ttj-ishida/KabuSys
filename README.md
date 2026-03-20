KabuSys
=======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買（データ収集・特徴量生成・シグナル生成・発注管理）を目的とした Python コードベースです。  
主な設計方針は次のとおりです。

- 研究（research）と実運用（execution）を分離し、ルックアヘッドバイアスを防ぐ設計
- DuckDB をデータレイクとして利用し、スキーマは冪等に作成
- J-Quants API や RSS からデータを取得し、ETL パイプラインで加工・保存
- 特徴量の正規化・合成 → 戦略によるスコア計算 → シグナル生成（BUY/SELL）までを分離して実装
- 外部依存は最小限（duckdb, defusedxml 等）

機能一覧
--------
- 環境変数/設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数の検証
- データレイヤ（kabusys.data）
  - J-Quants API クライアント（取得・リトライ・レート制限・トークン自動更新）
  - ETL パイプライン（日次差分取得 / 財務データ / 市場カレンダー）
  - RSS ニュース収集・正規化・DB保存（SSRF 対策，XML セキュリティ対策）
  - DuckDB スキーマ定義・初期化（冪等）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - 監査ログ（signal/order/execution のトレーサビリティ）
  - 汎用統計ユーティリティ（Z スコア正規化 等）
- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算 / IC（スピアマン） / 統計サマリー
- 戦略（kabusys.strategy）
  - 特徴量作成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
- 実行（kabusys.execution）および監視（kabusys.monitoring）の雛形

前提条件（最低限）
-----------------
- Python 3.10+
- duckdb（DuckDB Python パッケージ）
- defusedxml（RSS/XML の安全パース）
- （標準ライブラリ以外の追加があれば requirements.txt を参照してください）

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   プロジェクトルートに .env または .env.local を置くと自動ロードされます（kabusys.config が .git または pyproject.toml を基準にプロジェクトルートを検出）。

   必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API のパスワード（発注層利用時）
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

   オプション（デフォルト値あり）
   - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            — SQLite（監視等）パス（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを無効化

   例 (.env)
   - JQUANTS_REFRESH_TOKEN=xxxx
   - KABU_API_PASSWORD=secret
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - KABUSYS_ENV=development

初期化（DuckDB スキーマ作成）
----------------------------
Python REPL またはスクリプトから DuckDB スキーマを初期化します。デフォルトの DB パスは settings.duckdb_path です。

例:
- from kabusys.data.schema import init_schema
- from kabusys.config import settings
- conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成して全テーブルを作る

使い方（主要なワークフロー）
--------------------------

1) 日次 ETL（データ取得 → 保存 → 品質チェック）
- from kabusys.data.schema import init_schema
- from kabusys.data.pipeline import run_daily_etl
- conn = init_schema("data/kabusys.duckdb")
- result = run_daily_etl(conn)  # target_date を指定可能
- print(result.to_dict())

2) 特徴量生成（features テーブル作成）
- from kabusys.strategy import build_features
- build_count = build_features(conn, target_date=<date オブジェクト>)

3) シグナル生成（signals テーブル作成）
- from kabusys.strategy import generate_signals
- n_signals = generate_signals(conn, target_date=<date オブジェクト>, threshold=0.6, weights=None)

4) ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
- from kabusys.data.news_collector import run_news_collection
- results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  - sources を省略すると内蔵 DEFAULT_RSS_SOURCES を使う
  - known_codes を渡すと抽出した銘柄コードを news_symbols に保存

5) カレンダー更新ジョブ（夜間バッチ想定）
- from kabusys.data.calendar_management import calendar_update_job
- saved = calendar_update_job(conn)

開発向けの補足
- 設定の自動読み込みは kabusys.config 内で行われます。テストや特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- J-Quants API 呼び出しは rate limit（120 req/min）に合わせた内部 RateLimiter とリトライロジックを持ちます。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。

ディレクトリ構成
----------------
リポジトリの主要モジュール（src/kabusys 以下）を抜粋して示します。

- src/kabusys/
  - __init__.py              — パッケージ初期化（__version__ 等）
  - config.py                — 環境変数・設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py     — RSS ニュース収集・前処理・DB 保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - stats.py              — 統計ユーティリティ（Z スコア正規化）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py              — 発注/約定の監査ログ用スキーマ
    - features.py           — data.stats の公開ラッパ
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum / volatility / value）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py— 特徴量正規化・features への UPSERT
    - signal_generator.py   — final_score 計算・BUY/SELL 生成・signals への書き込み
  - execution/
    - __init__.py           — 発注層（雛形）
  - monitoring/
    - (監視用モジュールの雛形)

注意事項 / ベストプラクティス
-----------------------------
- 本コードは研究・検証目的のロジックを含みます。実運用する場合は、リスク管理・接続情報管理・テストを十分に行ってください。
- 環境によっては J-Quants の API 使用にあたり契約やキー管理が必要です。キーは安全に管理してください。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）はバックアップや権限設定に注意してください。
- シグナルを実際にブローカーに送る層（execution）は別途厳密な検証が必要です。本コードの execution は出発点の雛形と考えてください。

ライセンス・貢献
----------------
- 本リポジトリのライセンスや貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。必要なら README に追加したい「例の .env.example」や具体的な CLI/スケジュール設定例（cron / systemd timer / Airflow 等）、ユニットテストの実行方法、依存関係の明細を書き加えます。どの情報を追加しますか？