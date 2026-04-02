# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
DuckDB をデータストアに、J-Quants / OpenAI 等の外部 API を用いてデータ収集・品質チェック・ファクター計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理などを行うことを目的としています。

バージョン: 0.1.0

---

## 概要

本プロジェクトは以下の主要機能をモジュール単位で提供します。

- データ取得・ETL（J-Quants API 経由）と DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 市場カレンダー管理（JPX カレンダーの夜間更新・営業日判定）
- ニュース収集（RSS）と NLP による銘柄ごとのニュースセンチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントの合成）
- 監査ログ（signal / order_request / executions）スキーマ生成・初期化
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計ユーティリティ）

設計上の特徴:
- ルックアヘッドバイアスに注意した実装（target_date を明示し、内部で date.today() を不用意に参照しない）
- DuckDB を用いた高速な SQL 処理と冪等保存（ON CONFLICT DO UPDATE）
- 外部 API 呼び出しはリトライやバックオフ、失敗時のフォールバックを備える
- テスト容易性のため API キー注入や内部呼び出しの差し替えポイントを用意

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数読み込み（.env / .env.local の自動読み込み）、設定オブジェクト `settings`
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - pipeline / etl: 日次 ETL 実行 `run_daily_etl`、個別 ETL ジョブ
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - calendar_management: market_calendar 管理・営業日判定など
  - news_collector: RSS 収集・前処理・冪等保存（SSRF 対策・サイズ制限）
  - audit: 監査ログ用スキーマ作成 / 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して `ai_scores` に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースから市場レジームを判定し `market_regime` に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- その他
  - 各所で OpenAI クライアント（gpt-4o-mini 等）を使用。テストのため関数をモック可能。

---

## セットアップ手順

1. システム要件（推奨）
   - Python 3.10+（typing と型注釈を活用しているため最新環境を推奨）
   - ネットワークアクセス（J-Quants / OpenAI 等へアクセスする場合）

2. リポジトリのクローン（例）
   - git clone <リポジトリURL>
   - cd <repo>

3. 仮想環境の作成と依存パッケージのインストール
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
   - pip install --upgrade pip
   - 必要なパッケージをインストール（例）
     - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt または pyproject.toml を用意していることを想定します）

4. 環境変数の設定
   - 本ライブラリは複数の環境変数を参照します。最低限以下を設定してください：
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news/score_regime に引数で渡すことも可能）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   - .env / .env.local を使う場合:
     - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` と `.env.local` が自動読み込みされます。
     - 読み込み順序（優先度）:
       - OS 環境変数 > .env.local > .env
     - 自動読み込みを無効化するには:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化（監査テーブル等）
   - Python REPL 等で DuckDB 接続を作り、監査スキーマを初期化します:
     - import duckdb
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続に対して init_audit_schema(conn) を呼び出せます。

---

## 使い方（主要な例）

以下は簡単な呼び出し例です。target_date は必ず明示してルックアヘッドを避けてください。

1. 日次 ETL の実行
   - 例: 当日分の ETL を実行して DuckDB に保存・品質チェックを行う
     - import duckdb
     - from kabusys.data.pipeline import run_daily_etl
     - from kabusys.config import settings
     - conn = duckdb.connect(str(settings.duckdb_path))
     - result = run_daily_etl(conn, target_date=None)  # None で today を使う
     - print(result.to_dict())

2. ニュースセンチメントのスコアリング
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - conn = duckdb.connect(str(settings.duckdb_path))
   - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使う

   - テスト用に api_key を直接渡したり、内部の API 呼び出し関数をモックして単体テスト可能です。

3. 市場レジームの判定
   - from kabusys.ai.regime_detector import score_regime
   - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

4. 監査データベース初期化
   - from kabusys.data.audit import init_audit_db
   - conn = init_audit_db("data/audit.duckdb")

5. 研究用ファクター計算
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   - from kabusys.data.stats import zscore_normalize
   - res = calc_momentum(conn, target_date=date(2026, 3, 20))
   - normalized = zscore_normalize(res, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

6. カレンダー・営業日操作
   - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
   - is_trading = is_trading_day(conn, date(2026, 3, 20))
   - next_day = next_trading_day(conn, date(2026, 3, 20))

注意:
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を前提に実装されています。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ニュース収集（RSS）はデフォルトで Yahoo Finance のビジネス RSS が定義されていますが、ソース追加や URL の正規化・SSRF 対策が組み込まれています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment (development | paper_trading | live)
- LOG_LEVEL — ログレベル

---

## テスト & モックポイント

テストを容易にするためにモック可能なポイントが用意されています。

- OpenAI 呼び出し:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
  テストでは unittest.mock.patch で差し替えて deterministic なレスポンスを返せます。

- news_collector の外部 HTTP 呼び出し:
  - kabusys.data.news_collector._urlopen をモックして HTTP レスポンスを制御可能です。

- jquants_client.get_id_token() / _request() などもモックして API をシミュレートできます。

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
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - (その他 ETL/保存ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージエクスポート対象に含める想定)
  - execution/ (パッケージエクスポート対象に含める想定)
  - (その他モジュール)

---

## 運用上の注意

- ルックアヘッドバイアス対策として、各処理は必ず `target_date` を明示して実行することを推奨します。内部で現在時刻を参照する実装は最小限に抑えられていますが、安全のためバッチ実行時は日付指定を行ってください。
- OpenAI / J-Quants など外部 API の使用にはコストが発生します。バッチの頻度やバッチサイズに注意してください。
- DuckDB の executemany にはバージョン依存の制約（空パラメータリスト不可など）があるため、ETL 実装はその点に配慮しています。DuckDB のバージョンを上げた際は互換性を確認してください。

---

この README はコードベースの主要な使い方と設計意図を要約したものです。詳細は各モジュールのドキュメント文字列（docstring）を参照してください。必要であればサンプルスクリプトや CI 設定、requirements ファイルのテンプレートも作成できます。必要があればお知らせください。