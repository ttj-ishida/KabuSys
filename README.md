KabuSys
=======

日本株向けの自動売買・データ基盤ライブラリ群です。  
DuckDB をデータストアとして、J-Quants API からのデータ取得（ETL）、RSS ベースのニュース収集、LLM を用いたニュースセンチメント評価、マーケットカレンダーや監査ログなど、アルゴリズムトレーディングに必要なデータ処理・監査・研究ユーティリティを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB をコアに SQL + Python で効率的に処理
- 外部 API 呼び出しはリトライ・レートリミット・フェイルセーフを備える
- ETL / 品質チェック / 監査ログは冪等性・トレーサビリティを重視

機能一覧
- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄情報取得
  - 差分取得、バックフィル、DuckDB への冪等保存
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- カレンダー管理（営業日判定、次/前営業日の取得、期間内営業日列挙、カレンダー更新ジョブ）
- ニュース収集（RSS → raw_news 保存、URL 正規化・SSRF 対策・XML 防御）
- ニュース NLP（OpenAI を用いた銘柄別センチメント算出）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメントを合成）
- 研究ユーティリティ（ファクター計算、将来リターン計算、IC、統計サマリー、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions テーブル、監査スキーマ初期化ユーティリティ）
- 設定管理（.env 自動読み込み / 環境変数取得ラッパー）

セットアップ手順（開発環境向け）
1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（主要な依存例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに packaging や requirements.txt がある場合はそちらを使用してください）

3. 環境変数 / .env の準備
   - 設定は環境変数、またはプロジェクトルートの .env / .env.local ファイルから自動読み込みされます。
   - 自動ロードは、パッケージ内の config モジュールが .git または pyproject.toml を見つけてプロジェクトルートを決定した場合に行われます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須の環境変数（本リポジトリ内で参照される例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack Bot トークン（通知用）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（通知先）
   - OPENAI_API_KEY        : OpenAI 呼び出しで使用（news_nlp / regime_detector に必要）
   - オプション:
     - KABUSYS_ENV (development / paper_trading / live) （デフォルト development）
     - LOG_LEVEL (DEBUG/INFO/…)
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   .env 例（簡易）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的な呼び出し例）
- DuckDB 接続の作成
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックをまとめて実行）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- 単体 ETL（株価 / 財務 / カレンダー）
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- ニュース収集（RSS をフェッチして raw_news に保存するユーティリティ関数が存在）
  from kabusys.data.news_collector import fetch_rss, preprocess_text
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

- ニュース NLP スコア付け（銘柄別 ai_scores へ書き込み）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で指定

- 市場レジームスコア算出（market_regime テーブルへ書き込み）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査スキーマ初期化（監査用 DB を新規作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" でメモリ DB も可

- 設定取得
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

設計上の注意点（要点）
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。api_key 引数を関数に渡して上書きできます。
- LLM/API の失敗はフェイルセーフで扱い、致命的な失敗にしない設計（多くの箇所で 0.0 にフォールバック、ログ出力）。
- ETL は冪等（保存時に ON CONFLICT DO UPDATE ）で再実行可能。
- 日付処理はすべて明示的に target_date を受け取る設計で、ルックアヘッドバイアスを防止しています。
- DuckDB のテーブルスキーマはモジュールロジックと整合する必要があります（ETL / audit 初期化関数を活用してください）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動読み込み & settings
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（LLM）処理
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン / run_daily_etl 等
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS 収集 / 正規化 / 保存ロジック
    - calendar_management.py     — 市場カレンダー・営業日判定
    - quality.py                 — データ品質チェック
    - stats.py                   — zscore_normalize 等統計ユーティリティ
    - audit.py                   — 監査ログスキーマ初期化 / DB 作成ヘルパ
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility ファクター
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - research/*（その他リサーチユーティリティ）
  - ...（他モジュール: strategy / execution / monitoring が __all__ に含まれる想定）

ロギングと動作モード
- 設定: KABUSYS_ENV = development / paper_trading / live
  - settings.is_dev / is_paper / is_live で判定可能
- LOG_LEVEL 環境変数でログレベルを制御（DEBUG/INFO/…）

テスト・デバッグ
- OpenAI / HTTP 呼び出しは各モジュール内で一箇所にまとめられており、ユニットテストではモック差し替えが容易な構造になっています（例: kabusys.ai.news_nlp._call_openai_api を patch する等）。
- .env 自動読み込みはプロジェクトルートの特定に依存するため、ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

ライセンス / 貢献
- 本 README はコードベースに基づく簡易ドキュメントです。リポジトリに LICENSE や CONTRIBUTING 指針があればそちらを参照してください。

補足
- 実際に運用する際は、API トークンやシークレットを安全に管理してください（CI/CD のシークレット管理、Vault、Secret Manager 等を推奨）。
- ライブ運用（実際の注文発注）を行う前に paper_trading モードや十分なシミュレーションで動作検証を必ず行ってください。

必要であれば、README に以下を追加できます:
- 各 DuckDB テーブルのスキーマ（DDL）
- 具体的な .env.example ファイルのテンプレート
- docker-compose / systemd ジョブ例（バッチ実行・スケジューリング）
- 開発フロー（テストの実行方法、ローカル ETL のデバッグ手順）

必要があれば上記の詳細を追記します。