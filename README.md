README
=====

概要
----
KabuSys は日本株のデータ収集／品質管理／ファクター計算／ニュースNLP／市場レジーム判定／監査ログなどを包含する自動売買／研究プラットフォーム向けのライブラリ群です。DuckDB をバックエンドに用い、J-Quants API や RSS、OpenAI（LLM）などと連携してデータパイプラインと解析処理を提供します。

主な機能
--------
- データ取得（J-Quants API）: 株価日足、財務データ、上場情報、マーケットカレンダーの差分取得と DuckDB への冪等保存
- ETL パイプライン: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）、差分取得・バックフィル対応
- データ品質チェック: 欠損／スパイク／重複／日付不整合の検出（QualityIssue 表現）
- ニュース収集: RSS フィードの安全な収集・正規化・raw_news への保存
- ニュース NLP: OpenAI（gpt-4o-mini）でニュースを銘柄別にスコア化して ai_scores に登録
- 市場レジーム判定: ETF（1321）の MA200乖離 と マクロニュースセンチメントを合成して market_regime に登録
- 研究ユーティリティ: ファクター計算（モメンタム／バリュー／ボラティリティ）、将来リターン、IC、統計サマリー、Zスコア正規化
- 監査ログ（audit）: signal → order_request → execution のトレーサビリティ用スキーマ定義と初期化ユーティリティ
- 設定管理: .env 自動読み込み（プロジェクトルート検出）、環境変数アクセスのラッパ

要件
----
- Python 3.10+
- 必要な主なライブラリ:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - （標準ライブラリで多くを実装していますが、HTTP や XML 処理に標準/外部依存があります）
- ネットワーク接続: J-Quants API、OpenAI、RSS フィード などへのアクセス

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 例（requirements.txt がある場合）:
     - pip install -r requirements.txt
   - 直接インストールする場合:
     - pip install duckdb openai defusedxml

   - パッケージ化されている場合は開発モードでインストール:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml が存在する場所）に .env を置くと自動で読み込まれます（自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（主な）環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
     - SLACK_BOT_TOKEN: （Slack 通知を使う場合）
     - SLACK_CHANNEL_ID: （Slack 通知を使う場合）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要な場合）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime 等）
   - 任意（デフォルトが用意されているもの）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - .env の行の書き方は一般的な KEY=VAL に対応し、export KEY=VAL、クォートやコメントにも対応しています。

使い方（簡易）
----------------

- 共通準備: DuckDB 接続例
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（データ取得・保存・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=None, id_token=None)
  - result は ETLResult 型。has_errors / to_dict() 等を利用可能。

- ニュースをスコア化する（OpenAI 必須）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY が使われます。戻り値は書き込んだ銘柄数。

- 市場レジームを判定する（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  - market_regime テーブルに結果を冪等的に書き込みます。

- 監査DB（監査ログ専用）の初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  - これにより audit 用スキーマ（signal_events / order_requests / executions）を作成します。

- J-Quants API を直接使う例
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - id_token = get_id_token()  # JQUANTS_REFRESH_TOKEN 必須
  - records = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)

注意点・運用上のヒント
---------------------
- OpenAI 呼び出しはリトライやフォールバック（失敗時は中立スコア 0.0）を組み込んでいますが、APIキーと料金・レートに注意してください。
- J-Quants API は 120 req/min のレート制限を守るため内部でスロットリングしています。大量取得時は時間がかかります。
- データの「ルックアヘッドバイアス」防止が設計方針として徹底されています（datetime.today()/date.today() を直接参照しない、ETL やスコアリングは明示的に対象日を指定することを推奨）。
- 自動 .env 読み込みを無効化したいテストなどでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（概略）
-----------------------
src/kabusys/
- __init__.py
  - パッケージ初期化、公開サブモジュールリスト定義
- config.py
  - 環境変数読み込み／Settings クラス（J-Quants, kabu, Slack, DB パス, 監視設定 等）
- ai/
  - __init__.py
  - news_nlp.py     : ニュース記事を OpenAI でスコアし ai_scores に書き込む主要ロジック
  - regime_detector.py : マクロニュース + ETF(1321) MA200 乖離を合成して market_regime を算出
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - pipeline.py       : ETL パイプライン（run_daily_etl 等）
  - etl.py            : ETLResult の公開エイリアス
  - news_collector.py : RSS 取得と前処理、raw_news への保存ロジック
  - calendar_management.py : JPX カレンダーの管理・営業日の判定・更新ジョブ
  - quality.py        : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py          : zscore_normalize 等の統計ユーティリティ
  - audit.py          : 監査ログ（DDL / 初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py : モメンタム / バリュー / ボラティリティ 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、rank関数

各ファイルの役割（簡単）
- jquants_client.py: API レート制御、認証（get_id_token）、fetch_*、save_*（raw_prices, raw_financials, market_calendar）などを提供します。
- pipeline.py: ETL の高レベル関数（run_daily_etl）と差分ETL（run_prices_etl 等）を提供。品質チェックを組み合わせて結果を ETLResult で返します。
- news_nlp.py / regime_detector.py: OpenAI と連携する機能。API キーは引数で注入可能（テスト用）、または OPENAI_API_KEY 環境変数を参照します。
- audit.py: 監査ログ用の DDL と初期化関数を提供。init_audit_db でファイル作成とスキーマ初期化を行います。

ライセンス・貢献
----------------
（ここにはプロジェクト固有のライセンスや貢献ルールを記載してください — 例: MIT, CONTRIBUTING.md）

付録: 主要環境変数一覧（概要）
--------------------------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for AI機能): OpenAI の API キー
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (Slack 通知)
- KABU_API_PASSWORD, KABU_API_BASE_URL (kabu ステーション API)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live, default=development)
- LOG_LEVEL (ログレベル、default=INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化

この README はコード内の docstring と設計方針を要約したものです。より詳細な利用方法や運用手順（バッチスケジューリング、監視設定、バックテストとの分離など）はプロジェクトのドキュメント（Design doc / DataPlatform.md / StrategyModel.md 等）を参照してください。