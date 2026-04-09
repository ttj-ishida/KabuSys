# KabuSys

バージョン: 0.1.0

日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント分析）、ファクター計算・リサーチ、取引監査ログ（DuckDB ベース）など、自動売買システムの基盤的処理を提供します。

概要
- ETL: J-Quants API から株価（OHLCV）、財務情報、JPX カレンダーを差分取得して DuckDB に保存
- ニュース収集: RSS フィードから記事を安全に取得し raw_news に保存
- ニュースNLP: OpenAI（gpt-4o-mini）で記事を評価して銘柄ごとの ai_score を生成
- レジーム判定: ETF（1321）の 200 日 MA とマクロニュースの LLM センチメントを合成して市場レジームを判定
- 研究用ユーティリティ: ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算等
- 監査ログ: シグナル → 発注 → 約定のトレーサビリティを保持する監査テーブル群を DuckDB に初期化

主な機能（モジュール別）
- kabusys.config: .env / 環境変数管理、設定オブジェクト（settings）
- kabusys.data.jquants_client: J-Quants API クライアント、差分取得・保存関数（save_*）
- kabusys.data.pipeline / etl: 日次 ETL パイプライン実行（run_daily_etl 等）
- kabusys.data.news_collector: RSS 取得、安全対策（SSRF 対応）と前処理
- kabusys.ai.news_nlp: ニュースのバッチセンチメント分析（score_news）
- kabusys.ai.regime_detector: 市場レジーム判定（score_regime）
- kabusys.research: ファクター計算・特徴量解析（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等）
- kabusys.data.audit: 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- kabusys.data.stats: 汎用統計ユーティリティ（zscore_normalize）

セットアップ手順（ローカル開発用）
1. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型記法（|）を利用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb openai defusedxml
   - （開発用に logging 等の追加パッケージを使う場合は追加でインストール）

4. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（kabusys.config がプロジェクトルートを検出した場合）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN  （必須） — J-Quants リフレッシュトークン
     - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD      — kabuステーション API パスワード（注文連携で使用）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE        — paper_trading 時のモック約定挙動（instant|partial|never|reject、デフォルト "instant"）
     - KABUSYS_ENV            — 実行環境（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL              — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
     - PID_FILE_PATH / KILL_FLAG_PATH ...（監視・実行制御用）

5. データディレクトリ作成
   - デフォルトの DB 保存先等の親ディレクトリを作成しておくと安全です:
     - mkdir -p data

基本的な使い方（Python から呼び出す例）
- DuckDB 接続を作って ETL を実行する
  - import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日に対する ETL

- ニュースのセンチメントスコアを生成（score_news）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 19))  # 前日 15:00 JST ～ 当日 08:30 JST のウィンドウでスコア生成

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 19))

- 監査 DB 初期化（監査ログ専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" でメモリ DB も可

- 研究用関数の利用例
  - from kabusys.research.factor_research import calc_momentum
    result = calc_momentum(conn, target_date=date(2026,3,19))

環境設定の注意点
- .env の自動ロード順序: OS 環境変数 > .env.local > .env
- テストや特殊用途で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください
- settings クラスが必須とする値（JQUANTS_REFRESH_TOKEN など）が未設定だと ValueError が発生します

運用上の注意
- J-Quants API のレート制限（120 req/min）に対応するため、クライアントは内部でスロットリングを行います
- OpenAI 呼び出しはリトライ／バックオフを備えていますが、API クォータに注意してください
- ETL は差分更新を行い、DB への保存は冪等（ON CONFLICT DO UPDATE）を前提としています
- ニュース収集モジュールは SSRF 対策・トラッキングパラメータ除去・XML の安全パース（defusedxml）を行います
- DuckDB に対する executemany 空リストの扱いなど、バージョン差異に起因する注意点があります（コード内に回避処理あり）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py  — パッケージ情報（__version__ = "0.1.0"）
  - config.py    — 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント分析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py        — ETL パイプライン（run_daily_etl など）
    - etl.py             — ETLResult の再エクスポート
    - news_collector.py  — RSS 取得・前処理
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py         — データ品質チェック（run_all_checks 等）
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリー等
  - ai/、research/、data/ 以下にさらに補助関数・定数が実装されています

開発・テスト
- モジュール内部で外部 API 呼び出しを行う関数は、テストのために呼び出し点を差し替えられる設計（例: news_nlp._call_openai_api や news_collector._urlopen など）になっています
- 環境変数自動ロードはテスト環境で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

よくある使用シナリオ（短いワーキングフロー）
1. 環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を準備
2. DuckDB のファイルパス（settings.duckdb_path の親ディレクトリ）を作成
3. 日次 ETL を実行して prices / financials / market_calendar を取得
4. ニュース収集ジョブで raw_news を蓄積
5. score_news で ai_scores を生成
6. score_regime で market_regime を更新
7. research モジュールでファクター研究を行い戦略に反映
8. 監査用 DB を初期化してシグナル・発注・約定の追跡を開始

その他
- コード中に多くの設計方針（Look-ahead bias 回避、冪等性、フェイルセーフの原則）が書かれており、バックテストや実運用に配慮した実装になっています。
- README に記載のない実行スクリプトや CI/CD、pyproject.toml 等は本リポジトリの別箇所にあるかもしれません。導入先のプロジェクトルールに従って適宜調整してください。

フィードバック / 開発に関する注記
- 新しい機能やバグ修正の際は、外部 API 呼び出し点をモック可能にしてユニットテストを充実させることを推奨します
- OpenAI / J-Quants の API 仕様変更があった場合、該当クライアント（jquants_client.py / ai/*.py）を更新してください

以上。README に追加したい具体的な実行例や CI 設定、サンプル .env.example の雛形が必要であれば教えてください。