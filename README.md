# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買基盤のライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査（オーディット）ログなどを含むモジュールセットを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ基盤向けに設計された Python ライブラリです。主要な責務は以下です：

- J-Quants API を用いたデータ取得（株価日足、財務、マーケットカレンダー等）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集 & LLM を用いたニュースセンチメント解析（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの組合せ）
- ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）

パッケージはモジュールごとに責務が分離され、Look-ahead bias を避ける設計や冪等性（DB保存の ON CONFLICT）、外部 API の堅牢なリトライ／レート制御等に配慮されています。

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策等含む）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: LLM による銘柄別ニュースセンチメント取得 → ai_scores へ保存
  - regime_detector.score_regime: ETF の MA200 乖離とマクロニュースセンチメントを合成して market_regime を保存
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラス: 環境変数 / .env 読み込み（自動ロード機能あり）を提供

---

## 要件

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール（編集可能モード推奨）
   - pip install -e .
   - 必要なライブラリを個別にインストール（例）
     - pip install duckdb openai defusedxml

3. 環境変数の準備
   - ルートに `.env`（と必要なら `.env.local`）を配置すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定（必要に応じて）
   - 任意（デフォルトあり）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite パス（監視用）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

4. データベース初期化（監査スキーマ等）
   - 例:
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     import duckdb
     conn = init_audit_db(settings.duckdb_path)

   - または既存の DuckDB 接続にスキーマを追加する:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方

以下は代表的な利用例です。すべての API は duckdb.DuckDBPyConnection を受け取る設計です。

1) ETL（日次パイプライン）の実行
- 例（Python）:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl はカレンダー→株価→財務→品質チェックの順で実行し ETLResult を返します。

2) ニュースの LLM スコアリング（銘柄別ニュースセンチメント）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"書込み銘柄数: {n_written}")

- score_news は raw_news / news_symbols を参照して ai_scores を更新します。

3) 市場レジーム判定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使用

- ETF（1321）の MA200 乖離とマクロニュース LLM スコアを合成して market_regime テーブルに保存します。

4) ファクター計算 / リサーチ用ユーティリティ
- 例:
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026,3,20)
  momentum = calc_momentum(conn, target)
  volatility = calc_volatility(conn, target)
  value = calc_value(conn, target)
  forward = calc_forward_returns(conn, target)
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")

5) データ品質チェック
- run_all_checks を使うと全チェックをまとめて実行できます。
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=target)
  for i in issues:
      print(i)

注意点:
- ほとんどの関数は内部で datetime.today() を参照しないように設計されており、バックテストや再現性のある実行に向いています。
- OpenAI を呼ぶ箇所は API キーが必須（引数で注入可）。API 呼び出しはリトライやフォールバック（失敗時は 0.0 等の安全値）を行います。

---

## 環境変数（主な一覧、.env 例）

必須:
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token_
- OPENAI_API_KEY=あなたの_openai_api_key_
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

任意（デフォルトあり）:
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0

自動ロード無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
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
      - stats.py
      - audit.py
      - auditの初期化ユーティリティ等
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research と data のユーティリティを組み合わせた関数群

各モジュールは README の「機能一覧」で説明した責務を担っています。詳細は各モジュールの docstring を参照してください。

---

## 開発 / テスト時のヒント

- 環境変数ロードは .env / .env.local をプロジェクトルート（.git や pyproject.toml を基準）から自動読み込みします。テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はユニットテストでモックしやすい設計になっています。
- DuckDB を用いるためインメモリ（":memory:"）でテスト可能です。init_audit_db(":memory:") で監査スキーマ初期化後にテストを行うと良いです。
- ETL / 保存は冪等（ON CONFLICT DO UPDATE）を前提としています。部分失敗時に既存データを保護する設計になっています。

---

必要であれば README にサンプル .env.example や詳しい CLI 実行例（cron ジョブ、systemd ユニット、Dockerfile など）を追加します。どの情報を優先して追記しますか？