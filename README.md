# KabuSys

日本株向け自動売買・データプラットフォームのコアライブラリ（README 日本語版）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants）・ETL・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログ基盤などを含む自動売買／リサーチ向けのコアライブラリです。  
主な設計方針として次を重視しています。

- ルックアヘッドバイアス対策（内部で date.today() を盲目的に使わない）
- DuckDB を利用したオンディスク／インメモリ分析基盤
- J-Quants / OpenAI 等外部 API との堅牢な連携（リトライ・レート制御）
- ETL の冪等性とデータ品質チェック
- 監査（signal → order → execution）トレーサビリティ

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数読み込み、各種設定（J-Quants トークン、OpenAI、DBパス 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レートリミット）
  - pipeline / etl: 日次 ETL パイプライン（価格、財務、カレンダー）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 収集・前処理（SSRF 対策・トラッキング除去）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログ（signal / order_requests / executions）のスキーマ定義・初期化
  - stats: 汎用統計ユーティリティ（Zスコア正規化）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（OpenAI）で銘柄別センチメント化して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA 乖離 × マクロセンチメントで市場レジーム（bull/neutral/bear）を算出・保存
- kabusys.research
  - factor_research: momentum/volatility/value 等ファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー 等

---

## セットアップ手順

前提: Python 3.10+（union 型注釈等を使用）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を配置できます。
   - 自動読み込みは既定で有効。無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される最低限の .env（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

   注意: `JQUANTS_REFRESH_TOKEN` は必須（settings.jquants_refresh_token が参照します）。他の変数は default 値が設定されているものもあります。

4. データディレクトリ作成
   - デフォルトでは `data/` 下に DuckDB・PID ファイル等を作成します。必要に応じて作成してください。
     - mkdir -p data

---

## 主要な使い方・コード例

以下はライブラリ関数の簡単な使用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取る設計になっています。

- DuckDB 接続を開く
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可

- 日次 ETL 実行（株価 / 財務 / カレンダー / 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースのセンチメントスコアを生成して ai_scores に保存
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  - print("書込銘柄数:", n)

- 市場レジーム算出（ETF 1321 を利用）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- 監査 DB の初期化（監査専用 DB を別ファイルに作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from datetime import date
  - moments = calc_momentum(conn, date(2026, 3, 20))
  - vols = calc_volatility(conn, date(2026, 3, 20))
  - values = calc_value(conn, date(2026, 3, 20))

- 設定値取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level

注意点:
- OpenAI 呼び出しは API キーを引数で注入可能（テストの差し替えが容易）。
- ETL / API 呼び出しはそれぞれ内部でリトライやレート制御を行いますが、API キーやネットワークの状態に応じてエラーになることがあります。
- DuckDB に対する書き込みは可能な限り冪等に処理されます（ON CONFLICT DO UPDATE 等）。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — settings.env による検証あり
- LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` と `.env.local` を順に読み込みます。
- OS 環境変数が優先されます。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動読み込みを無効化します。

---

## よく使う公開 API（抜粋）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - 日次 ETL を実行し ETLResult を返す

- kabusys.data.jquants_client.get_id_token(refresh_token=None)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースセンチメントを算出して ai_scores を更新（戻り値: 書き込んだ銘柄数）

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - マクロセンチメントと MA 乖離を組み合わせて market_regime を更新

- kabusys.data.audit.init_audit_db(db_path)
  - 監査用 DuckDB を初期化して接続を返す

- kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value

- kabusys.data.stats.zscore_normalize(records, columns)

---

## ディレクトリ構成（主要ファイル）

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: monitor / schema 等を追加可能)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (README の要望に合わせて将来的な監視モジュールを想定)
  - execution/, strategy/ (パッケージの公開一覧に含められるが本リポジトリの一部機能を想定)

各サブモジュールは上で説明した役割を担います。ファイル内に詳細なドキュメント文字列（docstring）と設計方針が書かれているため、実装や利用時は関数毎の docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- OpenAI や J-Quants の API キーは安全に管理してください（.env.local に置き、`.gitignore` に追加）。
- 本ライブラリはデータ取得・ETL・分析ロジックを提供します。実際の発注ロジックや資金管理は別モジュール／運用ルールで管理してください。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動的な .env 読み込みの副作用を防ぐと便利です。
- DuckDB ファイルはバックアップ・スナップショット運用を検討してください（破損時の復旧対策）。

---

不明点や特定機能の詳細ドキュメント（例: news_collector の RSS マッピング、jquants_client のレスポンススキーマ、audit スキーマの拡張）を追加で作成できます。どの部分をより詳しく出力するか指定してください。