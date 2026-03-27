# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買支援ライブラリです。J-Quants や RSS、OpenAI（LLM）など外部データを取り込み、ETL、データ品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログ（発注追跡）などを提供します。

注意: この README はソースコード（src/kabusys）を元に作成しています。実運用には各種 API キーや DB パスの設定が必要です。各モジュールは Look-ahead bias（将来情報流入）を避ける設計を意識して実装されています。

主な特長
- J-Quants API 経由で株価（日足）・財務データ・JPX カレンダーを差分取得（ページネーション・レートリミット・トークン自動リフレッシュ対応）
- DuckDB を用いた ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）とニュースごとの銘柄紐付け（raw_news, news_symbols）
- ニュースを LLM（gpt-4o-mini）でセンチメント化し銘柄別 ai_scores を生成（バッチ・リトライ・レスポンス検証）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ（Zスコア、IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ生成・初期化ユーティリティ

機能一覧
- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_* / get_id_token）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS の取得・前処理・raw_news への保存補助）
  - 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: LLM で銘柄ごとのセンチメントを ai_scores テーブルへ）
  - マクロレジーム判定（score_regime: ETF1321 MA200 とマクロニュースセンチメントを合成）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析・IC・将来リターン計算（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数の自動ロード（.env / .env.local）と Settings クラス（各種必須設定をプロパティで提供）
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10+ を推奨（typing と一部 API を利用）

2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （ネット接続・システム環境に応じて他依存がある場合があります）
   - 例: pip install duckdb openai defusedxml

3. ソースコードを配置
   - レポジトリルートが .git または pyproject.toml を持つことを想定（config.py の自動 .env ロードでルート検出に使用）

4. 環境変数 / .env の準備
   - 必須環境変数（代表）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime に使用）
     - KABU_API_PASSWORD      — kabuステーション API パスワード（発注機能有りの場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用（存在する場合）
   - DB パス（任意デフォルト）
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
   - 環境フラグ
     - KABUSYS_ENV (development / paper_trading / live) — 動作環境
     - LOG_LEVEL (DEBUG/INFO/...)
   - 自動ロード:
     - ルートに .env / .env.local があれば自動で読み込み（OS 環境 > .env.local > .env の優先度）
     - 自動ロードを止める場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. サンプル .env（.env.example の例）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（コード例）
- 共通: Settings を介して設定取得
  from kabusys.config import settings
  print(settings.duckdb_path)

- DuckDB 接続と日次 ETL 実行
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（LLM）で銘柄スコア作成
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # api_key に OPENAI_API_KEY を渡すか省略して環境変数を使用
  print(f"scored {count} codes")

- マーケットレジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると env OPENAI_API_KEY を参照

- 監査ログ DB の初期化（監査専用 DB）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., "ma200_dev": ...}, ...]

- データ品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点 / 設計上の留意事項
- Look-ahead bias を避けるため、各処理は内部で date.today() を参照するコードを最小化しており、関数に target_date を明示的に渡すことを推奨します。
- OpenAI 呼び出しはリトライ・バックオフを実装していますが、API キーのレート制限やコストに注意してください。
- J-Quants API はレート制限（120 req/min）を守るため内部でスロットリングしています。
- DuckDB の executemany や型バインドの制約に配慮した実装になっています（空の executemany を避ける等）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを抑制できます。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETLResult 再エクスポート
    - calendar_management.py       — マーケットカレンダー管理
    - news_collector.py            — RSS 収集 / 前処理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化（init_audit_schema/init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー

開発・テスト
- 自動環境読み込みを無効化してテストしたい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI や J-Quants の外部アクセスをテストで差し替える場合は、各モジュール内の _call_openai_api などをモックしてシミュレートできます（ソース内にモック想定コメントあり）。

最後に
- 本リポジトリはデータ取得・処理・解析・監査ログ生成までの基盤を提供します。運用時は API キー管理、発注ロジックのリスク管理、監査・ログ保存ポリシー等を整備した上でご利用ください。

もし README に追記してほしい実行スクリプト例（cron ジョブ、systemd ユニット、Dockerfile など）や .env.example を具体化したい場合は、目的に応じて例を作成しますので教えてください。