KabuSys — 日本株自動売買基盤（README 日本語版）
概要
本リポジトリは「KabuSys」と呼ばれる日本株向けのデータ基盤・研究・AI・監査ログ・ETL・ニュース収集・リサーチ・市場レジーム判定・監視/監査周りのユーティリティを集めた Python パッケージです。  
主要な目的は以下です。
- J-Quants API から株価・財務・カレンダーを差分 ETL で取得・保存
- RSS ベースのニュース収集と LLM（OpenAI）を用いたニュースセンチメント付与
- 銘柄ファクター計算（モメンタム・バリュー・ボラティリティ等）と探索的解析ユーティリティ
- 市場レジーム判定（ETF + マクロニュースの合成）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB に永続化
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

主な機能一覧
- data/
  - jquants_client: J-Quants API 取得／保存（差分・ページネーション・リトライ・レートリミット対応）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - news_collector: RSS 収集・前処理・DB 保存ロジック（SSRF 対策、トラッキング除去、gzip/サイズ制限）
  - calendar_management: カレンダー（market_calendar）管理と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル初期化および監査 DB 初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM でセンチメントを算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離とマクロニュース LLM を合成して market_regime を更新
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: kabusys.config (自動 .env ロード / Settings クラス)

セットアップ手順（開発環境向け）
前提: Python 3.10 以上を想定（typing の | 演算子等を使用）

1) リポジトリをクローンして仮想環境を作成
   python -m venv .venv
   source .venv/bin/activate  # (Windows) .venv\Scripts\activate

2) 必要パッケージのインストール（最低限）
   pip install duckdb openai defusedxml

   ※ 実運用では logger, requests 等の依存もあるかもしれません。プロジェクトに requirements.txt があればそれを使用してください。

3) 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env または .env.local を配置すると、kabusys.config が起動時に自動読み込みします（自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（必須／任意の区別は Settings の _require を参照してください）:
   - JQUANTS_REFRESH_TOKEN    (必須) : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD        (必須) : kabuステーション API パスワード
   - KABU_API_BASE_URL        (任意) : kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN          (必須) : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID         (必須) : Slack チャンネル ID
   - OPENAI_API_KEY           (任意) : OpenAI API キー（score_news / score_regime に渡すか env に設定）
   - DUCKDB_PATH              (任意) : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH              (任意) : SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV              (任意) : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL                (任意) : DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 .env（値はダミー）
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=~/kabusys_data/kabusys.duckdb

4) データベース初期化（監査ログ）
   監査ログ用 DB を作るサンプル:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   init_audit_db はテーブル・インデックスを冪等的に作成します。

使い方（代表的な呼び出し例）
以下はパッケージ API を直接呼ぶ最小例です。実行前に環境変数や DB スキーマが準備されていることを確認してください。

1) Settings の読み出し
   from kabusys.config import settings
   print(settings.duckdb_path)  # Path オブジェクト

2) 日次 ETL 実行（DuckDB 接続を渡す）
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())

   ※ run_daily_etl は内部で run_calendar_etl / run_prices_etl / run_financials_etl / 品質チェック を順に実行します。J-Quants API 呼び出しのため JQUANTS_REFRESH_TOKEN が必要です。

3) ニュースセンチメントスコア付与
   from kabusys.ai.news_nlp import score_news
   conn = duckdb.connect(str(settings.duckdb_path))
   n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
   print("書き込み銘柄数:", n_written)

4) 市場レジーム判定
   from kabusys.ai.regime_detector import score_regime
   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 結果は market_regime テーブルへ挿入

5) 監査 DB 初期化（再掲）
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")

ノート / 注意点
- Look-ahead bias 対策: 多くの処理（news window 計算、MA 計算等）は target_date 未満のデータのみを参照するなど、ルックアヘッドを避ける設計です。バックテスト用途で呼び出す際は target_date を明示して利用してください。
- OpenAI 呼び出し: gpt-4o-mini（コード中指定）を JSON mode で利用します。API エラー時のフォールバックやリトライロジックが組み込まれていますが、利用量に注意してください。
- J-Quants クライアント: rate limit（120 req/min）を固定間隔スロットリングで守る実装です。401 受信時はリフレッシュして再試行するロジックがあります。
- DB スキーマ: audit.init は監査テーブルを作成しますが、raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / prices_daily / market_regime 等のテーブルスキーマはプロジェクトの別ファイル（スキーマ初期化モジュール）やドキュメントに従って作成してください（本コードベース内で完全な schema init を自動的に行う箇所がない場合があります）。ETL を実行する前に必要テーブルが存在することを確認してください。
- .env のパース: kabusys.config はプロジェクトルートの .env/.env.local を自動読み込みします。シンプルなシンタックス（export 形式やクォート、コメント扱いなど）に対応します。

ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                       # 環境変数 / Settings 管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                    # ニュースセンチメント付与（score_news）
  - regime_detector.py             # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py              # J-Quants API クライアント + 保存ロジック
  - pipeline.py                    # ETL パイプライン / run_daily_etl 等
  - etl.py                         # ETLResult 再公開
  - news_collector.py              # RSS 収集・前処理
  - calendar_management.py         # 市場カレンダー管理 / 営業日判定
  - quality.py                     # データ品質チェック
  - stats.py                       # 汎用統計ユーティリティ
  - audit.py                       # 監査ログテーブル初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py             # ファクター計算
  - feature_exploration.py         # IC, forward returns, summary, rank

開発／貢献
- コードは型注釈とロギングが豊富に含まれており、テストでモック可能な設計（API 呼び出しの差し替え等）がされています。ユニットテストの追加やドキュメントの補完、スキーマ初期化スクリプトの追加などの貢献を歓迎します。
- 実稼働での利用前に、各種テーブルスキーマ、権限、監視とバックアップ、API キー管理（シークレットの安全な保管）を整備してください。

ライセンス / 免責
このドキュメントはリポジトリに含まれるコードの説明を簡潔にまとめたものです。実運用に利用する場合はコードの各部分（API 呼び出し、DB 書き込み、外部サービス利用）について十分なテストとレビューを行ってください。

以上。必要であれば README にサンプルの SQL スキーマ（raw_prices 等）や運用手順（cron / CI / Airflow からの実行例）を追記します。どの情報を優先して追加しますか？