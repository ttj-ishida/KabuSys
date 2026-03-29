# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリです。  
データ取得（J‑Quants）、ETL、データ品質チェック、ニュース収集＋LLMによるニュースNLP、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレース）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を備えた内部ツール／ライブラリです。

- J‑Quants API を用いた株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、前処理）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄単位）とマクロセンチメント＋ETF MA200 による市場レジーム判定
- 研究用途のファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレース用テーブル定義と初期化）
- 環境変数ベースの設定管理（.env 自動読み込み機能、保護キー対応）

設計上の共通方針の例:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を安易に参照しない、クエリに排他条件を付ける）
- DuckDB を SQL + Python で高速に処理
- API 呼び出しはリトライ・バックオフ・レート制限を内蔵
- フェイルセーフ：外部API失敗時はスキップ/ゼロフォールバックで継続可能にする

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - jquants_client（J‑Quants API 呼び出し・保存ロジック）
  - market calendar 管理（is_trading_day 等）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - news_collector（RSS 取得と前処理）
  - audit（監査テーブルの DDL と初期化）
  - stats（zscore 正規化）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)：銘柄ごとニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None)：ETF 1321 の MA200 乖離とマクロセンチメントを融合して market_regime テーブルへ書き込む
- research/
  - factor_research（calc_momentum, calc_volatility, calc_value）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - Settings クラスで環境変数を一元管理
  - .env 自動読み込み（プロジェクトルート判定：.git または pyproject.toml）
- 監査用 DB 初期化（init_audit_db / init_audit_schema）

---

## 必要な環境変数

config.Settings で参照する主要な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD: kabuステーション等に接続する場合のパスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
  - OPENAI_API_KEY: OpenAI 呼び出しに使用（ai モジュール）
- 任意 / デフォルトあり
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト "development"）
  - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）

自動 .env ロードはデフォルトで有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python 環境を準備（推奨: 3.9+）
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt が無い場合は主要依存のみインストール:
     - pip install duckdb openai defusedxml
   - プロジェクトを editable インストール（パッケージ化されている前提）:
     - pip install -e .

3. .env の作成
   - リポジトリルートに .env（または .env.local）を作成し、必要な環境変数を設定してください。
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - SLACK_BOT_TOKEN=xxx
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

5. テスト時の自動 .env 読み込みを無効にするには:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡単な例）

以下はライブラリの主要機能を呼ぶための最小例です。すべて Python スクリプト / REPL 内で実行できます。

- DuckDB 接続を作る:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する:
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20), id_token=None)
  - print(result.to_dict())

- ニュースセンチメント（銘柄単位）をスコアリングして ai_scores に書き込む:
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
  - print(f"scored {n} codes")

- 市場レジーム判定を実行する:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ用 DuckDB を初期化する:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # テーブルが作成されロギングが有効になる

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026,3,20))
  - # zscore 正規化
  - from kabusys.data.stats import zscore_normalize
  - normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注意:
- ai モジュールは OpenAI API を呼び出します。APIキー（OPENAI_API_KEY）を .env か環境変数で設定してください。
- J‑Quants API は認証トークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## よく使う関数一覧（抜粋）

- data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
- data.pipeline.run_prices_etl(...)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.calendar_management.is_trading_day(conn, d)
- data.news_collector.fetch_rss(url, source)
- data.quality.run_all_checks(conn, target_date=..., reference_date=...)
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- research.factor_research.calc_momentum(conn, target_date)

---

## ディレクトリ構成

（ソースの主要ファイル構成の抜粋）

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
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他 client/quality/etl 関連)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（他モジュール）
    - (strategy/, execution/, monitoring/ はパッケージ公開名に含まれる想定)

上記は主要モジュールのみを抜粋しています。詳細はソースツリーを参照してください。

---

## 注意事項 / 運用上の補足

- ルックアヘッドバイアスの防止に設計が向けられているため、関数呼び出し時は target_date を明示的に指定することを推奨します。
- OpenAI 呼び出しはレスポンスのバリデーション・リトライ・フォールバックを備えていますが、API コストとレート制限に注意してください（バッチ処理・retry/backoff を含む）。
- J‑Quants API のレート制限 (120 req/min) を守るために内部でレートリミッタを使用しています。
- DuckDB バージョンや SQL の一部挙動に依存する箇所があるため、DuckDB の互換性に留意してください（コード内に互換性注意書きあり）。
- ニュース収集では SSRF 対策、XML の安全パーシング、レスポンスサイズ制限などに配慮しています。

---

## 開発 / テスト

- 自動 .env 読み込みを無効にしてテストしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- モジュール単位で OpenAI 呼び出し等をモックしてテスト可能（コード内で差し替え可能な _call_openai_api 等の抽象化がある）。
- ロギングレベルは環境変数 LOG_LEVEL で制御できます。

---

問題報告・機能要望・リファクタリング提案などがあれば、ソース管理に沿って Issue / PR を作成してください。