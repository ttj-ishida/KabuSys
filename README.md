# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ / ポートフォリオ構築 / 実行 / 監視 / AI補助）。  
この README はリポジトリ内の主要モジュールをもとに、開発者向けの概要・セットアップ・実行方法を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下の主要な機能を持つモジュール型自動売買基盤です。

- DuckDB / SQLite を用いた時系列データ解析・永続化
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine（注文管理・ブローカークライアント抽象化）
  - 本番（live）およびペーパートレーディング（paper_trading）対応
- 監視サブシステム（システム状態・注文滞留・リスク監視・Kill Switch）
- AI 補助（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の一部:
- 外部呼び出し（発注など）は Execution モジュール経由で抽象化
- リサーチ/AI 部分は本番資金や API 呼び出しに直接影響しないよう設計
- ルックアヘッドバイアス対策（日時参照の扱いに配慮）

---

## 機能一覧（主なコンポーネント）

- kabusys.config
  - .env 自動読み込み、Settings クラス（環境変数のラッパー）
- kabusys.config_setup
  - 対話式ウィザードで `.env` を生成/更新
- kabusys.validate_config
  - 起動前に環境変数 / config/*.yaml を検証する CLI
- Execution 系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により挙動変化）
  - broker_factory / order_manager / reconciler / risk_manager 等（発注ロジック）
- Monitoring 系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringDB
  - monitoring_db: SQLite の監視テーブル初期化・アクセスラッパー
- Research / Portfolio
  - research.factor_research: MOM, VOL, VALUE 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算・IC など
  - portfolio: 候補選定・重み計算・ポジションサイズ決定・セクター制限
- AI
  - ai.news_nlp: ニュースを LLM で解析し ai_scores を生成
  - ai.regime_detector: MA200 とマクロニュースを合成して市場レジーム判定
- utils
  - process_priority: プロセス優先度設定・CPU affinity ユーティリティ
- tools
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

---

## 前提 / 要件

最低限必要なパッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config YAML の検証を行う場合)

実際の要件はプロジェクトの `requirements.txt`（存在する場合）を確認してください。

---

## セットアップ手順

1. リポジトリをクローン/取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最低限: pip install duckdb psutil
   - AI 機能: pip install openai
   - YAML 検証: pip install PyYAML
4. .env を作成
   - 対話式: python -m kabusys.config_setup
   - または手動で `.env` を作成（下記「主な環境変数」を参照）
5. 設定確認（推奨）
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再度検証

---

## 主な環境変数（重要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

一般的/オプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は MockBroker を使用し、別 DB に記録される
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知（任意）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag をクリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要 CLI / スクリプト）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に同ファイルが作成されると安全に停止する
    - PID ファイル: data/execution.pid（デフォルト）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルトで 60 秒ごとに SystemMonitor.check_once() を実行
    - MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒）
    - 監視記録は sqlite (Settings.sqlite_path)／duckdb へ保存（監視は本番 sqlite_path を参照）
    - 停止フラグ: data/stop_requested.flag を検出するとループを終了

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用

- AI 系関数（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを実行するには OPENAI_API_KEY が必要（または api_key 引数で指定）

---

## 運用時の注意点 / フラグファイル

- 停止フラグ（run_execution / run_monitoring が参照）
  - data/stop_requested.flag: 起動中のプロセスに停止要求を送るために作成されるファイル。存在を検知すると安全にシャットダウンする。
- Kill Switch（自動停止）
  - monitoring.kill_switch はリスク条件（例: ドローダウン超過、ポジション上限超過）が満たされた場合に data/kill.flag を書き込み、ExecutionEngine 停止を促す仕組みです。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（誤って自動クリアされないようにするため）。
- PID ファイル
  - data/execution.pid: ExecutionEngine が起動時に作成（監視側が存在を確認）

---

## 例: 基本的な起動手順（ローカル開発）

1. 仮想環境を用意、依存インストール
2. python -m kabusys.config_setup で .env を作成（KABUSYS_ENV=development）
3. python -m kabusys.validate_config で確認
4. （データが整っている前提で）python -m kabusys.run_execution を起動（発注は行われない開発モード）
5. 別ターミナルで python -m kabusys.run_monitoring を起動して監視を有効化

---

## ディレクトリ構成（リポジトリ内の主なファイル/パッケージ）

（src/kabusys をルートとした概略）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (未表示部分あり)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                       — データファイル（デフォルトパス例）
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - process_priority.py

---

## 開発者向け補足

- DuckDB を使って大量の時系列計算（prices_daily / raw_financials）を行う設計です。research モジュールは DuckDB 接続を受け取り SQL を発行します。
- monitoring.monitoring_db は SQLite をシンプルに扱う永続化層です（テーブル作成と簡易マイグレーションを含む）。
- AI モジュールは OpenAI の Chat Completions（gpt-4o-mini）を前提にプロンプト設計されており、API の失敗時はフェイルセーフとして処理を継続する実装になっています（ログ出力・部分書き込み等で堅牢化）。
- process_priority.set_process_priority を起動時に呼び出してプロセス優先度を上げます（プラットフォーム差分を吸収）。

---

## よくある質問（簡易）

Q: ペーパートレードと本番の DB は分離されますか？  
A: はい。KABUSYS_ENV=paper_trading のときは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用します。監視の monitoring は本番 sqlite_path を参照します（監視は本番 DB に対して行われる想定）。

Q: MONITOR_POLL_INTERVAL の単位は？  
A: 秒です。run_monitoring のポーリング間隔を上書きできます（正の整数。無効値はデフォルト 60 秒にフォールバックします）。

Q: OpenAI を使うには？  
A: 環境変数 OPENAI_API_KEY を設定してください。AI 関連関数は API キーを引数で渡すこともできます。

---

README は必要に応じてプロジェクト固有の README と組み合わせてください。補足情報（requirements.txt、運用手順、CI 設定、詳細アーキテクチャ図など）は別途追加することを推奨します。