KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株を対象としたデータパイプライン・特徴量生成・シグナル生成・発注監査までを想定したライブラリ群です。  
主に以下の役割を持つモジュールで構成されています。

- Data 層: J-Quants からのデータ取得、DuckDB への保存、品質チェック、カレンダー管理、ニュース収集
- Research 層: ファクター計算・特徴量探索（IC・将来リターン等）
- Strategy 層: 特徴量を合成してシグナルを生成（BUY/SELL）
- Execution / Audit 層: 発注履歴・約定・ポジション・監査ログ（スキーマ定義含む）
- 設定管理: 環境変数/.env の自動読み込みと設定オブジェクト

本リポジトリはライブラリとして import して使用することを前提としています。CLI は含みませんが、簡易スクリプトや cron / job から各 API を呼ぶ設計です。

主な機能
--------
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB による永続ストレージ：raw / processed / feature / execution 層のスキーマ定義と初期化
- ETL パイプライン（日次差分取得、backfill、品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- クロスセクション Z スコア正規化ユーティリティ
- 特徴量ビルド（features テーブルへ冪等的に保存）
- シグナル生成（最終スコア算出、BUY/SELL 判定、signals テーブルへの保存）
- RSS ベースのニュース収集と銘柄抽出（SSRF対策・前処理・重複排除）
- マーケットカレンダー管理（JPX カレンダー取得・営業日判定）
- 設計に沿った監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

セットアップ手順
----------------

1. Python 仮想環境の作成（推奨）
   - macOS / Linux:
     - python3 -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 依存パッケージのインストール
   - 本リポジトリに requirements.txt がある想定：
     - pip install -r requirements.txt
   - 必須ライブラリ（主要な例）:
     - duckdb
     - defusedxml
   - （プロジェクトで他に必要なパッケージがあれば requirements.txt に追加してください）

3. 環境変数の設定 (.env)
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env/.env.local を自動読み込みします。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD=（kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN=（Slack 用 Bot Token）
     - SLACK_CHANNEL_ID=（通知先 Slack チャンネル ID）
   - 任意 / デフォルト
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|... (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH=data/monitoring.db (監視用 DB 等)
   - .env の読み込み仕様
     - .env がプロジェクトルートに存在すると自動で読み込みます（.env → .env.local の順に適用。 .env.local が上書き）。
     - export KEY=val 形式やクォート、コメントに対応した柔軟なパーサを使用しています。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから次を実行してデータベースとテーブルを作成します：

     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

   - ":memory:" を渡すとインメモリ DB を使用できます（テスト用途）。

使い方（主要 API）
-----------------

以下はライブラリを直接 import して使う際の代表例です。日付引数は datetime.date オブジェクトを使用します（"YYYY-MM-DD" を date に変換して利用）。

- ETL（日次パイプライン）
  - DuckDB 接続を用意した上で実行：

    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2025, 1, 31))
    print(result.to_dict())

  - run_daily_etl は市場カレンダーの更新 → 株価 ETL → 財務 ETL → 品質チェック の順で行います。
  - backfill_days, run_quality_checks 等の引数で挙動を調整できます。

- 特徴量ビルド（features テーブルへの保存）
  - research 側で計算した生ファクターを統合・正規化して features に保存します：

    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features

    conn = init_schema("data/kabusys.duckdb")
    n = build_features(conn, date(2025, 1, 31))
    print(f"upserted features: {n}")

- シグナル生成
  - features / ai_scores / positions を参照して BUY / SELL シグナルを生成し signals テーブルへ保存します：

    from datetime import date
    from kabusys.strategy import generate_signals
    from kabusys.data.schema import init_schema

    conn = init_schema("data/kabusys.duckdb")
    total = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
    print(f"signals written: {total}")

  - weights を与えてコンポーネント重みを上書き可能（合計は再スケールされます）。

- ニュース収集（RSS）
  - RSS をフェッチして raw_news に保存、銘柄紐付けまで行う：

    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import init_schema

    conn = init_schema("data/kabusys.duckdb")
    results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
    print(results)  # {source_name: inserted_count, ...}

- カレンダー関係ユーティリティ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等が用意されています。

- スキーマの取得 / 既存 DB への接続
  - 初回は init_schema() を用いてテーブルを作成します。以降は get_connection() を使って既存 DB に接続できます。

    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")

設計上の注意点
--------------
- ルックアヘッドバイアス防止
  - 特徴量・シグナル生成・ETL は target_date 時点で利用可能なデータのみを参照するように設計されています（未来データを参照しないことを意識）。
- 冪等性
  - DuckDB への保存処理は ON CONFLICT を使うなど冪等化を意識して実装されています。
- エラーハンドリング
  - ETL 等は各ステップで独立してエラーハンドリングされ、1 ステップの失敗が全体を止めないようになっています。戻り値で問題を確認してください。
- 自動 .env 読み込み
  - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）から .env を自動で読み込みます。テストや明示的管理が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。

ディレクトリ構成（概略）
-----------------------

（主要ファイル・モジュールのツリー表示）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — data 層の feature ユーティリティ（再輸出）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ（signal/events/order/execution）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリューの計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py    — final_score 計算とシグナル生成
  - execution/               — 発注関連（空ディレクトリ／将来的な実装想定）
  - monitoring/              — 監視・メトリクス（将来的な実装想定）

環境変数（主要）
----------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
  - SLACK_BOT_TOKEN — Slack 通知用トークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- 任意（デフォルトあり）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB など（デフォルト data/monitoring.db）
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — ログレベル（INFO / DEBUG / ...）

サンプル .env（例）
-------------------
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

開発 / 貢献
-----------
- テスト: 各モジュールはユニットテストを書きやすいように id_token 注入や _urlopen のモック等を想定しています。
- ドキュメント参照: StrategyModel.md / DataPlatform.md / DataSchema.md 等の設計ドキュメントに合わせて実装されています（プロジェクト内にあれば参照してください）。
- バグ報告・機能提案は issue にお願いします。プルリク歓迎です。

ライセンス
---------
（LICENSE ファイルに従ってください。ここでは省略）

補足
----
この README はコードベースの主要なモジュールと公開 API を説明するための概要です。各関数やモジュールの詳細な使用法やパラメータはソース内の docstring を参照してください。必要であればコマンド例やユースケースに合わせた詳細サンプルを追加できます。