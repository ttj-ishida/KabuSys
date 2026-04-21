# KabuSys

日本株向け自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
このリポジトリはシグナル生成・ポートフォリオ構築・発注実行・監視・研究向けユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成する以下の機能を提供します。

- ファクター計算・特徴量生成（research）
- ポートフォリオ選定・重み計算・ポジションサイジング（portfolio）
- 発注エンジン（ExecutionEngine）とブローカー抽象化（execution）
- システム／注文／リスク監視および Kill Switch（monitoring）
- ニュース NLP / レジーム検知（AI モジュール、OpenAI 使用）
- ペーパートレード検証レポート等のツール（tools）
- 環境設定ウィザードと起動前設定検証 CLI（config_setup / validate_config）

設計方針の概略：
- DB は DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- 環境依存設定は `.env` または環境変数で管理
- 実運用での安全策（Kill Switch、リスク監視、ログローテーション等）を備える

---

## 主な機能一覧

- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を使用）
  - 将来リターン、IC 計算、特徴量サマリー
- portfolio
  - 候補選定（スコア順）、等分配・スコア加重の重み算出
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株切り捨て、aggregate cap）
- execution
  - Broker クライアント抽象化（実ブローカーとモックの切替）
  - ExecutionEngine（セッション実行・PID 管理・停止フラグ監視）
  - RiskManager / OrderManager / Reconciler 等
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視ログ永続化（monitoring_db）
  - KillSwitch によるフラグファイル発行で ExecutionEngine を停止可能
- ai
  - ニュース記事のセンチメントを OpenAI で評価して ai_scores に保存
  - 市場レジーム判定（ETF MA + マクロセンチメント）
- tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+（ソースの typing 等から推定）
- pip 等のパッケージ管理ツール

1. リポジトリをクローン / ワークディレクトリへ移動

2. 依存パッケージをインストール（例）

   pip install duckdb psutil openai

   補助的 / 推奨：
   - PyYAML（config/*.yaml を検証したい場合）: pip install pyyaml

   （プロジェクト実運用では requirements.txt / Poetry 等で固定管理してください）

3. .env を作成（推奨：ウィザードを使用）

   python -m kabusys.config_setup

   このウィザードは `.env` に必要な環境変数を対話式で書き込みます。主な項目は下記参照。

4. 設定検証

   python -m kabusys.validate_config
   # 必要に応じて strict モード
   python -m kabusys.validate_config --strict

5. data / logs ディレクトリの作成（多くの場合スクリプトが自動作成しますが、権限などで失敗する場合は手動作成）

   mkdir -p data logs

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要オプション（デフォルト）
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - OPENAI_API_KEY: （AI 機能を使う場合必須）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: （アラート通知用）
  - KILL_FLAG_CLEAR_ON_START: 0 | 1（起動時に既存 kill.flag をクリアするか、デフォルト 0）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

詳細は `kabusys.config.Settings` または `python -m kabusys.config_setup` のウィザード出力を参照してください。

---

## 使い方（実行コマンド）

パッケージとしてモジュールを直接実行する形で提供されています。

- 環境設定ウィザード

  python -m kabusys.config_setup

- 設定検証（起動前チェック）

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動

  python -m kabusys.run_execution

  ポイント：
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - プロセスは実行時に PID ファイル（data/execution.pid）を作成します。
  - 停止シグナルはプロジェクトの stop flag（data/stop_requested.flag）で行います。

- Monitoring（監視ループ）起動

  python -m kabusys.run_monitoring

  ポイント：
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視 DB（SQLite）は環境にかかわらず production の `SQLITE_PATH` を使用します（監視は本番 DB を参照する設計）。
  - Stop flag（data/stop_requested.flag）が存在するとループを終了します。

- Paper Trading 検証レポート

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  # または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム内で呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB コネクション（kabusys 内で使用している DuckDBPyConnection）を受け取り、DB 内のテーブルを参照します。OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用します。

---

## 注意点 / 実行時の挙動

- process_priority: 起動スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（プラットフォーム依存、権限により失敗することがあります）。
- Stop / Kill フラグ:
  - 停止要求（stop_requested.flag）により run_execution / run_monitoring は安全にシャットダウンします。
  - Kill Switch（kill.flag）は KillSwitch により作成され、ExecutionEngine 停止要求をトリガーします。KILL_FLAG_CLEAR_ON_START が 1 のときは ExecutionEngine 起動時に kill.flag を自動で消去します（本番では 0 を推奨）。
- DB 初期化:
  - 起動スクリプトは monitoring 用の SQLite スキーマを `init_monitoring_db` で冪等に作成します。DuckDB は指定パスに接続しますが、必要なテーブルがない場合は機能の一部が動作しない場合があります。
- ログ:
  - ログは `kabusys.utils.logging_setup.setup_logging` を通じて stdout と `logs/<app_name>.log` に出力されます（日次ローテート、30日保持）。LOG_DIR 環境変数で変更可能です。
- Paper Trading と本番 DB の分離:
  - Execution は KABUSYS_ENV に応じて paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用可能。監視（monitoring）は本番の監視 DB を参照する仕組みで、監視専用の DB 初期化を行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス（環境変数/デフォルトの管理）
- config_setup.py
  - .env を対話式に作成するウィザード
- validate_config.py
  - 起動前の検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（PID / stop flag 管理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py — ログの統一設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化レイヤ
  - system_monitor.py — CPU / メモリ / ディスク / データ鮮度チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - trade_monitor.py — （注文ログ監視等）※詳細実装はモジュール内
  - monitoring_engine.py — 各 Monitor の束ね・ポーリングループ
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — アラート送信管理（LINE 等）

- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py
  - regime_detector.py

- tools/
  - paper_verification_report.py

---

## 参考コマンド例

- 1回だけ MonitoringEngine の各チェックを実行（テスト用）
  - 直接 Python REPL / スクリプトから MonitoringEngine.run_once を呼ぶか、ユニットテストを利用してください。run_monitoring は無限ループでポーリングするので単発実行は MonitoringEngine をインスタンス化して run_once を使います。

- 起動順の例（ローカルデバッグ）
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config
  3. python -m kabusys.run_execution
  4. 別プロセスで python -m kabusys.run_monitoring

---

## 開発 / テストに関する補足

- DuckDB / SQLite を使うため、テーブルやデータがない状態では一部機能（研究・AI）が動作しません。開発ではダミーデータや fixtures を用意してください。
- OpenAI を利用する AI 機能は API キーが必要です。テスト時には API 呼び出しをモックする設計（モジュール内で _call_openai_api を差し替え可能）になっています。
- PyYAML がない場合、validate_config は YAML の検証をスキップします（警告）。

---

もし README に追記したい具体的な項目（環境変数の全一覧、起動時ログ出力例、実運用でのデプロイ手順など）があれば教えてください。必要に応じて README を拡張します。