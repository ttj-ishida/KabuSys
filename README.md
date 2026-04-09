KabuSys — 日本株自動売買 / データプラットフォーム (README 日本語)

概要
- KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買基盤の骨格ライブラリです。
- DuckDB をデータ層に使い、J-Quants API からの ETL、ニュース収集、ニュースの LLM ベース分析、マーケットカレンダー管理、ファクター計算、監査ログ（オーディット）などを提供します。
- 設計上のポイント: ルックアヘッドバイアス回避、冪等性、堅牢な API リトライ・レート制御、明確な品質チェック、テスト容易性を重視しています。

主な機能一覧
- 環境設定管理
  - .env 自動ロード（プロジェクトルートを .git または pyproject.toml から検出）
  - 必須設定の取得とバリデーション（kabusys.config.settings）
- データ取得（J-Quants）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - RateLimiter、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（save_*）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult で返却
- ニュース収集
  - RSS フィード取得（SSRF 対策・リダイレクトチェック・トラッキング除去）
  - テキスト前処理、記事 ID は正規化 URL の SHA-256（先頭32文字）
- ニュース NLP（LLM）
  - score_news: 銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores に保存
  - calc_news_window（前日 15:00 JST 〜 当日 08:30 JST のウィンドウ）
- レジーム判定（市場センチメント）
  - score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime を作成
- リサーチ / ファクター
  - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials ベース）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize（統計ユーティリティ）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（J-Quants から差分取得して market_calendar を更新）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db：signal_events / order_requests / executions テーブルの作成・初期化
  - 発注トレーサビリティ（UUID ベース、冪等キー、UTC タイムスタンプ）
- データ品質チェック（quality モジュール）
  - run_all_checks により複数チェックをまとめて実行

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある想定:
     - pip install -e .
     - または pip install -r requirements.txt
   - 必要な外部依存例:
     - duckdb, openai, defusedxml, （他に必要であれば requests 等）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を置くと自動ロードされます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 最低限設定すべき環境変数（.env に記載例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token   (必須)
     - KABU_API_PASSWORD=your_kabu_api_password           (必須)
     - OPENAI_API_KEY=your_openai_api_key                 (LLM 機能を使う場合必須)
     - KABUSYS_ENV=development|paper_trading|live         (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...                           (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb                    (デフォルト)
     - SQLITE_PATH=data/monitoring.db
     - PAPER_FILL_MODE=instant|partial|never|reject       (paper trading 用)
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=... (任意)
     - LINE_USER_ID=... (任意)

使い方（主要な例）
- 設定取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.duckdb_path などでアクセス

- DuckDB 接続例
  - import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行例
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニューススコアリング（score_news）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> OPENAI_API_KEY を使う
    print(f"scored {count} codes")

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- マーケットカレンダー判定
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
    is_trade = is_trading_day(conn, date(2026,3,20))
    nxt = next_trading_day(conn, date(2026,3,20))

- 監査ログ初期化（監査用 DuckDB DB を別に作る場合）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- J-Quants 低レベル利用例
  - from kabusys.data import jquants_client as jq
    token = jq.get_id_token()
    quotes = jq.fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
    saved = jq.save_daily_quotes(conn, quotes)

注意点 / 運用メモ
- LLM 呼び出し（score_news / score_regime）は OpenAI API キーが必要。環境変数 OPENAI_API_KEY または引数 api_key を指定してください。
- .env の自動ロードはプロジェクトルート検出に基づくため、テストや一時的実行では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと静かに無効化できます。
- ETL は部分失敗でも他処理を継続する設計です。ETLResult に errors / quality_issues が格納されますので呼び出し側で判定してください。
- DuckDB の executemany は空リストを渡せないバージョン依存があるため、コード内で空チェックを行っています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py               (パッケージ初期化)
  - config.py                 (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py             (ニュース NLP / score_news)
    - regime_detector.py      (市場レジーム判定 / score_regime)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント + save_* 関数)
    - pipeline.py             (ETL パイプライン / run_daily_etl 等)
    - etl.py                  (ETLResult 再エクスポート)
    - news_collector.py       (RSS 取得 / 前処理)
    - calendar_management.py  (マーケットカレンダー判定 / calendar_update_job)
    - quality.py              (データ品質チェック)
    - stats.py                (統計ユーティリティ / zscore_normalize)
    - audit.py                (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py      (モメンタム / バリュー / ボラティリティ)
    - feature_exploration.py  (forward returns / IC / summary / rank)
  - ai/、data/、research/ の内部は更に細分化された関数群とユーティリティで構成されています。

開発・テスト
- ユニットテストでは外部 API（OpenAI / J-Quants / HTTP）呼び出しをモックすることを想定しています（モジュール内で呼び出しを注入・パッチ可能な設計）。
- 環境変数を擬似的に与える場合は .env を用意するか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にしてテスト中に os.environ を直接操作してください。

ライセンス / 貢献
- （ここにプロジェクトのライセンスや貢献方法を追記してください）

以上。必要であれば「具体的な .env.example」や「よく使う CLI スクリプト例（ETL を cron 化する方法など）」を追加で用意します。どの部分を詳しく書きたいか指示してください。