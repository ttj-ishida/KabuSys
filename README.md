KabuSys — 日本株自動売買システム (README)
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の主要コンポーネントを含みます:

- ExecutionEngine（発注エンジン、paper/live の切り替え対応）
- Monitoring（システム状態・発注状態・リスク監視・Kill Switch）
- Portfolio construction（候補選定・重み付け・株数算出）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート等）
- DB 永続化（SQLite / DuckDB をデータ層として使用）

設計方針の要点:
- 本番 DB と paper_trading は分離（paper_trading 用 SQLite を別ファイルに記録）
- DuckDB を分析テーブル（prices_daily / raw_financials 等）用に利用
- .env ベースの設定管理・対話ウィザード・事前検証を提供
- OpenAI を使う機能は API キー必須でフェイルセーフ設計（API 失敗時はフォールバック）

主な機能
--------
- Execution
  - ExecutionEngine によるセッション実行（run_execution.py）
  - ブローカー抽象化（BrokerClientFactory）により本番/モック切替（KABUSYS_ENV=paper_trading）
  - 発注ログ・トレードログの永続化（SQLite）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - Kill Switch（閾値超過で data/kill.flag を書くことで ExecutionEngine を停止）
  - ログ保存・アラート管理のフックポイント
- Portfolio
  - 候補選定（スコア降順）、等配分・スコア加重配分
  - セクター集中制限適用、レジーム乗数計算
  - 株数決定ロジック（単元株丸め、aggregate cap のスケーリング等）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 参照）
  - 将来リターン計算、IC（Spearman）などの統計分析ユーティリティ
- AI
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント化して ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム判定（regime_detector）
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

動作要件（目安）
----------------
- Python 3.10+
- DuckDB（Python バインディング: duckdb）
- psutil（プロセス優先度・モニタリング）
- OpenAI SDK（AI モジュールを利用する場合）
- （必要に応じて）PyYAML（config/*.yaml の中身検証時に使用）
- 依存パッケージはプロジェクト配布時の requirements.txt / pyproject.toml を参照してください。

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストールします（プロジェクトに requirements.txt / pyproject.toml がある前提）。
   - pip install -r requirements.txt
   - あるいは pyproject.toml を使う場合は poetry / pip-tools 等でインストール

3. 初期設定 (.env) を作成します（対話ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env を絶対に Git にコミットしないでください）

4. 設定を検証します:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

5. データディレクトリの準備（必要に応じて）
   - デフォルトの DB / ログパス
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログディレクトリ: logs/
   - これらは Settings クラスの環境変数で上書き可能です。

主要な環境変数
--------------
（アプリ起動に必須・重要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")。デフォルト: development
- OPENAI_API_KEY: AI モジュール利用時に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定自動ロード:
- プロジェクトルートにある .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

よく使う上書き:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番環境で自動クリアされないよう注意（デフォルト 0）

使い方（実行方法）
-----------------

1) Monitoring を起動
- 簡単起動:
  - python -m kabusys.run_monitoring
- 補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は Settings.env に関係なく本番 sqlite_path（SQLITE_PATH）を使用して monitoring DB を開きます
  - 停止: data/stop_requested.flag を作成するとループが終了します

2) ExecutionEngine を起動
- python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と完全分離されます
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します
  - エンジンは別スレッドで run_session を実行し、stop フラグ検知で安全停止します

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）

4) 設定ウィザード・検証
- ウィザード: python -m kabusys.config_setup
- 検証: python -m kabusys.validate_config [--strict]

AI 関連
-------
- ニュース NLP（センチメント）:
  - 関数: kabusys.ai.score_news (kabusys/ai/news_nlp.py)
  - OpenAI API キー (OPENAI_API_KEY) 必須
  - LLM 呼び出しでの 429 / タイムアウト / 5xx に対してリトライ実装あり
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime
  - 同じく OpenAI API を利用。API エラー時は macro_sentiment を 0.0 にフォールバックする設計

ログ / PID / フラグ
-------------------
- ログ:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出しているため、logs/<app_name>.log が日次ローテーションで保存されます（デフォルト logs/）
- PID / 停止フラグ:
  - ExecutionEngine 用 PID: data/execution.pid
  - 停止要求: data/stop_requested.flag（run_monitoring/run_execution が監視）
  - Kill Switch: data/kill.flag を書くことで ExecutionEngine に停止シグナルを与えます（Monitoring 内で評価・作成）

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在想定: Trade の監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信側の抽象)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     — 実行時生成の DB / PID / flag を置く想定（git 管理から除外）

設計上の注意点 / 運用ノウハウ
----------------------------
- 本番稼働時は KABUSYS_ENV=live に設定し、.env の内容・LINE 通知設定等を入念に確認してください。validate_config は live 環境で追加警告を出します。
- paper_trading は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- ログディレクトリの作成に失敗した場合はコンソールログのみになります。ログディレクトリのパーミッションに注意してください。
- Kill Switch / stop flag はファイル存在判定で動作するため、手動でフラグファイルを削除 / 作成する運用が可能です。
- AI モジュールの呼び出しは外部 API に依存します。API 失敗時の安全なフォールバックが組み込まれていますが、API キーや利用制限は運用者側で管理してください。
- process_priority（優先度）や CPU affinity を設定するために psutil を利用します。権限の関係で設定に失敗する可能性があるためログでの確認を行ってください。

開発者向けメモ
----------------
- DuckDB 接続を渡してファクター計算関数を呼ぶことで、Jupyter / スクリプトから簡単に解析が行えます。
  例:
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    result = calc_momentum(conn, date(2026,4,1))
- ローカルでのテストは KABUSYS_ENV=development を使い、外部 API をモックして実行することを推奨します。
- コード中の TODO / NOTE コメントを参照して将来的な拡張点（lot_size per stock、価格フォールバックなど）に対応してください。

ライセンス / コントリビューション
---------------------------------
- 本リポジトリのライセンスやコントリビューション規約はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

おわりに
--------
この README はコードベースの主要点をまとめたものです。各モジュールには詳細な docstring と説明が含まれているため、具体的な実装や API の使い方は該当ファイルを参照してください。質問や追加のドキュメントが必要であれば教えてください。