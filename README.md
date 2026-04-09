KabuSys — 日本株自動売買プラットフォーム（README — 日本語）
================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI 評価・監査ログ・ETL／ニュース収集機能を持つライブラリ群です。本コードベースは以下を目的としています。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を利用したデータ格納・品質チェック
- RSS ニュース収集と LLM によるニュースセンチメント評価（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- 研究（ファクター計算、前方リターン、IC、統計ユーティリティ）
- 発注・約定を追跡するための監査ログスキーマ（DuckDB）
- ETL パイプラインの実行・監視用ユーティリティ

このリポジトリはライブラリとしてモジュールを提供するため、直接の CLI は少なく、Python スクリプトやジョブからインポートして利用します。

主な機能一覧
-------------
- データ取得
  - J-Quants API クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info）
  - RSS ニュース収集（fetch_rss）と前処理（SSRF対策 / URL 正規化 / トラッキング除去）
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
  - ETL 結果型 ETLResult（品質チェック結果・エラーの集約）
- データ品質チェック
  - 欠損チェック、主キー重複、スパイク検出、日付不整合チェック
- 研究（Research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（クロスセクション正規化）
- AI（LLM）
  - ニュースセンチメント（score_news）：銘柄ごとの ai_score を ai_scores テーブルに書き込む
  - 市場レジーム判定（score_regime）：1321 の MA200 乖離とマクロニュースを合成して market_regime に保存
  - OpenAI 呼び出しにはリトライや JSON Mode（response_format）を使った堅牢化が施されています
- 監査（Audit）
  - signal_events, order_requests, executions テーブル定義と初期化（init_audit_schema / init_audit_db）
  - 監査用インデックスを含む冪等的な DDL 実行
- ユーティリティ
  - 環境設定管理（kabusys.config.Settings）：.env 自動ロード（プロジェクトルート検出）・必須 env の検証
  - 各種閾値設定（監視・paper trading 等）

前提（推奨環境）
----------------
- Python 3.10 以上（typing の | や型注釈の記法を使用）
- 必要なライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API / OpenAI / RSS フィード への接続

セットアップ手順
----------------
1. レポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - （プロジェクトに requirements.txt が無い場合は必要なものを個別に）
   - pip install duckdb openai defusedxml

4. 環境変数の設定（.env）
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:

     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>    （必須）
     - KABU_API_PASSWORD=<kabu_api_password>
     - OPENAI_API_KEY=<openai_api_key>                        （score_news/score_regime を使うなら必須）
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb                        （デフォルト）
     - SQLITE_PATH=data/monitoring.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - KABUSYS_ENV=development|paper_trading|live                （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|...                                 （デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1                           （自動 .env 読み込みを無効化）

   - 注意: Settings は必須 env が足りないと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

5. DuckDB の初期スキーマや監査 DB を作成する（必要に応じて）
   - Python REPL から:
     - import duckdb
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - これで監査用テーブルが作成されます。

使い方（基本例）
----------------

- ETL（日次パイプライン）を実行する例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア化（score_news）:

  - 前提: raw_news / news_symbols テーブルにデータが存在し、OPENAI_API_KEY が設定されていること。

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定（score_regime）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: モメンタム）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄ごとの dict のリスト
  ```

- 監査スキーマ初期化（既存接続に対して）:

  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

設計上の注意点 / 実運用での留意点
------------------------------
- Look-ahead bias 対策:
  - 多くのモジュール（news_nlp, regime_detector, pipeline など）は内部で datetime.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストや再現性のために target_date を必ず指定してください。
- OpenAI / J-Quants API 呼び出し:
  - リトライ・バックオフ・フェイルセーフが実装されていますが、API キーやレート制限の管理は呼び出し側で適切に行ってください。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動で読み込みます。テストや CI で自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の空リスト:
  - 一部コードでは DuckDB の executemany に空リストを渡さないようチェックしています（互換性対策）。
- RSS ニュース収集:
  - SSRF 対策・受信サイズ上限・XML の安全パース（defusedxml）を行っていますが、実運用の際はソースホワイトリスト等の運用ポリシーを設けてください。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                      : 環境設定・.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュースセンチメント（score_news）
    - regime_detector.py            : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
    - etl.py                        : ETLResult 再エクスポート
    - jquants_client.py             : J-Quants API クライアント + DuckDB への保存関数
    - news_collector.py             : RSS 収集・前処理
    - calendar_management.py        : 市場カレンダーと営業日ロジック
    - quality.py                    : データ品質チェック
    - stats.py                      : zscore_normalize 等
    - audit.py                      : 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            : calc_momentum, calc_value, calc_volatility
    - feature_exploration.py        : calc_forward_returns, calc_ic, factor_summary, rank
  - research/ ほかモジュール群...

ライセンス・貢献
----------------
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（無ければプロジェクト方針に従って追加してください）。
- バグ報告・機能要望は Issue を立ててください。PR はテスト・型チェック合わせて送っていただけると助かります。

トラブルシューティング
-----------------------
- 環境変数が足りない / settings で ValueError が出る:
  - 必須 env（主に JQUANTS_REFRESH_TOKEN、OpenAI 使用時は OPENAI_API_KEY）を .env に設定してください。
- OpenAI API 呼び出しで 429 やタイムアウトが多発する:
  - リトライロジックはありますが、レート制限の緩和（リクエスト頻度の調整）やモデル選択の変更、API プランの見直しを検討してください。
- DuckDB のテーブルが存在しないエラー:
  - ETL 実行前にスキーマ初期化や ETL が必要なテーブル作成を行ってください（schema 初期化機能が別にあれば実行）。

最後に
-----
この README はコードベース内ドキュメント（モジュール docstring）を基に作成しています。詳細な API や追加のユーティリティは各モジュールの docstring を参照してください。必要であれば README にサンプルワークフロー（Docker / systemd / scheduler 連携例）や CI 設定例も追記できます — 追加希望があれば教えてください。