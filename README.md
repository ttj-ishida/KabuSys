# KabuSys

日本株自動売買システムのサブモジュール群（設定管理、監視、ポートフォリオ構築、リサーチ、AI 補助など）。

以下はこのコードベースに含まれる主要機能、セットアップと実行方法、ディレクトリ構成の概要です。

注意: 本 README はリポジトリ中のソースコード（src/kabusys 以下）を参照して作成しています。実際の Production 運用前に必ず設定検証とローカルテストを行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供するモジュール群です。

- 環境設定・.env ウィザードと検証ツール
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
- 監視 (Monitoring) コンポーネント（システム稼働状況・注文監視・リスク監視・Kill Switch）
- ポートフォリオ構築・銘柄選定・サイズ計算（等重・スコア重み・リスクベース）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP（OpenAI を利用したニュースセンチメント評価）とレジーム判定
- ペーパートレード用の検証レポート生成ツール

設計方針の一部:
- 本番 DB とペーパートレード DB を明確に分離
- ルックアヘッドバイアス防止（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時は安全側にフォールバック）
- DB 初期化・マイグレーションは起動時に自動で行う（monitoring DB など）

---

## 機能一覧（抜粋）

- 設定管理
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - 自動 .env 読み込み（プロジェクトルートの .env / .env.local）

- 実行 & 監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード/本番を切替）
  - run_monitoring.py: SystemMonitor ポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
  - Kill Switch: リスク基準到達時に data/kill.flag を書き込み ExecutionEngine 停止
  - stop_requested.flag / execution.pid の利用で外部より停止制御

- モニタリング
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、PID の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出、dashboard 更新
  - MonitoringDB: SQLite に監視ログを永続化

- ポートフォリオ構築
  - 銘柄選定（スコア昇順ソート・上位 N 抽出）
  - 重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース／等配分／スコア配分、単元株丸め、aggregate cap）

- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（情報係数）、統計サマリ

- AI 統合（OpenAI）
  - news_nlp: ニュース記事をまとめて LLM に投げ、銘柄別センチメントを ai_scores に書込
  - regime_detector: ETF（1321）の MA200 とマクロニュースセンチメントを合成し market_regime を算出

- ツール
  - paper_verification_report: ペーパートレード用 DB から検証レポートを生成

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください）

3. プロジェクトルートに .env を作成
   - 設定ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に以下必須値を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV を development / paper_trading / live のいずれかに設定

4. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い

5. data ディレクトリ等を作成（必要なら）
   - デフォルトの DB パスは data/ 以下にあります。起動時に自動作成されることもありますが手動で用意しておくと安心です。

注意:
- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。環境を自動読み込みしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV によって run_execution の挙動が変わります:
  - paper_trading: MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
  - live / development: 本番 sqlite_path を使用（Settings.sqlite_path）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings に基づき DB 接続を作成
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用
    - BrokerClientFactory により適切な broker クライアントを生成（実ブローカー / モック）
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag が存在すると停止
  - 停止方法:
    - 実行中に data/stop_requested.flag を作成すると起動を停止または停止ルーチンが呼ばれます
    - Kill Switch により data/kill.flag が書き込まれることがある（Monitoring が発動）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更（デフォルト: 60）
  - 動作概要:
    - SystemMonitor.check_once() をポーリング実行し、監視ログ（monitoring DB）に記録
    - stop_requested.flag を検知するとループを終了
    - Monitoring は常に Settings.sqlite_path（本番 sqlite）を使用して監視情報を保存

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使って DB パスを指定可能（--db が優先）

- AI / レジーム関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ロギング
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- データベース
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、本番: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB, デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading の MockBroker の fill 挙動: instant|partial|never|reject）

- OpenAI
  - OPENAI_API_KEY（AI 機能を使う場合に必須）

- Kill / Stop
  - KILL_FLAG_CLEAR_ON_START: 1 にすると Execution 起動時に kill.flag を自動で削除（危険: 本番では 0 推奨）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - PID_FILE_PATH（デフォルト: data/execution.pid）

- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env 読み込みを無効化

---

## 停止制御（フラグファイル）

- data/stop_requested.flag
  - run_monitoring と run_execution のスクリプトで監視される停止フラグ（手動停止など）
- data/kill.flag
  - KillSwitch（監視コンポーネント）がリスク閾値到達時に作成するファイル。ExecutionEngine はこれを検出して安全停止を行います。
- data/execution.pid
  - Execution 起動時の PID ファイル。SystemMonitor は PID の存在 / 有効性をチェックし、stale PID を検出した場合に削除します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ層・Migration
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (未表示: アラート送信ロジック)
  - execution/ (発注処理周辺: ファクトリ・エンジン・リポジトリ等)
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/ (実行時に使用されるデータ／DB ファイル等を置くディレクトリ。デフォルトの sqlite/duckdb ファイルを格納)
  - config/ (YAML 設定ファイル群: system_config.yaml 等)

---

## 注意点 / 運用メモ

- DB 初期化:
  - monitoring DB のスキーマ初期化・カラム追加は init_monitoring_db() が行います（起動時に自動）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path による完全分離を行います。実ブローカーへの発注は行われません（MockBroker を使用）。
- OpenAI とコスト:
  - news_nlp / regime_detector は OpenAI API を利用するため API キーと通信コストが発生します。利用回数やバッチサイズに注意してください。
- ログ:
  - ログレベルは LOG_LEVEL で制御。起動時に logging.basicConfig(level=logging.INFO) が呼ばれるので上書きする場合は環境変数を設定してください。
- セキュリティ:
  - .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。

---

この README はコードを元にした概要ドキュメントです。各モジュールの詳細な API や ExecutionEngine の内部実装、BrokerClient の設定方法などは個別のドキュメント（設計書 / 各モジュールの docstring）を参照してください。必要であれば各コンポーネントごとの詳細 README を追補作成できます。