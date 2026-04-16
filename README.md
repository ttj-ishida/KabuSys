KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的としたモジュール群です。  
このリポジトリは主に以下の機能を持ちます。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- Paper Trading（本番 DB とは独立した検証用 DB）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な設計方針:
- DuckDB / SQLite を用いたローカル DB 中心の処理（外部ブローカー・API へのアクセスは分離）
- ルックアヘッドバイアス対策（内部で date.today() に依存しない設計）
- フェイルセーフ（API 失敗時にフォールバックして継続する実装）

機能一覧
---------
主なコンポーネントと役割（抜粋）

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - 停止は data/stop_requested.flag / data/kill.flag を使って行える
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor：監視ロジックとログ永続化（SQLite）
  - MonitoringEngine：複数のモニタを束ねてポーリング・アラート判定
  - AlertManager：LINE への一方向プッシュ通知
  - streamlit_dashboard.py：監視用ダッシュボード（Streamlit）
- execution/
  - OrderManager、Reconciler：注文の作成、状態同期、自動リコンシリエーション
- portfolio/
  - 候補選定（select_candidates）、重み計算、位置サイズ算出（calc_position_sizes）
- research/
  - ファクター計算（momentum/value/volatility）や IC, 将来リターン計算
- ai/
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを用いた市場レジーム判定
- tools/
  - paper_verification_report.py：Paper Trading DB の検証レポート生成

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の union 型表記を使用しているため）
- SQLite、DuckDB、ネットワーク接続（API 利用時）

推奨仮想環境の作成と必要パッケージ例（requirements.txt を用意している場合）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール（代表的な必要パッケージ）:
  - pip install duckdb psutil requests openai streamlit

プロジェクト設定 (.env)
- プロジェクトルートに .env を置くと自動読み込みされます（.env.local は上書き可能）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（主なもの）
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live") — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使うとき）
- PAPER_FILL_MODE: paper_trading 時の約定挙動 ("instant"|"partial"|"never"|"reject") — default: "instant"
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- SQLITE_PATH: 監視ログ用 SQLite（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（空なら送信はスキップ）
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）

初期ディレクトリ／ファイルの用意
- data ディレクトリを作成（DB の配置先など）:
  - mkdir -p data
- 必要に応じて .env/.env.local を作成して上記の環境変数を設定してください。

使い方
------

実行エントリ

- 実行エンジン（本番／paper）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading モードで起動し、data/paper_trading.db に記録します。
  - 実行中に停止するには data/stop_requested.flag を作成すると起動ループが検知して終了します。KillSwitch（リスク発生時）により data/kill.flag が作成されることがあります。

- 監視（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で設定できます（例: MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は監視ログを sqlite_path（Settings.sqlite_path）に書き込みます。Monitoring は本番 sqlite_path を常に使用します（環境に依らず）。

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite を開くため、監視が未起動だと DB が存在しない旨のエラーを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定できます（優先度: --db > PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

運用上のファイル（フラグ / pid）
- data/stop_requested.flag: run_monitoring / run_execution の外部停止フラグ（存在するとループを抜ける）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に対する停止シグナル）
- data/execution.pid（デフォルト名は Settings.pid_file_path）: 実行エンジンの PID ファイル。SystemMonitor はこの PID ファイルを参照してプロセスの生存を確認します。

注意点 / 補足
- Paper Trading は本番 DB と分離して記録するよう設計されています（settings.is_paper をチェック）。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必須です。API 呼び出しはリトライやエラー処理を行いますが、キー未設定なら例外が出ます。
- ストリームや外部 API の失敗はフェイルセーフで継続する設計が多く組み込まれています（ログ出力、フォールバック値）。
- プロセス優先度を変更するコード（utils.process_priority）により起動時に優先度変更を試みますが、権限不足等で失敗することがあります（警告ログ）。

ディレクトリ構成
----------------
主要ファイル / ディレクトリ（src 以下をルートとして抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境設定読み込み / Settings クラス
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py            — 優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite スキーマ + MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連モジュール) …
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py              — レジーム判定（ETF + マクロ）
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート
  - data/                             — 運用時に DB や flag を置く想定（git 管理外）

その他
-----
- DB スキーマは cabusys.monitoring.monitoring_db.init_monitoring_db で作成されます。起動時に自動で冪等に初期化されます。
- 設計やアルゴリズムの詳細はコード内の docstring コメントに記述されています（PortfolioConstruction.md / StrategyModel.md など参照の注釈あり）。
- テストやローカル検証を行う際は KABUSYS_ENV=development を利用してください。Paper Trading を行う場合は KABUSYS_ENV=paper_trading を指定することで本番 DB と完全に分離して動作します。

連絡先・貢献
--------------
この README はリポジトリのコード片に基づいて生成されています。実装の拡張やバグ修正、ドキュメント改善の PR を歓迎します。