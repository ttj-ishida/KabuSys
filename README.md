# KabuSys

日本株自動売買システムのコアライブラリ（README 日本語版）

## プロジェクト概要
KabuSys は日本株向けの自動売買フレームワークです。  
主な責務は以下の通りです：
- シグナルをもとに発注を行う ExecutionEngine（発注ロジック、リスクガード、リコンシリエーション）
- 実行状態の監視（SystemMonitor）
- ブローカー API 抽象化（kabu-station 実装 / テスト用モック）
- データ/カレンダー/ニュース収集のユーティリティ
- 環境設定ウィザード (.env の生成) と起動前検証ツール

設計上、DB（SQLite / DuckDB）は発注履歴・監視・分析に用い、発注フローはクラッシュ耐性（2相永続化・リコンシリエーション）を考慮して実装されています。

## 主な機能一覧
- ExecutionEngine: シグナル取り込み（DuckDB）→ 2 段階リスクチェック → 発注 → push ドレイン
- Order 管理: OrderRecord（状態遷移検証）、OrderRepository（SQLite 永続化）、OrderManager（ブローカー API 経由の送信 / 同期 / 取消）
- Broker クライアント:
  - KabuStationClient: kabu-station REST/WebSocket 実装（httpx, websocket-client）
  - MockBrokerClient: テスト/ペーパートレード用（fill_mode を指定可能）
- RiskManager: Gate1/2/3（シグナル／実行／メトリクス）による発注制御（レート制限、サーキットブレーカー、ドローダウン）
- Reconciler: 再起動時の OrderSent の突合、ポジション差分検出
- Data ユーティリティ: マーケットカレンダー管理（J-Quants 連携）、ニュース収集（RSS）
- 設定関連:
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
- run_execution / run_monitoring: 各種常駐プロセス用起動スクリプト

## 動作要件（依存パッケージ）
本リポジトリの一部機能は以下パッケージを必要とします（最小限）:
- Python 3.9+
- pip install で入れる想定パッケージ:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML (config YAML 検証用。未インストールでも実行は可能だが YAML 内容チェックはスキップされます)

その他、SQLite は標準ライブラリで利用可能です。

（プロジェクトに requirements.txt がない場合は上記パッケージ群を仮定してください）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
4. 初期設定ファイル (.env) を作成
   - python -m kabusys.config_setup
     - ウィザードが対話式に .env を作成・更新します。
     - デフォルトはプロジェクトルートの .env に保存されます。
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

注意:
- .env は機密情報（API トークンやパスワード）を含むため必ず .gitignore に登録し、リモートへコミットしないでください（ウィザードのヘッダにも注意書きを出力します）。

## 主要な環境変数（主に必須）
validate_config と Settings で使用される代表的な環境変数：
- 必須:
  - JQUANTS_REFRESH_TOKEN — J‑Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨:
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabu-station base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート通知（live 時に推奨）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

多くは .env に記載して自動読み込みされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

## 使い方（主要コマンド）
- .env を対話生成（初期セットアップ）
  - python -m kabusys.config_setup
- 起動前設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も失敗として扱う）: python -m kabusys.validate_config --strict
- 実行（ExecutionEngine）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading / development 環境では MockBrokerClient が使われます（実ブローカー不要）
    - 本番（live）はまだ完全実装が必要（BrokerClientFactory は未実装エラーを出す）
  - 実行フロー:
    - PID ファイル（デフォルト data/execution.pid）に PID を書き、停止フラグ（data/stop_requested.flag）で停止可能
    - 起動前に data/kill.flag があると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリア）
- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
    - 監視は KABUSYS_ENV に関わらず sqlite_path（監視 DB）を使用します
- 開発 / テスト用:
  - MockBrokerClient や paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を設定して発注フローをローカルで検証可能

## 運用上のフラグ（停止 / キル）
- 停止要求:
  - data/stop_requested.flag — 監視・実行ループはこのファイルの存在を検知して安全に停止します。
- Kill スイッチ:
  - data/kill.flag — 発注の即時停止 / 起動拒否に使います。KILL_FLAG_CLEAR_ON_START によって起動時自動クリアを許可可能（本番では 0 推奨）。

## 注意事項とトラブルシュート
- PyYAML がインストールされていない場合、validate_config は config/*.yaml のパース検証をスキップします（警告）。
- KABUSYS_ENV=live に設定する場合は LINE 通知等のモニタリング設定を必ず確認してください（validate_config が警告を出します）。
- run_execution は既存の stop / kill フラグの存在により起動を拒否します。必要に応じてフラグを削除または KILL_FLAG_CLEAR_ON_START を一時的に有効化してください（リスクあり）。
- DuckDB / SQLite の親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、権限やパスに注意してください。
- 実ブローカー（kabu station）との接続には端末上で kabuステーション が起動していることが前提です。Mock クライアントでまず動作確認を行うことを推奨します。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル / モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み・Settings 定義（.env 自動読み込み）
    - config_setup.py          — .env 対話式ウィザード CLI
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
    - execution/
      - broker_api.py         — Broker API の Protocol / データモデル / ファクトリ
      - broker_factory.py     — Settings に基づく BrokerClient 作成
      - kabu_client.py        — kabu-station REST/WebSocket 実装
      - mock_client.py        — テスト用 MockBrokerClient
      - order_record.py       — Order 状態遷移ロジック
      - order_repository.py   — SQLite 永続化層（orders テーブル）
      - order_manager.py      — 発注ワークフロー（create/send/sync/cancel）
      - execution_engine.py   — 発注エンジン（シグナル処理 / push ドレイン / kill）
      - reconciler.py         — 起動時リコンシリエーション
      - risk_manager.py       — Gate1/2/3 リスクガード
    - data/
      - calendar_management.py — マーケットカレンダー管理（J-Quants 連携）
      - news_collector.py      — RSS ニュース収集
    - monitoring/
      - monitoring_db.py      — 監視用 SQLite テーブル初期化 / ログ
      - system_monitor.py     — システム監視ロジック（CPU/MEM/DISK 等）
    - utils/
      - logging_setup.py      — ロギング初期化ユーティリティ
      - process_priority.py   — プロセス優先度設定ユーティリティ

（上記は抜粋です。実際のリポジトリにはさらにモジュールが含まれます）

## 開発メモ / 設計ポイント
- 発注のクラッシュ耐性を重視し、OrderSent 前後で 2 段階に永続化しています。これによりリコンシリエーションで状態回復が可能です。
- リスク管理は 3 段階（signal / execution / metrics）で分離し、それぞれ別責務で実装されています。
- DuckDB を使ってシグナル・カレンダー・分析データを管理し、SQLite は監視と注文履歴（永続化）に使用します。
- WebSocket push はブローカー側の push を受けて発注状態を同期する用途に設計されています（kabu-station の websocket を利用）。

---

問題が発生した場合は、実行ログ（LOG_LEVEL やログファイル設定に応じた出力）を確認してください。README への追加情報や具体的な導入手順（Docker / systemd ユニット等）が必要であれば指示をください。