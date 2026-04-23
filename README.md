# KabuSys

日本株自動売買システム（ミニマル実装）

このリポジトリは、シグナルを受け取って発注・約定管理・監視を行う Execution / Monitoring コンポーネント群、および環境設定ウィザードや設定検証ツールを含んだプロジェクトです。実稼働（live）、ペーパートレード（paper_trading）、開発（development）を考慮した設計になっています。

概要、機能、セットアップ、使い方、主要ファイル構成を以下にまとめます。

## プロジェクト概要
- ExecutionEngine により "Signal Queue Pull" 型で発注を実行。発注は broker クライアント（実環境向け / モック）を通して行う。
- OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（外向き API）により堅牢な注文管理を提供。
- リコンシリエーション（Reconciler）によりクラッシュ復旧時に OrderSent 状態の注文を突合して自動復旧。
- RiskManager による 3 段階（Gate1/Gate2/Gate3）のリスク統制（余力、重複、レート制限、サーキットブレーカー、ドローダウン監視）。
- monitoring 用プロセス（SystemMonitor）でシステム資源や監視ログを収集。
- 環境設定ウィザード（.env 作成）と設定検証 CLI を提供。

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）: .env の対話的作成・更新
- 設定検証 CLI（python -m kabusys.validate_config）: .env と config/*.yaml の存在/妥当性検査（--strict で警告も FAIL）
- ExecutionEngine（python -m kabusys.run_execution）: 発注セッション実行（ペーパートレード時は MockBroker）
- Monitoring ループ（python -m kabusys.run_monitoring）: 定期的システム監視と監視 DB への記録
- ブローカー抽象化（BrokerAPIProtocol）: 実実装（KabuStationClient）とモック（MockBrokerClient）を切替可能
- 注文状態機構（OrderState / OrderRecord）：状態遷移の検証と履歴永続化
- リスク管理（RiskManager）：Gate1（シグナルレベル）、Gate2（エグゼキューション）、Gate3（メトリクス）
- データユーティリティ：マーケットカレンダー管理（DuckDB）、ニュース収集（RSS → raw_news）

## セットアップ手順（開発向け）
前提: Python 3.9+（typing, dataclasses 等を利用）。以下は基本的な手順です。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低限以下を入れてください）
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML （設定検証で YAML のパースを行う場合に必要）
   - note: sqlite3 は標準ライブラリ、duckdb は外部パッケージです

4. 環境変数ファイル (.env) を作成
   - 対話的に作成する: python -m kabusys.config_setup
   - 既存の .env を手動で作る場合は .env.example を参考にしてください（リポジトリにある想定のキーを参照）

5. 設定を検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合: python -m kabusys.validate_config --strict

6. 実行（例 — ペーパートレード）
   - python -m kabusys.run_execution
   - 監視ループ: python -m kabusys.run_monitoring

注意:
- 自動で .env をプロジェクトルートから読み込みます（OS 環境変数 > .env.local > .env の順）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は決して Git にコミットしないでください（config_setup にもその旨の注意が含まれます）。

## 環境変数（主要）
以下はコードから読み取れる主要な環境変数とデフォルト・挙動のまとめです。

必須（未設定だとエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルト:
- KABUSYS_ENV: 実行環境。valid = development | paper_trading | live（デフォルト: development）
  - live の場合は追加の注意・警告が出ます
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用（任意）
- LINE_USER_ID: LINE 通知先（任意）
- PID_FILE_PATH: PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- PAPER_FILL_MODE: ペーパートレードの fill モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（デフォルトは Settings 参照）

補足:
- config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）を想定。PyYAML が無い場合は内容の検証をスキップします（警告が出ます）。

## 使い方（コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - 対話式で .env を生成／更新します
- 設定検証
  - python -m kabusys.validate_config
  - 警告も FAIL とする: python -m kabusys.validate_config --strict
- 実行エンジン起動（通常はサービス起動等から呼ぶ）
  - python -m kabusys.run_execution
    - KABUSYS_ENV により挙動が変わります（paper_trading → MockBrokerClient を使用）
    - 起動時に data/execution.pid に PID を書き込み、data/stop_requested.flag を検出すると停止します
    - kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START によって挙動が変わる（0: 起動拒否、1: クリアして起動）
- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で秒間隔を上書き可能（デフォルト: 60）
    - 停止フラグ data/stop_requested.flag を検知するとループを抜けます

## 実装上のポイント（運用ノート）
- ExecutionEngine の流れ:
  - 起動時に Reconciler を実行して OrderSent の未解決注文を突合
  - 指定時間帯にシグナル処理 → WebSocket push ドレインで状態同期
  - kill_switch() により全 active 注文をキャンセルし安全停止
- OrderManager は発注の二相永続化を採用（OrderSent 状態の DB 永続化 → Broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移等）し、クラッシュ耐性を高めています。
- RiskManager はトークンバケツ方式のレート制御、サーキットブレーカー、ポジション上限・利用率・ドローダウンを実施します。
- ブローカー実装:
  - MockBrokerClient: fill_mode によりテスト用の挙動を変えられる（instant/partial/never/reject）
  - KabuStationClient: httpx を使う同期 API 実装、WebSocket push を受け取る stream_push を持つ
- データ層:
  - DuckDB は分析・シグナルソースや market_calendar を格納
  - SQLite は主に監視（および Orders DB は SQLite）に使用

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル一覧と目的（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor（監視）起動スクリプト
- src/kabusys/execution/
  - broker_api.py — BrokerAPIProtocol, データモデル, 例外, create_broker_api()
  - kabu_client.py — kabu station 実装（HTTP/WebSocket）
  - mock_client.py — テスト用 MockBrokerClient
  - broker_factory.py — Settings に基づき broker を生成
  - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン / セッション管理）
  - order_record.py — OrderRecord, OrderState（状態遷移ロジック）
  - order_repository.py — SQLite を使った永続化層（orders テーブル）
  - order_manager.py — 注文フローの高レベル API（create/send/sync/cancel）
  - reconciler.py — 起動時リコンシリエーション（OrderSent 突合、ポジション差分検出）
  - risk_manager.py — RiskManager（3 段階リスクガード）
- src/kabusys/data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集と前処理
- src/kabusys/monitoring/
  - (monitoring 関連実装。監視 DB 初期化や SystemMonitor 実装がある想定)
- src/kabusys/utils/
  - logging_setup.py — ログセットアップヘルパ
  - process_priority.py — プロセス優先度設定ヘルパ

（注）上記はコードベースの一部抜粋です。詳細は該当モジュールの docstring やソースを参照してください。

## 運用上の注意・トラブルシュート
- validate_config は PyYAML 未インストール時に config/*.yaml のパース検証をスキップします（警告）。YAML 検証を有効にしたい場合は PyYAML をインストールしてください。
- KABUSYS_ENV=live は本番用の強い警告や追加チェックを有効にします。LINE 通知設定等が不足していると警告が出ます。
- run_execution は stop フラグ（data/stop_requested.flag）や kill.flag によって外部から停止できます。運用時はこれらのファイル管理に注意してください。
- DB 親ディレクトリが存在しない場合は起動時に自動作成されることがあるものの、事前に data ディレクトリの権限等を確認しておくと安全です。
- 実ブローカー（kabu station）接続にはローカルで kabu station アプリが起動していることが前提です（KabuStationClient を使用する場合）。

---

この README はコード内の docstring と実装に基づく概要ドキュメントです。各モジュールの詳細、運用手順や設定例は別途ドキュメント（Operation.md、DataPlatform.md 等）を用意することを推奨します。必要であれば README にさらに導入例や設定テンプレートを追記しますので、用途に合わせて指示してください。