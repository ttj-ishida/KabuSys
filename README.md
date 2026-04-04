KabuSys
======

日本株向けのデータプラットフォーム／自動売買支援ライブラリ。  
データ収集（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなど、売買戦略の開発・運用に必要なユーティリティ群を提供します。

主な目的
- J-Quants からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と LLM を使った銘柄センチメント付与
- 市場レジーム判定（ETF + マクロニュース）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- DuckDB を用いたデータ保存・監査ログ（冪等設計）

機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート基準）、環境変数必須チェック
  - important settings: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, 等
- データ ETL（kabusys.data.pipeline / jquants_client）
  - fetch / save（raw_prices, raw_financials, market_calendar）
  - 差分取得、ページネーション、レートリミット、トークン自動リフレッシュ、冪等保存
  - run_daily_etl でカレンダー→株価→財務→品質チェックを順次実行
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合 等を検出し QualityIssue を返す
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、記事重複排除（ID=URLハッシュ）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント評価し ai_scores に書込み
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の MA200 乖離 + マクロニュースの LLM センチメントを合成して
    daily market_regime を計算・保存
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブル定義と初期化
- 研究（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic 等
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

セットアップ手順
1. Python 環境
   - 推奨: Python 3.10+（typing の union 表記等を利用）
2. リポジトリをチェックアウト
   - プロジェクトルートに pyproject.toml / .git がある想定
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （必要に応じて他のユーティリティを追加）
4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - OPENAI_API_KEY (LLM を使う機能で必須: news_nlp/regime_detector)
     - KABU_API_PASSWORD (kabuステーション API 用)
     - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (既定: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB、既定: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
5. DB 初期化（監査 DB など）
   - 監査ログ初期化例（DuckDB ファイルを作成してスキーマを適用）:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

基本的な使い方（コード例）
- DuckDB 接続を作り、日次 ETL を実行する
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントをスコアリングして ai_scores に保存する
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
    print("書き込み銘柄数:", n_written)

- 市場レジーム判定を実行する
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB を初期化する
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # ファイルとテーブルを作成

設定と振る舞いの注意点
- .env の自動読込順序: OS 環境変数 > .env.local > .env
  - プロジェクトルートは __file__ を基点に .git / pyproject.toml を探索して決定
- 環境変数の必須チェック: Settings クラスの _require() が未設定時に ValueError を投げます
- LLM 呼び出し（OpenAI）
  - news_nlp と regime_detector は gpt-4o-mini を想定し JSON Mode（厳密な JSON 出力）を期待
  - OPENAI_API_KEY が必要。api_key を明示的に渡すことも可能
  - API 呼び出し失敗時はフェイルセーフとして部分スコアを 0 にする等の設計
- J-Quants クライアント
  - レート制限（120 req/min）を守る実装、リトライ、401 時のトークンリフレッシュ等を含む
  - fetch + save 関数は冪等（ON CONFLICT DO UPDATE）なので安全に再実行可能
- 日付の扱い
  - ルックアヘッドバイアス防止のため、内部関数は datetime.today() や date.today() を参照しない設計を心がけています（target_date を明示することで再現性を担保）

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                          # 環境変数 / 設定
    - ai/
      - __init__.py
      - news_nlp.py                      # ニュースNLP（score_news 等）
      - regime_detector.py               # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py                # J-Quants API クライアント + save_* 関数
      - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
      - etl.py                           # ETLResult 再エクスポート
      - news_collector.py                # RSS ニュース収集
      - quality.py                       # 品質チェック
      - stats.py                         # zscore_normalize 等
      - calendar_management.py           # 市場カレンダー管理（is_trading_day 等）
      - audit.py                         # 監査ログテーブル初期化
    - research/
      - __init__.py
      - factor_research.py               # calc_momentum / calc_value / calc_volatility
      - feature_exploration.py           # calc_forward_returns / calc_ic / factor_summary / rank
    - (その他: strategy, execution, monitoring のプレースホルダあり)
- pyproject.toml (想定)
- .env / .env.local (ユーザが配置)

開発者向け補足
- テスト時に .env 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出し部分や HTTP の低レイヤは unittest.mock.patch で差し替え可能に設計されています（テスト容易性を意識）
- DuckDB の executemany はバージョン差異があるため、コード内で空パラメータの扱いに注意があります（既に対策済み）

ライセンス / 責務
- 本 README ではコード仕様の概要を記載しています。実運用を行う場合は API キー・資金管理・注文ロジック・証券会社 API の動作を十分にテストし、法令・各種規約を遵守してください。

フィードバック / 追加情報
- 各モジュールには docstring に設計方針・処理フローが記載されています。機能追加や挙動確認は各ファイルの docstring を参照してください。必要であれば README に具体的な実行スクリプト例や CI 設定も追記できます。