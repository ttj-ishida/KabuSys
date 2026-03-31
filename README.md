KabuSys — 日本株自動売買 / データプラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータ取得・ETL、ニュース NLP（LLM ベースのセンチメント評価）、市場レジーム判定、監査ログ管理などを備えた内部ライブラリ群です。主にバックテスト / リサーチ / 自動売買システムの基盤層を提供します。設計上、ルックアヘッドバイアス防止・冪等性・堅牢な API リトライ／レート制御・サニティチェックを重視しています。

主な機能
--------
- データ取得・ETL
  - J-Quants API からの株価（日足）・財務データ・上場情報・JPX カレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・前処理
  - RSS フィードの収集と前処理（URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 上限チェック）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）でセンチメント化し ai_scores に書き込む（score_news）
  - マクロニュース + ETF (1321) の MA200 乖離から市場レジーム（bull/neutral/bear）を判定（score_regime）
  - API 呼び出しはリトライ・フォールバック（失敗時は中立スコア）
- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（相関）計算、Z スコア正規化など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ初期化と専用 DB 初期化ユーティリティ
- カレンダー管理
  - market_calendar の取得・更新、営業日判定・前後営業日の取得等

セットアップ
-----------
1. Python 環境（3.10+ を想定）を用意します。

2. 必要なパッケージをインストールします（例）:
   - duckdb
   - openai
   - defusedxml
   - （その他 logging 等は標準ライブラリ）
   例:
   pip install duckdb openai defusedxml

   （プロジェクトが pyproject.toml を持つ場合は pip install -e . が可能な想定です）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと自動的に読み込まれます（デフォルト）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主に必要となる環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で省略時に参照）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuAPI のベース URL（省略時 http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
   - Settings は kabusys.config.settings から参照できます。未設定の必須値は ValueError を投げます。

基本的な使い方（サンプル）
-------------------------

- DuckDB 接続を作成して日次 ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを取得して ai_scores に保存する
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {n_written}")

  ※ api_key を省略すると環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定を実行する
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査 DB を初期化する
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

- カレンダー関連ユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))

実装上の注意点 / テストヘルプ
-----------------------------
- ルックアヘッドバイアス防止: 多くの関数は datetime.today()/date.today() を直接参照せず、引数で target_date を受け取る設計です。ETL やスコアリングで未来データを参照しないよう留意しています。
- OpenAI 呼び出しのテスト: news_nlp と regime_detector のモジュールは内部で _call_openai_api を定義しており、ユニットテスト時は unittest.mock.patch で差し替えて挙動を制御できます。
- .env の自動ロード: kabusys.config はプロジェクトルートの .env → .env.local を順に読み込みます。既存 OS 環境変数は保護され、.env.local は上書き可能です。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants クライアント: 内部で固定間隔レートリミッター（120 req/min）やリトライ、401 のトークン自動リフレッシュを実装しています。ページネーション対応です。
- NewsCollector は SSRF 対策、gzip サイズチェック、XML パースの安全化（defusedxml）など堅牢化しています。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント付与（score_news）
    - regime_detector.py     -- マクロ + MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - news_collector.py      -- RSS 取得・前処理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py -- 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     -- momentum / value / volatility の計算
    - feature_exploration.py -- 将来リターン・IC・統計サマリー等

運用上のヒント
-------------
- 環境区分: settings.env で development / paper_trading / live を切り替えます。live 実行時は特に設定値・ログレベルの管理を厳重にしてください。
- トークン管理: J-Quants リフレッシュトークンや OpenAI キーは安全に管理し、CI/CD に埋め込まないでください。ローテーションと最小権限を推奨します。
- 部分失敗の取り扱い: ETL は個々のステップでエラーを捕捉して継続し、ETLResult に issues や errors を蓄積します。呼び出し側で適切に判断してください。
- DuckDB のスキーマ管理: ETL / audit の各関数は既存スキーマに対して冪等性を保つよう設計されていますが、マイグレーション管理は別途必要です。

ライセンス・その他
------------------
この README はコードベースの説明と利用手順をまとめたものです。実際に運用する際は pyproject.toml / LICENSE / contribution ガイドライン等をプロジェクトルートで確認してください。

お問い合わせ
--------------
実装や利用に関する質問・不明点があれば、ソースの該当モジュール（kabusys.config / kabusys.data.jquants_client / kabusys.ai.news_nlp など）を参照した上でご連絡ください。