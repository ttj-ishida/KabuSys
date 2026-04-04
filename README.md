KabuSys
=======

KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI支援市場判定・監査ログ・ETL・ニュース収集を含む自動売買／リサーチ基盤ライブラリです。DuckDB をローカル DB として利用し、J-Quants / JPEX（マーケットカレンダー）や OpenAI（LLM）を用いた処理を行います。

主な目的
- データの差分 ETL（株価・財務・カレンダー）
- ニュース収集と LLM による銘柄／マクロのセンチメント評価
- ファクター計算・特徴量探索（研究用）
- 市場レジーム判定（MA + マクロセンチメントの合成）
- 監査ログ（シグナル→約定のトレース）用スキーマ管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
- 環境設定管理（.env 自動ロード / settings API）
- J-Quants クライアント（認証、自動リフレッシュ、レート制御、ページネーション）
- ETL パイプライン（run_daily_etl / 個別 ETL）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース収集（RSS 取得、SSRF 対策、正規化、raw_news 保存補助）
- ニュース NLP（銘柄ごとの ai_score、LLM 呼び出しのリトライ・バリデーション）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
- 研究モジュール（ファクター計算・forward returns・IC・統計サマリ）
- 監査（audit）テーブル初期化ユーティリティ（init_audit_db / init_audit_schema）
- ユーティリティ（統計関数、カレンダー管理、パイプライン結果 ETLResult）

セットアップ手順（ローカル開発）
- 前提
  - Python 3.10+（typing | union types が利用されています）
  - DuckDB（Pythonパッケージ）
  - OpenAI（openai Python SDK）
  - defusedxml（RSS 安全パース）
  - ネットワークアクセス（J-Quants API / RSS / OpenAI）
- インストール（例: pip で editable install）
  1. リポジトリルートで仮想環境を作成・有効化（推奨）
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
  2. 必要パッケージをインストール（プロジェクトに requirements.txt が無ければ下記を例示）
     - pip install duckdb openai defusedxml
     - pip install -e .
     （src 配下がパッケージルートの場合は pip install -e . が使えます）
- 環境変数 / .env
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の存在）を基準に .env と .env.local を自動的に読み込みます（優先順: OS > .env.local > .env）。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
  - 主要な環境変数
    - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
    - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
    - OPENAI_API_KEY (LLM 呼び出しに使用。関数呼び出しで明示的に渡すことも可能)
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）
    - DUCKDB_PATH (default: data/kabusys.duckdb)
    - SQLITE_PATH (default: data/monitoring.db)
    - PID_FILE_PATH, KILL_FLAG_PATH（監視用フラグ）
    - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
    - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - サンプル (.env)（例）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
    DUCKDB_PATH=data/kabusys.duckdb
    LOG_LEVEL=INFO

使い方（主要な API / 実行例）
- 設定の利用
  from kabusys.config import settings
  settings.jquants_refresh_token  # 必須値を取得（未設定時は ValueError）

- DuckDB 接続の作成（例）
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  # result は ETLResult オブジェクト。result.to_dict() で辞書化可能。

- ニュースセンチメント（銘柄ごと）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  # api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
  # 戻り値は書き込んだ銘柄数（int）。

- 市場レジーム判定（マクロ + MA200）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  # market_regime テーブルへスコアを冪等書き込みします。

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブル・インデックスを作成し、接続を返します。

- ファクター計算（研究向け）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- カレンダー操作
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trading = is_trading_day(conn, date(2026, 3, 20))
  next_day = next_trading_day(conn, date(2026, 3, 20))

- J-Quants 直接使用（トークン取得・データ取得）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

注意点と設計方針（要点）
- ルックアヘッドバイアス対策
  - モジュール内の各関数は基本的に date 引数を受け取り、datetime.today()/date.today() を参照せずに動作する設計です。バックテストや再現性を保つためです。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）失敗時は多くの箇所で明示的フォールバック（例: macro_sentiment=0.0、処理スキップ）やリトライロジックを実装しています。
- 冪等性
  - ETL・保存処理は基本的に ON CONFLICT DO UPDATE / INSERT ... DO UPDATE で冪等に動作します（DuckDB の制約に留意）。
- セキュリティ
  - news_collector は SSRF 防止、defusedxml を用いた XML パース、レスポンスサイズ制限などを実装しています。
- レート制御
  - J-Quants クライアントは120 req/min の制約に合わせた固定間隔の RateLimiter を備えています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py            — パッケージ定義（version 等）
  - config.py              — 環境変数 / settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの LLM スコアリング（銘柄別）
    - regime_detector.py   — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py    — RSS 収集・正規化
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - quality.py           — データ品質チェック（QualityIssue 等）
    - audit.py             — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/、research/、data/ 以下に詳しい処理や設計方針の docstring を多数含みます。

運用上のヒント
- 環境分離: KABUSYS_ENV=development/paper_trading/live を設定し、ライブ環境では is_live 判定で安全チェックを追加してください。
- OpenAI 呼び出し: テストでは各モジュールの _call_openai_api を unittest.mock.patch で差し替えることで外部依存を切り離せます。
- データ品質: run_daily_etl の戻り値 ETLResult.has_quality_errors を監視してアラートを出す等の運用を推奨します。
- PID / kill フラグ: settings.pid_file_path, settings.kill_flag_path を使った単一実行や外部キルフローを用意できます。

ライセンス・貢献
- 本リポジトリのライセンスはプロジェクトルートの LICENSE を参照してください（ここでは記載がありません）。
- バグ報告や機能提案は Issue を通じて行ってください。コードスタイル・テストの追加を歓迎します。

さらに詳しく
- 各モジュールの先頭 docstring に詳細な設計意図・処理フロー・フェイルセーフ挙動が書かれています。実装や拡張を行う際は該当ファイルの docstring を必ず参照してください。

以上が KabuSys の概要と使い方の要点です。必要であれば、具体的なセットアップ手順（requirements.txt / pyproject.toml の例、Docker イメージ作成手順）、よくあるトラブルシュート、サンプルデータベース初期化スクリプトなどを追記します。どの情報を優先して補完しますか？