README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした Python コードベースです。本リポジトリには以下の主要コンポーネントが含まれます。

- 注文実行（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ）
- リサーチ（ファクター計算・将来リターン・IC 等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（paper trading 検証レポート、Streamlit ダッシュボード）

特徴
----
- 環境による振る舞い切替:
  - KABUSYS_ENV により "development" / "paper_trading" / "live" を切り替え可能
  - paper_trading 時は MockBroker を使用し、本番 DB とは別の SQLite（data/paper_trading.db）に記録
- 監視:
  - システムリソース、プロセス存否、データ鮮度、滞留注文、約定異常、ドローダウンやポジション上限を監視
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースのダッシュボード
- ポートフォリオ構築:
  - 候補選定、等配分／スコア加重、リスクベースのポジションサイズ算出、セクター上限・レジーム乗数
- AI:
  - OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメントに基づく市場レジーム判定
  - API 呼び出しはリトライ・パース・バリデーションの仕組みあり
- DuckDB / SQLite を用いたデータ処理と永続化

セットアップ手順
--------------
前提:
- Python 3.10+（typing の Union 表記や match を使っていない設計上 3.10 以上を想定）
- git リポジトリのルートに src/ 配下がある構成と想定

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - pip install duckdb psutil openai requests streamlit
   - 追加で使うものがあれば同様にインストールしてください。

3. パスの設定 / インストール方法
   - 開発時はソースを PYTHONPATH に追加して実行する方法が簡単です:
     - export PYTHONPATH=src  (Windows: set PYTHONPATH=src)
   - あるいはパッケージとしてインストール:
     - pip install -e .

4. 環境変数 (.env)
   - リポジトリルートに .env / .env.local を置けます。自動ロードはデフォルトで有効。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須／よく使う環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI モジュールを使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
     - PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）
   - .env のパースはシェル風でコメントや export KEY=val 形式に対応しています。

使い方
------

実行系（ExecutionEngine）
- 本番 / 開発 / paper_trading に応じて動作が切り替わります。
- 起動スクリプト（src/kabusys/run_execution.py）を実行する例:
  - PYTHONPATH=src python -m kabusys.run_execution
  - paper_trading モードで起動する例:
    - export KABUSYS_ENV=paper_trading
    - export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  # 任意のパス
    - PYTHONPATH=src python -m kabusys.run_execution
- 注意:
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。OS 権限により失敗する場合があります。
  - 起動時に互換性のため監視テーブルを初期化します（init_monitoring_db）。

監視（Monitoring）
- 監視ループ起動:
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  （秒）
- 動作:
  - 監視は Settings の sqlite_path に接続し、monitoring DB を使用（環境に関わらず本番 sqlite_path を使う実装）。
  - kill.flag の場所は Settings.kill_flag_path（デフォルト: data/kill.flag）で制御。

Streamlit ダッシュボード
- 起動方法（スクリプトに推奨コマンドあり）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開き、ポジション・注文・システム状態・リスクログ等を可視化します。

Paper Trading 検証レポート
- ツール: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - --db path/to/paper_trading.db
  - 出力: 期間の稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力します。

AI モジュール
- ニュースセンチメント取得:
  - 関数 kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）
- レジーム判定:
  - 関数 kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - API 呼び出しはリトライとバリデーションの仕組みがあり、失敗時は安全にフォールバックする設計です。

重要な環境変数 / 設定一覧（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、デフォルト 60）。不正値や 0/負値はデフォルトにフォールバック。
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 DB（data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用トークン／パスワード
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）

ディレクトリ構成
----------------
（src をルートパッケージとした構成を示します）

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み含む）
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト

  - execution/                 — 発注・実行関連
    - order_manager.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - (その他ブローカー関連)

  - monitoring/                — 監視系コンポーネント
    - monitoring_db.py         — SQLite スキーマ／永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py

  - portfolio/                 — ポートフォリオ構築ロジック（純粋関数）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/                  — リサーチ / ファクター計算
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/                        — AI 関連（OpenAI を使った NLP）
    - news_nlp.py
    - regime_detector.py
    - __init__.py

  - data/                      — （想定）データパイプライン / DuckDB 関連（参照のみ）
    - pipeline.py
    - stats.py
    - (prices_daily / raw_financials テーブルを想定)

  - tools/
    - paper_verification_report.py
    - __init__.py

実運用上の注意
-------------
- process priority の変更（高優先化）は OS の権限に依存します。権限不足時は警告ログが出ますが処理は継続します。
- monitoring は環境にかかわらず Settings.sqlite_path（本番 DB）を使用する実装です。paper_trading 時の分離は run_execution.py 側で行います。
- kill.flag を使った強制停止は冪等（既存ファイルがあれば上書きしない）です。Execution 起動時にフラグをクリアするオプションがあります（Settings.kill_flag_clear_on_start）。
- OpenAI API を利用する機能は API キーと通信可能な環境が必要です。API コールにはレートや課金が発生します。

おわりに
--------
この README はコードベースを素早く理解して運用／開発を始めるための要約です。ソース内の docstring や関数コメントは詳細な設計意図や注意点を多く含んでいます。追加で運用ガイドや開発ドキュメント（例えば PortfolioConstruction.md, StrategyModel.md 等）があれば併せて参照してください。