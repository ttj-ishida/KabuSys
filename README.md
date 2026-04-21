KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買（Execution）、監視（Monitoring）、ファクター計算／リサーチ、Paper Trading 検証、AI ニュース解析などを含むモジュール群を提供します。  
以下はコードベース（src/kabusys 以下）に基づく README です。

プロジェクト概要
----------------
KabuSys は次のような責務を持つコンポーネント群で構成されています。

- ExecutionEngine：ブローカークライアントを通じた発注ロジック、オーダー管理、リスク管理、リコンシリエーション。
- Monitoring：システム状態、注文状況、リスク（ドローダウン・ポジション上限等）を定期監視し、必要に応じて kill flag を書き込む等のガードを提供。
- Research：DuckDB を使ったファクター計算（momentum、value、volatility 等）や特徴量探索機能。
- Portfolio：候補選定、重み計算、ポジションサイズ算出、セクター制約等の純粋関数。
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む、市場レジーム判定等。
- Tools：Paper Trading 検証レポート生成などの補助スクリプト。
- 設定ユーティリティ：.env ウィザード、設定検証 CLI、共通設定読み込み（Settings クラス）。

機能一覧
--------
主な機能（抜粋）：

- 環境設定ウィザード（kabusys.config_setup）で .env の対話的作成/更新が可能
- 設定検証 CLI（kabusys.validate_config）で起動前チェック
- ExecutionEngine の起動（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- Monitoring のポーリング実行／複数モニタ（System / Trade / Risk）統合
  - システム CPU / メモリ / ディスクの監視、Execution プロセス生存確認、データ鮮度チェック等
  - kill.flag による安全停止（KillSwitch）
- Portfolio 構築ロジック（候補選定、等金額／スコア加重、リスクベース発注量計算、セクター上限）
- Research（DuckDB 経由）でのファクター計算（momentum/value/volatility）、IC 計算、forward returns 等
- AI ニュース解析（OpenAI）での銘柄ごとセンチメント評価（score_news）
- Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）
- ログ管理ユーティリティ：標準出力 + 日次ローテートファイル（logs/<app>.log）

セットアップ手順
----------------

前提
- Python 3.9+（typing 機能を多用）
- pip

推奨手順（ローカル開発）
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を利用）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動の場合はルートに .env を作成（後述の必須環境変数を参照）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（抜粋とデフォルト）
- KABUSYS_ENV: execution モードを決定（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI 呼び出しを行う場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject （paper_trading 時の擬似約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

使い方（主要コマンド）
--------------------

起動スクリプト（モジュール実行）
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - プロセス優先度を high に設定（set_process_priority）
    - Settings からパスを取得して SQLite（monitoring DB）と DuckDB に接続
    - SystemMonitor を作成してポーリング（間隔は MONITOR_POLL_INTERVAL またはデフォルト 60 秒）
    - 監視停止はプロジェクトルート/data/stop_requested.flag を作成することで実現

- ExecutionEngine 起動（Engine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB から分離
    - ブローカークライアントは設定に応じてファクトリ生成（Mock は paper_trading 用）
    - 実行中に data/stop_requested.flag を作成すると Engine.stop() が呼ばれて安全停止する
    - PID ファイルは data/execution.pid（デフォルト）に書かれます

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

AI モジュール（OpenAI）
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を利用します。環境変数 OPENAI_API_KEY を設定してください。
- 使用モデル: gpt-4o-mini（コード内定数）
- API呼び出しでのリトライや検証ロジックは組み込まれていますが、APIキーとネットワークが必要です。

ログとファイル
- ログ出力:
  - 標準出力（stdout）とファイル（logs/<app_name>.log、日次ローテーション、30日分保持）に出力
  - 設定は kabusys.utils.logging_setup.setup_logging で統一
- DB ファイル（デフォルト）
  - data/monitoring.db — 監視ログ（MonitoringDB）
  - data/paper_trading.db — ペーパートレード用（KABUSYS_ENV=paper_trading 時）
  - data/kabusys.duckdb — DuckDB（分析）
- フラグ / PID
  - data/stop_requested.flag — run_* スクリプトでループを停止するための外部フラグ
  - data/kill.flag — KillSwitch による Execution 停止フラグ（Monitoring が書き込む）
  - data/execution.pid — ExecutionEngine の PID（デフォルト）

注意点 / 運用に関する補足
- Monitoring は run_monitoring の実装上、環境にかかわらず Settings.sqlite_path（本番 monitoring DB）を使用する仕様になっています。Execution は KABUSYS_ENV に応じて paper_sqlite_path を使い分けます。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を必ず確認してください。validate_config は live 時に追加警告を出します。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアしますが、本番では危険のため 0 を推奨します。
- Paper Trading は実際のブローカーに発注しないものの、検証のためのログとレポートを data/paper_trading.db に残します。

ディレクトリ構成
----------------
以下は src/kabusys の主なファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数と Settings クラス、自動 .env ロードロジック
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 監視 DB の初期化と永続化 API
    - monitoring_engine.py       — 各 Monitor の統合ポーリング
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — （trade 監視ロジック、コード内に存在）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みロジック
    - alert_manager.py           — （アラート送信ロジック、コード内に存在）
  - execution/
    - execution_engine.py        — ExecutionEngine 本体
    - order_manager.py           — 発注/管理
    - order_repository.py        — 発注ログ永続化
    - reconciler.py              — ブローカー状態とローカル同期
    - broker_factory.py          — BrokerClientFactory（Mock/Live 切替）
    - risk_manager.py            — リスク判定ロジック
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・スケールダウン・単元丸め
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — momentum/value/volatility 等
    - feature_exploration.py     — forward returns / IC / summary
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         — 市場レジーム判定（ma200 + macro sentiment）
  - data/                        — 実行時に使う data/*.db, flag ファイル等（プロジェクトルート data/）
  - logs/                        — デフォルトのログ出力先（logs/<app>.log）

FAQ / よくある確認事項
--------------------
Q: 監視のポーリング間隔を変えたい
A: MONITOR_POLL_INTERVAL 環境変数（秒）で上書きできます。0 以下や非整数は無効でデフォルト 60 秒を使います。

Q: Monitoring がどの DB を使うか？
A: Monitoring（run_monitoring）は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。環境（KABUSYS_ENV）に依存せず本番用 path を使う設計です。

Q: ペーパートレードは本番 DB を汚さない？
A: はい。KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。

Q: OpenAI を試したい（news_nlp / regime_detector）
A: 環境変数 OPENAI_API_KEY を設定し、必要パッケージ openai をインストールしてください。使用モデルは gpt-4o-mini に設定されています。

最後に
------
この README はソースコード（src/kabusys/*.py）に基づく概要・操作手順の抜粋です。実運用では .env の管理（決して Git にコミットしない）、ログ監視、監視アラート受信の設定（LINE 等）を必ず整備してください。追加の質問や README の拡張（例: deploy / systemd サービス化手順）が必要であれば教えてください。