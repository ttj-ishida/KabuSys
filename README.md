KabuSys
======

日本株向けのデータパイプライン／リサーチ／AI支援を備えた自動売買基盤のライブラリ群です。DuckDB をデータ層に使い、J‑Quants API や OpenAI を組み合わせて市場データ取得・品質チェック・特徴量算出・ニュースセンチメント評価・市場レジーム判定・監査ログ（トレーサビリティ）を提供します。

主な特徴
-------
- ETL（J-Quants → DuckDB）:
  - 日次差分取得（株価日足・財務・市場カレンダー）
  - 冪等保存（ON CONFLICT / DO UPDATE）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集・NLP:
  - RSS 収集・前処理（SSRF 保護、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアの算出（news_nlp）
  - マクロニュースとETF MA乖離を合わせた市場レジーム判定（regime_detector）
- リサーチ / ファクター:
  - モメンタム/バリュー/ボラティリティ等の定量ファクター計算
  - 将来リターン、IC、ファクター統計サマリー
  - クロスセクション Z スコア正規化ユーティリティ
- データ・カレンダー管理:
  - JPX カレンダーの差分取得と営業日判定ユーティリティ
- 監査ログ（audit）:
  - signal → order_request → execution までのトレーサビリティ用テーブル定義・初期化
- 実運用に耐える設計方針:
  - Look‑ahead bias を避ける（内部で datetime.today() に依存しない）
  - API エラーに対するリトライ / バックオフ / フェイルセーフ
  - SQL のパラメータバインド使用、DB 操作の冪等性を重視

必要条件
-------
- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで多くの処理を実装）
※ 実プロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください。

セットアップ手順
-------------
1. リポジトリをクローンして仮想環境を用意:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストール:
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトが配布されていれば: pip install -e .）

3. 環境変数設定:
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須/推奨環境変数（一例）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API 用パスワード（発注・実行系を使う場合）
- OPENAI_API_KEY (AI 機能を使う場合必須): OpenAI API キー（score_news/score_regime など）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知機能を使う場合)
- DUCKDB_PATH (省略時 data/kabusys.duckdb)
- SQLITE_PATH (省略時 data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値など（省略可）

例（.env の最小例）
- .env:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_password
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（主要 API）
----------------

基本: settings の利用
- from kabusys.config import settings
- settings.jquants_refresh_token / settings.duckdb_path / settings.env 等で設定値にアクセス可能
- パッケージはプロジェクトルートの .env / .env.local を自動ロードします（無効化可）

DuckDB 接続の例
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行（株価・財務・カレンダーの差分取得）
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=some_date)
- result は ETLResult（フェッチ数・保存数・quality_issues 等を含む）

個別 ETL を呼ぶ例
- from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
- fetched, saved = run_prices_etl(conn, target_date=some_date)
- fetched, saved = run_financials_etl(conn, target_date=some_date)
- fetched, saved = run_calendar_etl(conn, target_date=some_date)

ニュースセンチメント（銘柄別）スコア算出
- from kabusys.ai.news_nlp import score_news
- # OPENAI_API_KEY を環境変数に設定しておくか api_key を渡す
- n = score_news(conn, target_date=some_date)  # 書き込み件数を返す

市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=some_date)  # market_regime テーブルに書き込む

監査ログ（監査DB の初期化）
- from kabusys.data.audit import init_audit_db, init_audit_schema
- audit_conn = init_audit_db(settings.duckdb_path)  # ファイル作成・テーブル初期化
- または既存 conn に対して init_audit_schema(conn, transactional=True)

リサーチ / ファクター計算例
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- mom = calc_momentum(conn, target_date=some_date)
- vol = calc_volatility(conn, target_date=some_date)
- val = calc_value(conn, target_date=some_date)
- from kabusys.research import zscore_normalize, calc_forward_returns, calc_ic, factor_summary

ニュース収集（RSS）
- kabusys.data.news_collector.fetch_rss(url, source)
- preprocessing や検証（SSRF 対策、トラッキング除去）済みで raw_news に保存する処理を組み合わせて使います。

ログ・運用
- settings.log_level を参照してログレベルを制御
- KABUSYS_ENV により開発/紙取引/本番の挙動（フラグ）を分けられる
- ETL と AI 呼び出しはリトライやフォールバック（API 失敗時は安全側の値で継続）を備えています

設計上の注意点
-------------
- 多くの処理は「Look‑ahead bias（未来情報参照）」を避ける実装方針です。内部で date/today を勝手に参照することは避け、呼び出し側で target_date を明示してください。
- OpenAI / J-Quants API 呼び出しはリトライ・バックオフ・限度のある失敗処理を行いますが、API キー・レート制限等は運用側でも把握してください。
- DuckDB の executemany に空リストを与えると問題になるバージョンがあるため、内部実装では空チェックを行っています。

ディレクトリ構成（主なファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / .env 読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py                  -- 銘柄別ニュースセンチメント算出（score_news）
  - regime_detector.py           -- マクロ+ETF MA200 で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント（取得・保存）
  - pipeline.py                  -- ETL パイプライン (run_daily_etl 等)
  - etl.py                       -- ETLResult 再エクスポート
  - calendar_management.py       -- 市場カレンダー管理・営業日ヘルパ
  - news_collector.py            -- RSS 収集・前処理
  - quality.py                   -- 品質チェック
  - stats.py                     -- zscore_normalize 等ユーティリティ
  - audit.py                     -- 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py           -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py       -- calc_forward_returns / calc_ic / factor_summary / rank

ライセンス・貢献
----------------
本 README はコードベースからの抽出に基づき作成しています。実プロジェクトでは LICENSE ファイル、コントリビューションガイドライン (CONTRIBUTING.md)、および pyproject.toml / requirements.txt を追記してください。

補足（トラブルシューティング）
------------------------------
- .env の自動読み込みが働かない場合:
  - プロジェクトルートの判定は .git または pyproject.toml の存在に依存します。パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて手動ロードしてください。
- OpenAI 呼び出しで JSON パースに失敗した場合:
  - モジュールは失敗時に安全側のスコア（0.0）で継続する設計です。詳細はログを確認してください。
- DuckDB のバージョンにより executemany の挙動が異なるため、空のバルク挿入を避ける実装になっています。

必要であれば、利用シナリオ（ETL の Cron 設定例、発注系の安全対策、モニタリング設定ファイル例など）を追加で README にまとめます。どのトピックを優先してほしいか教えてください。