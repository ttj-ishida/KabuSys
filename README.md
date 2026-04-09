# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。J-Quants からの市場データ取得、ニュースの収集・NLP スコアリング、ファクター計算、ETL パイプライン、監査ログ（オーダー・約定のトレーサビリティ）などを含むモジュール群を提供します。

主な用途例:
- 日次 ETL：J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存
- ニュースセンチメント：OpenAI を用いた銘柄／マクロニュースのスコアリング
- ファクター計算・研究：モメンタム・バリュー・ボラティリティ等の計算、IC / 統計分析
- 監査ログ：シグナル→発注→約定の監査テーブル初期化

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理（.env 自動読み込み、上書き制御、必須チェック）
- J-Quants API クライアント
  - 日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集（RSS）および前処理（URL 正規化・SSRF 対策等）
- OpenAI を使った NLP
  - 銘柄ごとのニュースセンチメント（news_nlp.score_news）
  - マクロ × ETF(1321) の MA200 乖離を使った市場レジーム判定（regime_detector.score_regime）
- リサーチ用ユーティリティ
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算・IC（情報係数）計算・統計サマリー
- 監査ログ（audit）: signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型注釈で | 演算子や型ヒントを使用）

1. リポジトリをクローン（またはパッケージをプロジェクトに追加）
   git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要な Python パッケージをインストール
   pip install duckdb openai defusedxml

   ※ 実行環境や CI では追加パッケージ（logging 設定、依存関係管理用の requirements.txt）を用意してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で使用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（注文周りで使用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: paper trading の埋め合わせモード（instant|partial|never|reject）
     - その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, KABUSYS_ENV（development/paper_trading/live）など

   例 `.env`（例示）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（主要なユースケース例）

以下はいくつかの代表的な使い方のサンプルです。実運用時はログやエラーハンドリングを整備してください。

- DuckDB 接続を作って日次 ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- OpenAI を使ったニューススコアリング（銘柄ごと）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {n_written}")

  注意: OPENAI_API_KEY は環境変数または api_key 引数で渡す必要があります。

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DuckDB を初期化する
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions 等のテーブルが作成されます

- 環境設定をコードから参照する
  from kabusys.config import settings
  print(settings.kabu_api_base_url)
  print(settings.is_paper)

---

## 主要モジュールと API（簡易リファレンス）

- kabusys.config
  - settings: Settings インスタンス（環境変数をプロパティ経由で取得）
  - 自動 .env ロード: プロジェクトルートの `.env` / `.env.local`（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（トークン取得）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult クラス

- kabusys.data.news_collector
  - fetch_rss(url, source): RSS から NewsArticle リストを取得

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None): ai_scores テーブルへ書き込み

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None): market_regime テーブルへ書き込み

- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats 経由）

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date, ...): データ品質チェックを実行

---

## 動作上の注意点 / 設計方針の要約

- Look-ahead bias の防止:
  - 各モジュールは内部で datetime.today() 等を不必要に参照しないよう設計（target_date を明示的に渡す）。
  - DB クエリは target_date より前のデータのみを参照するなどの対策が施されています。

- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は致命的に落とさずフォールバックする箇所が多くあります（例: マクロセンチメントが取得できない場合は 0.0 を使う等）。
  - ETL は各ステップを個別にエラーハンドリングし、1 ステップ失敗でも他の処理を継続します。

- 冪等性:
  - データ保存関数は ON CONFLICT DO UPDATE を用い、再実行可能な差分 ETL を想定しています。
  - 監査ログでは order_request_id / broker_execution_id 等を冪等キーとして扱います。

- セキュリティ:
  - ニュース収集では SSRF 対策（リダイレクト先チェック・プライベート IP ブロック）や defusedxml を使用して XML 攻撃を軽減。
  - API 呼び出しではレート制限・リトライ・トークンの自動リフレッシュを実装。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（銘柄別）
    - regime_detector.py            -- マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch / save）
    - pipeline.py                   -- ETL パイプラインと run_daily_etl
    - etl.py                        -- ETLResult の再エクスポート
    - news_collector.py             -- RSS 収集・前処理
    - calendar_management.py        -- 市場カレンダー管理（営業日判定等）
    - stats.py                      -- 統計ユーティリティ（zscore_normalize 等）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py            -- Momentum / Value / Volatility の計算
    - feature_exploration.py        -- 将来リターン、IC、統計サマリー

---

## 推奨ワークフロー（例）

1. .env を作成して J-Quants / OpenAI のキーを配置
2. DuckDB データベースを用意（自動作成されることが多い）
3. 初回: ETL を実行して過去データを取得
   - python スクリプトから run_daily_etl を呼び出す（backfill を使って過去分を遡る）
4. ニュース収集 / スコアリングを定期実行（cron / Airflow 等）
5. 監査ログ DB を初期化して、発注・約定イベントを記録
6. リサーチ環境でファクター計算・IC 検証を行う

---

## 参考: よく使うコードスニペット

- settings の参照
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.paper_fill_mode)

- ETL を定期実行する最簡単な cron スクリプト（疑似例）
  # daily_etl.py
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

---

もし README に加えたい内容（例: CI / テスト方法、依存関係の固定ファイル、具体的な SQL スキーマ定義、運用時の監視設定テンプレート等）があれば教えてください。必要に応じてサンプル .env.example やデプロイ手順を追記します。