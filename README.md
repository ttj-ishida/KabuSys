# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ、ETL パイプライン、そして市場レジーム判定までを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API からの株価・財務・マーケットカレンダー等の差分取得と DuckDB への冪等保存（ETL）。
- RSS ニュースの収集と前処理、OpenAI を利用したニュースごとのセンチメント算出（ai_scores へ保存）。
- 市場レジーム（bull/neutral/bear）判定（ETF の MA 乖離 × ニュースセンチメントの合成）。
- 研究用途のファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ。
- 監査ログ（signal → order_request → executions）のスキーマ初期化と監査 DB 管理。
- データ品質チェック（欠損・重複・スパイク・日付整合性）。

設計上の留意点として、バックテスト時のルックアヘッドバイアスを避ける実装（date の明示、DB クエリの排他条件等）や、外部 API 呼び出しの堅牢性（リトライ、レート制御、フェイルセーフ）を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得 + 保存；トークン自動リフレッシュ、レート制御、リトライ）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げて銘柄別スコアを生成し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
  - OpenAI 呼び出しはリトライ・JSON 検証を含む堅牢な実装
- research/
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env 自動読み込み（プロジェクトルート検出）、設定アクセス用 settings オブジェクト
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）

---

## 要件

- Python 3.10 以降（型注釈に `|` を使用）
- 主な依存ライブラリ:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）

（プロジェクトで pyproject.toml を使っている想定です。packaging に合わせて仮想環境・依存解決を行ってください。）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   - 例（venv + pip）:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存関係をインストールします（プロジェクトに requirements.txt / pyproject.toml がある想定）。

   - pip を使う例:
     - pip install -U pip
     - pip install duckdb openai defusedxml

   - もしくは:
     - pip install -e .  （パッケージ化されている場合）

3. 環境変数を用意します。
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと、自動的に読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須変数（アプリ起動時に参照される主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY (ai モジュールを使う場合)
   - その他（任意・デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - 簡単な .env 例:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567

4. データディレクトリを作成（DuckDB ファイル等を保存する場合）:
   - mkdir -p data

---

## 使い方（Python API 例）

基本的には DuckDB の接続を作成して、各モジュール関数に渡して実行します。

- ETL（1 日分の差分 ETL を実行）:

  - 例:
    - from datetime import date
    - import duckdb
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    - print(result.to_dict())

- ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で与えられます）:

  - 例:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - n = score_news(conn, target_date=date(2026,3,20))
    - print(f"scored {n} codes")

- 市場レジーム判定:

  - 例:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.regime_detector import score_regime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_regime(conn, target_date=date(2026,3,20))

- 監査 DB の初期化（監査ログ用の DuckDB を作成）:

  - 例:
    - from kabusys.data.audit import init_audit_db
    - conn = init_audit_db("data/audit.duckdb")
    - # これで監査テーブルが作成される

- 設定値の参照:

  - 例:
    - from kabusys.config import settings
    - print(settings.jquants_refresh_token)
    - print(settings.duckdb_path)

---

## 主要関数・エントリポイント一覧

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult dataclass（結果集約）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss(url, source)
- kabusys.data.quality
  - run_all_checks 等
- kabusys.data.audit
  - init_audit_schema / init_audit_db
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize(records, columns)

---

## 安全性・設計上の注意

- Look-ahead bias 対策:
  - 日時判定やニュースウィンドウ等で現在日時を安易に参照しない実装。
  - DB クエリは target_date 未満 / 以前等、ルックアヘッドを防ぐ条件を厳格に使用。
- 外部 API 呼び出しの堅牢性:
  - J-Quants クライアントはレート制御（120 req/min）、リトライ、401 リフレッシュ対応を実装。
  - OpenAI 呼び出しは JSON レスポンス検証・リトライ・フェイルセーフ（失敗時は 0.0 でフォールバック）実装。
- ニュース収集のセキュリティ:
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策（プライベート IP チェック）、受信サイズ上限。
  - defusedxml を利用して XML ベースの攻撃を防止。
- DuckDB への保存は基本的に冪等（ON CONFLICT / DO UPDATE）で設計。
- 監査ログは削除しない想定（完全トレーサビリティ）。order_request_id は冪等キーとして機能。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - audit.py
    - stats.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (package 想定、コードベースに一部あり)
  - research/ ...
- pyproject.toml (プロジェクトルート想定)
- .git/ （プロジェクトルート探索に使用）
- .env.example（存在する場合は参照して設定作成）

---

## 開発・テスト

- 自動 .env 読み込みはデフォルトで有効。テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- OpenAI / J-Quants API 呼び出し部分はモック可能に実装されています（テスト時は該当モジュール関数を patch してください）。
- DuckDB はファイルベースでもインメモリ（":memory:"）でも使用可能なユーティリティ関数を用意。

---

## 貢献・ライセンス

- 貢献する場合は issue / PR を送ってください（リポジトリの CONTRIBUTING に準拠）。  
- ライセンスはプロジェクトのルートに置かれた LICENSE を参照してください（この README には含めていません）。

---

不明点や追加で README に載せたい実行例（CLI コマンド、systemd サービス化、cron ジョブ例など）があれば教えてください。必要に応じてサンプル .env.example や簡易の run script を追記します。