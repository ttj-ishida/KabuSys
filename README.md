KabuSys — 日本株自動売買プラットフォーム
=================================

この README は提供されたコードベース（src/kabusys 以下）を元に作成した日本語の概要ドキュメントです。インストールや主要な使い方、モジュール構成、必要な環境変数等をまとめています。

概要
----
KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、ETL パイプライン、ニュースの NLP 評価（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（注文〜約定のトレーサビリティ）などを備えた、自動売買／研究プラットフォームのコンポーネント群です。データ保存に DuckDB を用い、外部 API（J-Quants、OpenAI、kabuステーション 等）と連携します。

主な機能一覧
--------------
- 環境変数・設定管理
  - settings（kabusys.config.Settings）による .env / .env.local 自動読み込みと環境変数解決
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD
- データ取り込み（J-Quants）
  - 日次株価（OHLCV）、財務データ、上場銘柄情報、JPX 市場カレンダー取得（jquants_client）
  - レート制限・リトライ・トークン自動リフレッシュの実装
  - DuckDB への冪等的保存（ON CONFLICT / UPDATE）
- ETL パイプライン
  - run_daily_etl: カレンダー・株価・財務データの差分取得と品質チェックの実行（ETLResult を返す）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付整合性チェック（quality）
- ニュース収集・前処理
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去）、記事正規化、raw_news への保存設計（news_collector）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとのニュースをまとめ、gpt-4o-mini に JSON Mode で投げて ai_scores を生成
  - レート制限／429・ネットワークエラー等へのリトライ、レスポンスバリデーション
- 市場レジーム判定（AI + 指標）
  - score_regime: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）
- リサーチ（ファクター・特徴量）
  - calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（研究用途の統計・評価ツール）
- 監査ログ（注文 → 約定 のトレーサビリティ）
  - init_audit_schema / init_audit_db：監査用テーブル群（signal_events / order_requests / executions）を DuckDB に作成

前提・要件
-----------
- Python 3.10+（型記法 Path | None を使用）
- 主要依存ライブラリ（最低限）
  - duckdb
  - openai (新しい SDK の OpenAI クラスを想定)
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime, logging 等）

セットアップ手順
----------------

1. リポジトリをクローン（またはソースを配置）
   - 例）git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に .env または .env.local を配置できます。
   - 自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な環境変数（.env 例）:
   - JQUANTS_REFRESH_TOKEN=xxxxx         # 必須（J-Quants 用リフレッシュトークン）
   - OPENAI_API_KEY=sk-xxxxx             # OpenAI API キー（score_news/score_regime 用）
   - KABU_API_PASSWORD=xxxxx             # kabuステーション API パスワード（必要なら）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト値あり
   - LINE_CHANNEL_ACCESS_TOKEN=...      # 任意
   - LINE_USER_ID=...                   # 任意
   - DUCKDB_PATH=data/kabusys.duckdb    # デフォルト値あり（expanduser される）
   - SQLITE_PATH=data/monitoring.db     # デフォルト値あり
   - PID_FILE_PATH=data/execution.pid    # 等、settings に定義済みのキーが使えます

   注意:
   - settings.jquants_refresh_token は必須です。未設定だと ValueError が発生します。
   - OpenAI キーは score_news / score_regime の引数 api_key に渡すか、環境変数 OPENAI_API_KEY に設定します。

5. データベース・監査テーブルの初期化（例）
   - Python REPL またはスクリプト内で:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # これで監査用テーブルが作成されます

基本的な使い方（例）
-------------------

- ETL（デイリー）を実行する（DuckDB 接続を渡す例）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアを生成する（OpenAI API キーを環境変数に置くか引数で渡す）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")

  # または明示的にキーを渡す
  n_written = score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジームを判定して保存する:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究向け関数（例: モメンタム）:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]

- jquants_client を直接使ってトークンやデータを取得する:

  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token が使われる
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))

設定（kabusys.config.Settings）
------------------------------
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に .env と .env.local を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要プロパティ:
  - jquants_refresh_token（必須）
  - kabu_api_password
  - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path, pid_file_path, kill_flag_path 等
  - 環境: KABUSYS_ENV (development / paper_trading / live)
  - LOG_LEVEL（DEBUG/INFO/...）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールとファイル一覧（提供コードに基づく要約）:

- kabusys/
  - __init__.py
  - config.py                        # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュース NLP（score_news）
    - regime_detector.py              # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py          # 市場カレンダー管理（is_trading_day 等）
    - etl.py                          # ETL 公開インターフェース
    - pipeline.py                     # 日次 ETL 実装（run_daily_etl 等）
    - stats.py                         # 統計ユーティリティ（zscore_normalize）
    - quality.py                       # データ品質チェック
    - audit.py                         # 監査ログ（テーブル定義・初期化）
    - jquants_client.py                # J-Quants API クライアント（fetch/save）
    - news_collector.py                # RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py               # ファクター計算（momentum/value/volatility）
    - feature_exploration.py           # 将来リターン・IC 等
  - (その他: strategy, execution, monitoring を __all__ に含むが今回の提供コードには該当実装が含まれていない部分あり)

注意事項・設計上のポイント
-------------------------
- ルックアヘッドバイアス対策:
  - 多くの関数（news ウィンドウ計算、regime/score_news、ETL）は datetime.today()/date.today() を直接参照せず、target_date を引数で明示することでバックテスト等でのリークを防止します。
- フェイルセーフ:
  - 外部 API の失敗（OpenAI / J-Quants）に対しては多くの箇所でフォールバック（スコア 0.0 など）やリトライを実装し、例外で全体が停止しない設計になっています。
- データベース操作:
  - DuckDB を採用。保存は冪等（ON CONFLICT）で実装されているため再実行耐性があります。
- セキュリティ対策:
  - news_collector では SSRF 対策、トラッキングパラメータ除去、受信サイズ制限、defusedxml による XML パース保護などを実装。

よくある操作フロー例
-------------------
- 毎朝のバッチ（ETL → ニューススコア → レジーム判定 → 戦略評価）
  1. run_daily_etl(conn, target_date=today)
  2. score_news(conn, target_date=today, api_key=...)
  3. score_regime(conn, target_date=today, api_key=...)
  4. strategy モジュールでシグナル生成 → audit に記録 → execution モジュールで発注

サポート・拡張ポイント
---------------------
- strategy / execution / monitoring モジュールは __init__ で公開される想定（今回のコードスニペットでは詳細実装なし）。実運用時には発注ロジック・ブローカ連携・プロセスマネジメントを追加してください。
- OpenAI の呼び出し部はテスト容易性のため差し替え可能（内部関数を patch してモック可能）。

ライセンス・作者
----------------
- 本 README は提供されたコードに基づいて自動生成されたドキュメントです。実運用に使う前に各 API キー・通信先の取り扱い、法遵守、リスク管理を十分に確認してください。

補足（トラブルシューティング）
------------------------------
- DuckDB に関する executemany の空パラメータ制約（コメントで触れられている）に注意。関数側は空リストの executemany を呼ばないようチェックしていますが、独自に操作する際は考慮してください。
- settings.jquants_refresh_token が未設定だと多くの機能が動作しません。まずこれを .env に設定してください。

以上がコードベース（src/kabusys）に基づく README の要点です。必要であれば README を README.md 形式で整形したり、各 API の使用例（スクリプト雛形）や requirements.txt、起動スクリプト例を追記します。どの形式（Markdown ファイル出力、インストール手順の詳細化、例スクリプトの追加等）を優先しますか？