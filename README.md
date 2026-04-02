# KabuSys

KabuSys は日本株向けの自動売買/データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP 評価（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレース）などを備えています。

注意: このリポジトリはライブラリとしての実装が中心で、実行用の CLI やサービスラッパーは含まれていません。アプリケーション側で各モジュールを組み合わせて利用します。

主な特徴
- J-Quants API からの差分取得（株価、財務、マーケットカレンダー）と DuckDB への冪等保存
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメントのバッチ評価（gpt-4o-mini）
- ETF（1321）の 200 日移動平均乖離 + マクロニュースセンチメントを合成した市場レジーム判定
- ETL パイプライン（run_daily_etl）とデータ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリュー、将来リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions）のスキーマ定義・初期化（DuckDB）
- セキュリティ考慮（SSRF 対策、XML パースの安全化、API リトライとレート制限）

必須環境
- Python >= 3.10（typing の | 演算子を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール（例）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発時）pip install -e .

注: プロジェクトをパッケージとしてインストールする場合は pyproject.toml / setup.cfg に基づく手順に従ってください（この README の配布パターンは例示です）。

環境変数と設定
- 自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動で読み込みます。
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。
- 主要な環境変数（settings で参照されるもの）
  - 必須:
    - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
    - KABU_API_PASSWORD — kabu ステーション API のパスワード
    - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
    - SLACK_CHANNEL_ID — Slack チャネル ID
  - 任意（デフォルト有り）:
    - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
    - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV — one of development / paper_trading / live（デフォルト: development）
    - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - OpenAI:
    - OPENAI_API_KEY — OpenAI 呼び出しに使用（ai モジュールの引数で上書き可能）
- .env の記述は簡易的な shell 形式（KEY=VALUE）に対応します。.env.local は .env をオーバーライドします。

セットアップ手順（簡易）
1. 必要パッケージをインストール（上記参照）
2. プロジェクトルートに .env（または .env.local）を作成して必須環境変数を設定
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
3. DuckDB ファイルの初期化（監査ログ用など）
   - 例: 監査 DB を初期化して接続を取得する
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings
     conn = init_audit_db(settings.duckdb_path)
   - または既存の DuckDB 接続を使用して init_audit_schema を呼ぶことも可能
4. 必要に応じて ETL を実行してデータを取り込む（下記参照）

基本的な使い方（コード例）
- DuckDB 接続の作成
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  # ETLResult を返す。result.to_dict() で詳細確認可能。

- ニュースの AI スコアリング（前日 15:00 JST 〜 当日 08:30 JST ウィンドウ）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))
  # written は書き込まれた銘柄数

- 市場レジーム判定（ETF 1321 の MA200乖離 + マクロセンチメント）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))
  # market_regime テーブルに書き込み

- 研究用ファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化（既述）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

運用上の注意
- OpenAI 呼び出しは API リトライ・バックオフを備えていますが、料金とレート制限に注意してください。API KEY は OPENAI_API_KEY または関数引数で指定できます。
- J-Quants API はレート制限（120 req/min）を守るため内部でスロットリングを行います。
- ETL / AI の各処理はルックアヘッドバイアス対策が組み込まれています（関数は date 引数を受け取り、内部で date.today() を参照しません）。
- ニュース収集では SSRF 対策と XML 安全化（defusedxml）を実施していますが、外部フィードの挙動には注意してください。
- DuckDB の executemany はバージョン依存の挙動があるため、モジュール内で対応済みです。

よく使う API（概要）
- kabusys.config.settings — 環境変数ベースの設定取得
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（結果オブジェクト）
- kabusys.data.jquants_client — J-Quants API クライアント（fetch_*/save_*）
- kabusys.data.news_collector — RSS 収集ユーティリティ（fetch_rss 等）
- kabusys.data.quality — 品質チェック（run_all_checks 等）
- kabusys.ai.news_nlp.score_news — ニュースセンチメント計算と ai_scores 書込み
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定（market_regime 書込み）
- kabusys.research.* — 研究／因子計算ユーティリティ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み / 設定クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースのバッチセンチメント評価（OpenAI）
    - regime_detector.py — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダーの判定・更新ロジック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py — データ品質チェック（欠損・スパイク・重複等）
    - audit.py — 監査ログ用スキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

開発 / テストに関するヒント
- 自動環境読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（ユニットテストで .env の影響を排除）
- OpenAI の呼び出し部分はモジュール内で _call_openai_api をラップしているため、ユニットテストでは patch して差し替えが可能です（モック化しやすい設計になっています）。
- DuckDB を ":memory:" で使うとテスト用にインメモリ DB が利用できます（init_audit_db などは ":memory:" に対応）。

ライセンス / 貢献
- 本 README ではライセンス情報を含めていません。実際のリポジトリの LICENSE を確認してください。  
- コントリビュートする際はコードのスタイル、型注釈、安全性（リトライ・例外ハンドリング）、およびルックアヘッドバイアス対策を維持してください。

お問い合わせ
- 実装方針や仕様に関する質問があれば、リポジトリの issue を立てるか直接メンテナにお問い合わせください。

以上が KabuSys の概要・セットアップ・使い方の簡易ガイドです。具体的な利用例や運用用ラッパー（サービス / スケジューラ / デプロイ手順）は、利用環境に合わせて作成してください。