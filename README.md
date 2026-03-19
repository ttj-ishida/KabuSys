# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータレイクに使い、J-Quants からの市場データ取得、ニュース収集、ファクター計算、特徴量構築、シグナル生成、発注/監査のためのスキーマとユーティリティ群を提供します。

---

## 特徴（概要）

- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS パーサ・SSRF/サイズ制限対策・記事→銘柄紐付け）
- ファクター計算（Momentum / Value / Volatility / Liquidity）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け集計、BUY/SELL 判定、SELL 優先ポリシー）
- 監査ログ用スキーマ（シグナル→発注→約定までトレース可能）
- 設定管理（.env 自動読み込み、環境ごとのフラグ）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数管理、.env/.env.local の自動読み込み（無効化フラグあり）
  - 必須設定のアクセス用プロパティ（例: settings.jquants_refresh_token）
- kabusys.data
  - jquants_client: J-Quants API クライアント & DuckDB 保存関数
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS 収集 / raw_news 保存 / 銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - features / stats: zscore_normalize 等
  - audit: 監査ログ用テーブル定義
- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 研究用ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- kabusys.strategy
  - feature_engineering.build_features: raw factor を正規化して features テーブルに保存
  - signal_generator.generate_signals: features/ai_scores から signals を生成
- kabusys.execution, kabusys.monitoring: 拡張用プレースホルダ（パッケージ公開対象）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

推奨手順（例）:
- 仮想環境を作成
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb defusedxml

---

## 環境変数（主なキー）

kabusys.config.Settings で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト: INFO

.env 自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

1. レポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他ライブラリを追加）

4. 環境変数設定
   - プロジェクトルートに `.env`（およびローカル上書き用に `.env.local`）を作成し、以下キーを設定してください（例）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

   - 注意: .env のフォーマットはシェル形式（コメント #、export 前置にも対応）です。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)
   - これで必要なテーブルとインデックスが作成されます。

---

## 使い方（代表的な作業フロー例）

以下はモジュールを直接利用する例です。運用スクリプトや cron / Airflow / Prefect 等のワークフローに組み込んでください。

- DuckDB 初期化（1回）
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（市場カレンダー取得 → 株価/財務取得 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- 特徴量の構築（strategy 用 features テーブル更新）
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 31))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", ...}  # 上場銘柄コードセット
  - stats = run_news_collection(conn, known_codes=known_codes)

- カレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- J-Quants から直接データを取得したい場合（テスト用に id_token を渡すことも可能）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()
  - rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

ログや例外は各モジュールで適切に記録される設計です。運用時は ログレベル / ハンドラ を設定して監視してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下に実装されています）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント + 保存ロジック
    - news_collector.py        — RSS 収集・加工・DB 保存
    - schema.py                — DuckDB スキーマ定義 & init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - stats.py                 — zscore_normalize 等統計ユーティリティ
    - features.py              — features API 再エクスポート
    - calendar_management.py   — カレンダー管理・更新ジョブ
    - audit.py                 — 監査ログテーブル定義
    - (その他: quality, audit 補助等 想定)
  - research/
    - __init__.py
    - factor_research.py       — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   — calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py   — build_features（Zスコア正規化・ユニバース）
    - signal_generator.py      — generate_signals（final_score 計算・BUY/SELL）
  - execution/                 — 発注・実行層の拡張用パッケージ（空モジュール含む）
  - monitoring/                — 監視・アラート用の拡張（placeholder）

---

## 運用上の注意 / 実装上の設計ポイント

- ルックアヘッドバイアス対策: すべての計算は target_date 時点で利用可能なデータのみを参照する設計です（fetched_at の記録等）。
- 冪等性: DB への保存は基本的に ON CONFLICT / INSERT ... DO UPDATE（または DO NOTHING）を用いて冪等に実装されています。
- レート制限・リトライ: J-Quants へのリクエストは固定間隔レートリミットと指数バックオフを組み合わせた実装です。401 は自動リフレッシュ処理を試行します。
- セキュリティ: news_collector は SSRF 対策や XML 脆弱性対策（defusedxml）・レスポンスサイズ制限等を実装しています。
- 環境切替: KABUSYS_ENV を用いて development / paper_trading / live を区別できます。settings.is_live / is_paper / is_dev で判定できます。

---

## 追加情報 / 開発ヒント

- テスト時に .env の自動ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をインメモリで使いたい（テスト）:
  - conn = init_schema(":memory:")
- feature / signal の計算は外部 API（発注等）に依存しない設計になっているため、単体でユニットテストを作成しやすくなっています。

---

必要であれば README に簡易の .env.example やサンプルスクリプト（cron 用 wrapper、systemd ユニット、Dockerfile など）を追記できます。どの形式を優先して追加しますか？