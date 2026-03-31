# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（監査テーブル / 約定トレーサビリティ）など、運用に必要なユーティリティ群を提供します。

---

## 主な特徴

- データ取得（J-Quants）と DuckDB への冪等保存（ON CONFLICT 相当）を実装
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメントスコアリング（JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース sentiment を合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー）とリサーチ用ユーティリティ（IC、forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）を初期化するユーティリティ
- 自動環境変数読み込み（プロジェクトルートの .env / .env.local）／無効化可能

---

## 機能一覧（モジュール概要）

- kabusys.config
  - .env / 環境変数読み込み、設定オブジェクト（settings）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・レートリミット・保存（raw_prices / raw_financials / market_calendar）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）・ETLResult
  - news_collector: RSS 取得 / 前処理 / raw_news への保存補助
  - calendar_management: 市場カレンダー判定・更新ジョブ（is_trading_day / next_trading_day / calendar_update_job 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: MA200 乖離とマクロセンチメントを用いた市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 前提 / 必要事項

- Python 3.10+
- DuckDB（Python パッケージ）
- openai パッケージ（OpenAI の v1 SDK を想定）
- defusedxml（RSS の安全なパース）
- ネットワーク経路で J-Quants, RSS, OpenAI にアクセス可能であること

推奨インストールパッケージ（例）
- duckdb
- openai
- defusedxml

---

## 環境変数（主要）

以下はコード内で参照される主要な環境変数です（.env に設定推奨）。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabuステーション API の base URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL             : ログレベル ("DEBUG" / "INFO" / ... )（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" を設定するとパッケージインポート時の自動 .env 読み込みを無効化

.env.example を用意しておくと設定が楽になります。

---

## セットアップ手順（例）

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境と依存パッケージのインストール

   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （パッケージ配布用の setup / pyproject があれば pip install -e . でインストール）

3. 環境変数の設定

   プロジェクトルートに .env または .env.local を作成し、上記の必須キーを設定します。例:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

   ※ 自動ロードはパッケージインポート時に .env → .env.local の順で行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。

4. データベースの初期化（監査 DB など）

   監査ログ（audit）用 DB 初期化例:

   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()

   または既存 DuckDB 接続へスキーマを追加:

   import duckdb
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)

---

## 使い方（代表的な呼び出し例）

以下は simple な Python スニペット例です。適宜 logging 設定や例外処理を追加してください。

- 日次 ETL（run_daily_etl）

   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())

- ニューススコアリング（score_news）

   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key 無指定なら環境変数 OPENAI_API_KEY を使用
   print(f"書き込み銘柄数: {written}")

- 市場レジーム算出（score_regime）

   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026,3,20), api_key=None)

- カレンダー更新ジョブ（calendar_update_job）

   from datetime import date
   import duckdb
   from kabusys.data.calendar_management import calendar_update_job

   conn = duckdb.connect("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"保存レコード数: {saved}")

- 監査 DB 初期化（init_audit_db）

   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()

---

## 推奨オペレーション

- OpenAI 呼び出しはコスト・レートリミット対策が必要です。API キー管理・バッチサイズ・リトライ設定を運用に合わせて調整してください（news_nlp はバッチ数やチャンクサイズを内部で制御）。
- ETL はスケジューラ（cron / airflow / kubernetes cronjob）で日次実行し、run_daily_etl の戻り値（ETLResult）をログ・アラートに利用してください。
- データ品質チェック（quality.run_all_checks）結果に基づいてアラートを上げる運用を推奨します（重大なエラーは停止検討）。
- 監査テーブルは削除しない前提で設計されています（トレーサビリティ確保）。定期的なバックアップを推奨。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

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
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ想定: モニタリング関連の実装がこの下に入る想定)
  - execution/, strategy/, monitoring/ 等（パッケージ公開名に含まれるが実装は別途）

上記はコードベースの主要モジュールを反映しています。詳細は各モジュールの docstring を参照してください。

---

## 注意点 / 実装上の設計方針（抜粋）

- Look-ahead bias を避けるため、各モジュールは内部で date.today()／datetime.today() を直接参照しない設計。target_date を引数で与える方式を採用しています。
- OpenAI 呼び出しは失敗時にフェイルセーフ（ゼロスコアにフォールバック）する箇所があり、運用での過度な停止を避けます。
- J-Quants の API 呼び出しはレートリミット（120 req/min）に従い、指数バックオフやトークンリフレッシュを実装済みです。
- RSS 周りは SSRF 対策（リダイレクト先検査、プライベートIP検査）、XML の安全パース（defusedxml）、受信サイズ制限などを実装しています。

---

## ライセンス・貢献

（ここにプロジェクトのライセンスや貢献方法を記載してください）

---

必要であれば、README にサンプル .env.example、さらに詳細なコマンドや CI/CD / デプロイ手順（Kubernetes / systemd / cron の例）を追記できます。追加したい内容があれば教えてください。