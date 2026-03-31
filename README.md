KabuSys
=======

日本株のデータプラットフォーム／リサーチ／AI支援を想定した軽量ライブラリ群です。ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、ファクター計算・特徴量探索、監査ログ（約定トレーサビリティ）などを提供します。

主な目的
- J-Quants API からの差分 ETL と品質チェック
- RSS ニュース収集と LLM による銘柄別センチメント算出
- 市場レジーム判定（ETF MA + マクロニュース × LLM）
- 研究用のファクター計算・統計ユーティリティ
- 発注／約定フローの監査ログ用スキーマ（DuckDB）

機能一覧
- 環境設定読み込み（.env / .env.local / OS 環境変数、auto-load 対応）
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系（DuckDB への冪等保存）
  - レートリミッタ、リトライ、401 自動リフレッシュ等の堅牢性
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult で返却、品質チェック統合
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
- ニュース収集（RSS）と前処理、安全対策（SSRF/サイズ制限等）
- ニュース NLP（gpt-4o-mini を用いた JSON Mode の呼び出し）
  - score_news(conn, target_date, api_key=None) → ai_scores に保存
- 市場レジーム検出（ETF 1321 の MA200 乖離 + マクロニュース LLM）
  - score_regime(conn, target_date, api_key=None) → market_regime に保存
- 研究モジュール
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（DuckDB に監査テーブルを作成）
- 汎用統計ユーティリティ（z-score 正規化 等）

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo_url>
2. Python 仮想環境作成（例: Python 3.10+ を推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt や pyproject.toml があれば pip install -e . を使用）
   - 例: pip install -e .

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（使用する場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）。デフォルト "INFO"
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

.env 自動ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探して、.env（override=False）→ .env.local（override=True）の順で自動ロードします。
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env.example
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb

使い方（サンプル）
- DuckDB 接続を開いて ETL を実行する（最小例）:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースのセンチメントを計算（OpenAI API キーが必要）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} ai_scores")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化:

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # 生成された conn_audit に対して監査データを挿入・参照できる

- マーケットカレンダー・ユーティリティ:

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trading = is_trading_day(conn, date(2026, 03, 20))
  next_bd = next_trading_day(conn, date(2026, 03, 20))

注意点・設計方針のハイライト
- ルックアヘッドバイアス防止:
  - 多くのモジュールは datetime.today()/date.today() を内部で参照しないか、明示的に target_date を受け取る設計になっています。
  - ETL / ニュース / レジーム判定は target_date を外部から与えることが可能です。
- 冪等性:
  - DuckDB へは ON CONFLICT DO UPDATE / INSERT … DO UPDATE を用い冪等保存を実現しています。
- フェイルセーフ:
  - LLM/API エラー時はできる限り処理を継続（ゼロスコア或いはスキップ）し、致命的な例外は明示的に上位へ伝搬します。
- セキュリティ対策:
  - RSS収集は SSRF 対策・レスポンスサイズ上限・gzip 解凍上限等を実装。
  - J-Quants クライアントはレート制御および 401 の自動リフレッシュを実装。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                              -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                           -- ニュースセンチメント算出（score_news）
    - regime_detector.py                    -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                     -- J-Quants API クライアント / 保存ロジック
    - pipeline.py                           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                                -- ETLResult エクスポート
    - calendar_management.py                -- マーケットカレンダー管理（営業日等）
    - news_collector.py                     -- RSS 収集
    - quality.py                            -- データ品質チェック
    - stats.py                              -- 統計ユーティリティ（zscore）
    - audit.py                              -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                    -- momentum/value/volatility 等
    - feature_exploration.py                -- forward returns / IC / rank / summary
  - ai、data、research 以下の各モジュールには詳細な docstring と処理フロー説明があります。

依存関係（主なもの）
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで動く箇所も多く、追加の heavy な deps はない設計）

よくある運用フロー例
- 夜間バッチ（cron）:
  1. run_daily_etl を呼んでデータを更新（DuckDB に保存）
  2. score_news を呼び、AI スコアを生成・保存
  3. score_regime を呼び、市場レジームを更新
  4. 監視・通知（Slack 連携は別モジュールで実装可）

追加情報 / テスト
- 自動ロードされる .env の振る舞いをテスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はテスト容易性のため _call_openai_api をパッチして差し替え可能です（unittest.mock.patch）。

お問い合わせ・貢献
- バグ報告・機能提案は Issue を作成してください。Pull Request は歓迎します。コードベースには関数ごとに詳細な docstring があるため、それに従った実装・テストをお願いします。

以上が本リポジトリの README（概要・セットアップ・使い方・構成）です。必要であれば「.env.example の完全なテンプレート」や「cron での実行例」「簡単なスクリプトテンプレート」など追記します。どの情報を詳細化しますか？