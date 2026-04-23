# KabuSys

日本株向け自動売買システムのコアライブラリ（開発用ミニ実装）。  
このリポジトリには、環境設定ウィザード・設定検証ツール、Execution エンジン、Monitoring ループ、ブローカークライアント抽象など、運用に必要な基盤コンポーネントが含まれます。

## 概要
- 環境変数／`.env` 管理を支援する対話式ウィザード (config_setup)。
- `.env` と `config/*.yaml` の起動前チェックを行う検証 CLI (validate_config)。
- シグナルに基づく発注フローを実行する `ExecutionEngine`（発注ロジック、リスクガード、リコンシリエーション等）。
- モニタリング用のポーリングプロセス（監視データを SQLite / DuckDB に格納）。
- 実運用では kabuステーション API を使う設計だが、開発／テスト向けに MockBrokerClient（ペーパートレード用）を用意。

設計方針として、API クライアント層は DB に触れない、ビジネスロジックは OrderRecord 等で純粋関数的に保つ、永続化は OrderRepository（SQLite）に限定する、などの分離がなされています。

## 主な機能一覧
- 環境設定ウィザード: .env の作成/更新（python -m kabusys.config_setup）
- 設定検証: 必須環境変数や config/*.yaml の存在／パース検証（python -m kabusys.validate_config）
- ExecutionEngine:
  - シグナル読み込み・発注（DuckDB の signals / portfolio_targets から）
  - 3段階リスクガード (Gate1: シグナル、Gate2: レート制限/サーキット、Gate3: ドローダウン)
  - OrderManager / OrderRecord による状態遷移管理、SQLite による永続化
  - ブローカー抽象（BrokerAPIProtocol）とファクトリ（Mock / KabuStation）
  - WebSocket push の受信（kabu push）とドレイン処理
  - リコンシリエーション（起動時の注文状態同期）
- Monitoring:
  - 定期ポーリングによるシステム監視ループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - 監視用 SQLite / DuckDB へのログ保存
- Data ユーティリティ:
  - マーケットカレンダー管理（DuckDB + J-Quants 連携想定）
  - ニュース収集（RSS）モジュール（SSRF対策・XML サニタイズ等を考慮）

## セットアップ手順（開発環境向け）
1. リポジトリをクローン:
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（最低限）:
   - pip install duckdb httpx websocket-client defusedxml
   - 任意 / 検証用: pip install PyYAML
   - （本番の依存管理は requirements.txt / poetry 等を用意してください）
4. .env を用意:
   - 対話式ウィザードを使うと簡単です（次の節参照）。

注意:
- 自動で .env を読み込む仕組みがあり（プロジェクトルートに .env / .env.local があれば読み込まれます）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- デフォルトの DB パスは `data/kabusys.duckdb`（DuckDB）と `data/monitoring.db`（SQLite）です。必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` で上書きできます。

## 使い方

### .env 作成（ウィザード）
対話式で .env を作成／更新します。
- 実行:
  - python -m kabusys.config_setup
- オプション:
  - --env-file <path> で保存先を指定可能
- ウィザード終了後、.env に保存すると README に表示される例に従って次の手順（validate）を実行してください。

### 設定検証
`.env` と `config/*.yaml` の不備を起動前に検出します。
- 実行:
  - python -m kabusys.validate_config
- strict モード（警告を FAIL 扱い）:
  - python -m kabusys.validate_config --strict
- 出力: INFO / WARNING / ERROR を表示し、エラーがあれば exit code 1 を返します。

### 実行エンジン（Execution）
ExecutionEngine を実行してシグナル→発注のワークフローを動かします。
- 実行:
  - python -m kabusys.run_execution
- 注意:
  - `KABUSYS_ENV` が `paper_trading` の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します。
  - `KILL_FLAG_PATH`（デフォルト: data/kill.flag）が存在する場合、起動を拒否するか自動クリアの挙動は `KILL_FLAG_CLEAR_ON_START` に従います。
  - 実行中は `data/execution.pid`（デフォルト）に PID を書き、停止フラグ（stop_requested.flag）で安全に停止できます。

### 監視ループ（Monitoring）
SystemMonitor のポーリングを開始します。
- 実行:
  - python -m kabusys.run_monitoring
- 設定:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定（デフォルト 60）。
  - 監視は環境にかかわらず本番の SQLite（settings.sqlite_path）を使用します。

## 主要な環境変数
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（デフォルト値あり / 機能によっては必須となる場合あり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番用アラート送信に必要
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading のモック fill 動作（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

ヒント:
- validate_config はプレースホルダ（"your_value" や "*_here"）のままの変数に警告を出します。
- KABUSYS_ENV=live の場合は運用上の注意や追加チェック（LINE の設定等）を促す警告が出ます。

## ディレクトリ構成（抜粋）
リポジトリの主なファイル / モジュール構成の抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数の自動読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - broker_factory.py       — Settings からブローカークライアントを生成
    - kabu_client.py          — kabu station REST / WebSocket クライアント
    - mock_client.py          — テスト用モックブローカー
    - execution_engine.py     — ExecutionEngine 本体
    - order_record.py         — 注文状態モデルと状態遷移
    - order_repository.py     — SQLite による永続化層
    - order_manager.py        — Order 管理（作成・送信・同期・キャンセル）
    - reconciler.py           — 起動時リコンシリエーション
    - risk_manager.py         — 3段階リスクガード
    - ... (その他 execution 関連)
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB + J-Quants）
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py       — J-Quants API クライアント（想定）
    - ... 
  - monitoring/
    - monitoring_db.py        — 監視 DB 初期化・ログ関数（参照される）
    - system_monitor.py       — 実際の監視ロジック（参照される）
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ

（注）ここに挙げたファイルは主要な実装抜粋です。実際のツリーはリポジトリ全体を参照してください。

## 開発 / テストに関するメモ
- MockBrokerClient により kabuステーションを起動せずに発注フローの単体・統合テストが可能です（PAPER_FILL_MODE で挙動を切り替え）。
- OrderRepository の DB 初期化関数（init_orders_db）でテーブルを冪等に作成できます。
- Reconciler は起動時に OrderSent 状態の注文を照合し、ポジション差分を検出・ログに残します。
- `.env` のロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行われます。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## よくあるコマンドまとめ
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動（デーモン等でラップして起動）:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- （テスト用）Mock ブローカーを使うには KABUSYS_ENV を `development` または `paper_trading` に設定

---

README に記載の内容はこのコードベースの現在の実装に基づいています。運用や本番接続（kabuステーションとの連携）を行う場合は、kabuステーション のセットアップ、API パスワード管理、監査ログ、運用手順（デプロイ、バックアップ、監視）等を別途整備してください。必要であれば README に追加する運用手順やサンプル .env を作成します。