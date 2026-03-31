# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けライブラリです。J-Quants 等の外部データソースからデータを取得・保存（DuckDB）、品質チェックを行い、ニュース NLP / マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

以下はこのリポジトリの README（日本語）です。

## プロジェクト概要

- 日本株向けデータ ETL（J-Quants からの株価 / 財務 / カレンダー取得）
- ニュース収集（RSS）→ raw_news 保存、銘柄紐付け
- OpenAI を使ったニュースセンチメント解析（AI スコア）と市場レジーム判定
- リサーチ用のファクター計算（モメンタム／ボラティリティ／バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）を DuckDB に格納
- 環境変数ベースの設定管理（.env 自動ロード機能あり）

設計上の特徴:
- ルックアヘッドバイアスを避けるため、内部実装は日付参照に注意している（datetime.today() を直接参照しない等）
- DuckDB をデータ永続化に利用
- 外部 API 呼び出しはリトライ／バックオフやレート制御を備える
- モジュール毎に冪等性を考慮した保存処理（ON CONFLICT / DELETE→INSERT など）

## 主な機能一覧

- data
  - J-Quants クライアント（認証・ページネーション・保存）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - market_calendar 管理（営業日、SQ判定、next/prev_trading_day 等）
  - news_collector（RSS 収集、SSRF対策、トラッキングパラメータ除去）
  - quality（欠損・重複・スパイク・日付整合性チェック）
  - audit（監査ログスキーマ作成 / 初期化）
  - stats（Zスコア正規化等の統計ユーティリティ）
- ai
  - news_nlp: ニュース記事をまとめて OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores テーブルへ保存
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を判定・保存
- research
  - factor_research: モメンタム、ボラティリティ、バリューなどのファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）、統計サマリー 等
- config
  - 環境変数読み込み、.env/.env.local の自動ロード、設定値アクセス（settings オブジェクト）
- その他: 実行監視・Slack 通知等の設定用プロパティ（設定は環境変数で管理）

## セットアップ手順

前提: Python 3.10 以上を推奨（型記法や機能に依存）。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate      (Windows)

3. 必要パッケージをインストール
   - 主要依存例（requirements.txt が無い場合の最低例）:
     - pip install duckdb openai defusedxml
   - 他に urllib / sqlite3 等は標準ライブラリを使用します。

4. 環境変数を設定
   - リポジトリルートの `.env` / `.env.local` を作成することで自動読み込みされます（詳細は下記）。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN: Slack ボットトークン（必要なら）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必要なら）
     - KABU_API_PASSWORD: kabu API のパスワード（注文連携を行う場合）
     - OPENAI_API_KEY: OpenAI を利用する場合に必要（ai モジュール）
   - 任意の設定（デフォルトあり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等
   - 自動 .env ロードを無効化するには:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定（テストなどで使用）

5. データベース初期化（監査ログ等）
   - 監査ログ用 DB を初期化する一例:
     - Python REPL などで:
       - import duckdb
       - from kabusys.data.audit import init_audit_db
       - conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続に対して init_audit_schema(conn) を呼び出す

## 使い方（簡単な例）

以下は代表的なユースケースのコード例（Python）。

- DuckDB 接続を作る:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースの NLP スコア付与（ai/news_nlp）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で参照
  - print(f"updated {n} codes")

- 市場レジームスコア算出（ai/regime_detector）:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - s = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, target_date=date(2026,3,20))
  - normalized = from kabusys.data.stats import zscore_normalize
  - normalized_records = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

- 監査ログスキーマの初期化:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

注意事項:
- OpenAI を利用する関数は api_key を引数で受け取り、省略時は環境変数 OPENAI_API_KEY を参照します。
- ETL / AI モジュールは外部 API を呼ぶためネットワーク・API 利用料が発生します。テスト時は該当呼び出しをモックしてください。
- DuckDB の executemany は空リストを受け付けないバージョン（例: 0.10）向けのガードを実装していますが、念のためパラメータが空でないことを確認してください。

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu): kabu API のパスワード
- KABU_API_BASE_URL (任意): kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI): OpenAI の API キー
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (任意): Slack 通知用
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite（監視など）パス
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: INFO 等（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化

.env / .env.local の読み込み挙動:
- 自動でリポジトリルート（.git または pyproject.toml が存在するディレクトリ）から .env を読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- .env.local は override=True で読み込まれる（.env の値を上書きするが OS 環境変数は保護される）

## ディレクトリ構成（主なファイルと説明）

以下はコードベースの主要モジュールです（src/kabusys 以下）。実際のリポジトリではこれに加えて tests, docs, examples 等があるかもしれません。

- src/kabusys/__init__.py
  - パッケージ初期化（バージョン・公開サブパッケージ）

- src/kabusys/config.py
  - 環境変数・設定管理（.env 自動読み込み、Settings オブジェクト）

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: ニュースセンチメント解析（OpenAI によるバッチ解析・結果の ai_scores への保存）
  - regime_detector.py: マーケットレジーム判定（ETF 1321 MA200 とマクロニュース）

- src/kabusys/data/
  - __init__.py
  - calendar_management.py: 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - etl.py: ETL の公開型（ETLResult 再エクスポート）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - stats.py: 統計ユーティリティ（zscore_normalize）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ（DDL 定義、初期化、インデックス）
  - jquants_client.py: J-Quants API クライアント（認証、fetch / save 系）
  - news_collector.py: RSS 収集（SSRF 対策、前処理、raw_news 保存）

- src/kabusys/research/
  - __init__.py
  - factor_research.py: モメンタム／ボラティリティ／バリュー等
  - feature_exploration.py: 将来リターン、IC、統計サマリー、rank ユーティリティ

- その他
  - 各モジュール内に logger を使用した情報・警告出力、例外処理、トランザクション制御（BEGIN/COMMIT/ROLLBACK）あり

例: 簡易ツリー
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - pipeline.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - calendar_management.py
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

## 運用上の注意・ベストプラクティス

- OpenAI・J-Quants API には利用制限・課金があるため、本番運用前にキーと制限を確認してください。
- テスト環境では外部 API 呼び出しをモックしてください（コード内にもモックポイントの想定あり）。
- データベースファイルはバックアップ・スナップショットを適宜行ってください。
- ETL は backfill を使って直近数日の再取得を行う設計になっています（API の後出し修正を吸収）。
- 監査ログ（audit テーブル）は削除しない前提のスキーマ設計です。不要な削除や UPDATE を行わないでください。
- 自動 .env ロードを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

この README はコード内のドキュメント文字列（docstring）をもとにまとめています。詳細な使用方法や追加の運用手順（CI/tuning/monitoring）はプロジェクト固有のドキュメントを参照してください。質問や補足があれば教えてください。