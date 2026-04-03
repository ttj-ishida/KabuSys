KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants） → DuckDB保存 → データ品質チェック → 研究・ファクター計算 → AIを用いたニュース解析／市場レジーム判定 → 監査ログの初期化 といった機能をモジュール形式で提供します。

主な特徴
--------
- J-Quants API からの差分取得・ページネーション・トークン自動リフレッシュ・レート制御
- DuckDB を用いた冪等保存（ON CONFLICT / executemany を活用）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と LLM（OpenAI）を用いた銘柄別ニュースセンチメント集計
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを重み付け）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）・特徴量探索ユーティリティ
- 監査ログ（signal / order_request / executions）テーブル定義と初期化ユーティリティ
- .env（および .env.local）自動読み込み機能（プロジェクトルート検知）

機能一覧
--------
- data.jquants_client
  - J-Quants API からのデータ取得: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - DuckDB への保存: save_daily_quotes / save_financial_statements / save_market_calendar
  - 認証・トークン管理: get_id_token（リフレッシュトークン経由）
- data.pipeline
  - 日次 ETL run_daily_etl（calendar → prices → financials → 品質チェック）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果は ETLResult dataclass で取得
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.news_collector
  - RSS 取得・前処理・raw_news テーブルへの冪等保存（SSRF 対策、トラッキングパラメータ除去等）
- ai.news_nlp
  - ニュースの銘柄別センチメント算出（OpenAI を用いる）: score_news
- ai.regime_detector
  - ETF(1321) の 200 日 MA 乖離 と マクロニュース LLM スコアを合成して市場レジーム判定: score_regime
- research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- data.audit
  - 監査テーブル DDL と初期化: init_audit_schema / init_audit_db
- config
  - 環境変数 / .env 自動読み込みと Settings オブジェクト（settings）で集中管理

セットアップ手順
----------------

1) リポジトリをクローン（またはプロジェクトを配置）
   - プロジェクトルートには .git または pyproject.toml があることを想定しています（.env 自動読み込みに使用）。

2) Python 仮想環境を作成・有効化
   - 例（venv）:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows (PowerShell では別コマンド)

3) 必要パッケージをインストール
   - 必須（代表例）:
     pip install duckdb openai defusedxml
   - 開発環境ではプロジェクトの依存管理ファイル（pyproject.toml / requirements.txt）があればそれを使ってください。
   - 開発中にパッケージとして扱う場合:
     pip install -e .

4) 環境変数 (.env) を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
   - settings オブジェクトは必須キーが未設定だと ValueError を出すので .env を忘れずに。

注意:
- settings は .env.example を参照して必要なキーを用意してください（JQUANTS_REFRESH_TOKEN は ETL 実行や jquants_client.get_id_token で必須）。
- 実際の売買（kabu ステーション連携）を行う場合は KABU_API_PASSWORD 等の追加設定が必要です。

使い方（代表的な例）
--------------------

- DuckDB 接続を作成して日次 ETL を実行する（Python スクリプトや REPL で）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（AI）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数にセットしておくか api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルとインデックスが作成される

- 設定をプログラムから参照する:

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

- テスト時の .env 自動読み込みを無効化する:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

実行上の注意
-------------
- AI モジュール（score_news / score_regime）は OpenAI の API を呼び出します。OPENAI_API_KEY を環境変数に設定してください。
- jquants_client は J-Quants のリフレッシュトークンを用いて id_token を取得します。JQUANTS_REFRESH_TOKEN を設定してください。
- DuckDB のバージョン互換性により、executemany に空リストを渡せない箇所があるため、空チェックが入っています。ETL 結果の取り扱いに注意してください。
- news_collector は RSS の取得で SSRF／大容量レスポンス対策を備えています。外部フィードの追加時は URL の安全性にご注意ください。
- データベースファイルのパス（DUCKDB_PATH 等）は settings で設定可能です。デフォルトは data/kabusys.duckdb。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py               -- 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py           -- ニュース NLP（score_news）
  - regime_detector.py    -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py     -- J-Quants API クライアント（取得・保存）
  - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
  - etl.py                -- ETLResult の再エクスポート
  - news_collector.py     -- RSS 取得・前処理
  - calendar_management.py-- 市場カレンダー管理・判定
  - quality.py            -- データ品質チェック
  - stats.py              -- 統計ユーティリティ（zscore_normalize）
  - audit.py              -- 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py    -- ファクター計算（momentum / value / volatility）
  - feature_exploration.py-- 将来リターン / IC / summary / rank

付録: よくある操作例
-------------------
- パッケージを編集可能インストール:
  pip install -e .

- ETL を日次で cron / systemd タスク化:
  - 仮想環境をアクティブにした起動スクリプトから Python を呼んで run_daily_etl を実行してください。
  - PID ファイル・キルフラグなどの監視設定は settings で調整できます。

問い合わせ / 開発
-----------------
- コード内の docstring と logger 出力を参照すると動作イメージが得られます。  
- 新しい外部依存を追加する場合は pyproject.toml / requirements.txt を更新してください。

ライセンスや貢献方法についてはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。