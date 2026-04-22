# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
このリポジトリは発注エンジン、リスクガード、モニタリング、カレンダー管理、ニュース収集などの主要コンポーネントを包含します。

## プロジェクト概要
KabuSys はローカル環境またはペーパートレードで動作する日本株向け自動売買プラットフォームのコア実装です。  
主な目的は以下です。

- シグナルに基づく発注フローの安全な実行（ExecutionEngine）
- 発注の永続化と状態遷移（OrderRepository / OrderRecord）
- ブローカー抽象（BrokerAPIProtocol）とモック実装（MockBrokerClient）
- 起動時のリコンシリエーション（Reconciler）
- 3段階リスクガード（RiskManager: Gate1/2/3）
- 監視ループ（SystemMonitor）と監視 DB
- データ周り（マーケットカレンダー、ニュース収集）
- .env ベースの設定管理ウィザードと事前検証ツール

開発 / テスト用に、kabuステーションを使わずに動作可能な Mock ブローカークライアントが用意されています（KABUSYS_ENV=development / paper_trading）。

## 機能一覧
- 環境設定ウィザード（interactive）で `.env` を生成・更新（src/kabusys/config_setup.py）
- 起動前に環境変数・設定ファイル（config/*.yaml）の検証（src/kabusys/validate_config.py）
- 発注フロー実装（ExecutionEngine）: シグナル処理、WebSocket push ドレイン、PID / stop フラグ対応
- 注文状態管理（OrderRecord の状態遷移検証）
- SQLite ベースの注文永続化（OrderRepository）と初期化関数
- ブローカー抽象化とファクトリ（create_broker_api / BrokerAPIProtocol）
- KabuStation の REST + WebSocket 実装（KabuStationClient）
- MockBrokerClient（テスト用: instant/partial/never/reject の fill モード）
- 起動時のリコンシリエーション（Reconciler）
- リスクマネージャ（チェック: 余力・重複・ポジション上限、レート制限、サーキットブレーカー、ドローダウン）
- マーケットカレンダー管理（DuckDB を用いる）および夜間更新ジョブ
- ニュース収集（RSS 取得、正規化、raw_news への保存）

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.9+
- SQLite（標準で付属）
- システムに `git` 等があること

1. リポジトリをクローンしてソースのルートに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成と有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   必須/推奨パッケージ（一部はオプション）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config の YAML パース検証に使用、無い場合は検証をスキップ）
   例:
   ```bash
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```

4. `.env` の作成
   - 対話式ウィザードで `.env` を作成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成してください（下に最小サンプルを記載）。

5. 設定検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

## 使い方

基本的な起動シナリオ:

- 設定ウィザード（.env を作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定の事前チェック
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（本番相当／ペーパートレード）
  ```bash
  python -m kabusys.run_execution
  ```
  注意:
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient が使われ、発注履歴は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に保存されます。
  - 実行中の停止はプロジェクトルート `data/stop_requested.flag` を作成すると検出して安全に停止します。
  - PID ファイルはデフォルト `data/execution.pid` に書き込まれます（環境変数 PID_FILE_PATH で変更可）。

- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で調整可能。

主要な CLI / モジュール
- config_setup: .env 対話ウィザード
- validate_config: .env および config/*.yaml の検証
- run_execution: ExecutionEngine の起動スクリプト
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト

環境変数の挙動（自動ロード）
- プロジェクトルートにある `.env` と `.env.local` が自動でロードされます。
  - 優先度: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に既存の kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL（監視ポーリング秒）

サンプル（最小）`.env`
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

運用上の注意
- Production (KABUSYS_ENV=live) 時は LINE 通知や kill switch 周りの設定を必ず確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険（既存 kill.flag を無効化して起動してしまうため推奨しない）。
- config/*.yaml（system_config.yaml 等）はリポジトリの config ディレクトリで管理。validate_config は PyYAML が無い場合パース検証をスキップします。

## ディレクトリ構成
以下は主要なファイル / モジュールのツリー（src/kabusys 以下を抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み / Settings
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py            — BrokerAPIProtocol, データモデル, 例外, ファクトリ
    - broker_factory.py        — Settings に基づくクライアント生成
    - kabu_client.py           — KabuStationClient (HTTP + WebSocket)
    - mock_client.py           — MockBrokerClient（テスト用）
    - order_record.py          — OrderRecord（状態遷移ロジック）
    - order_repository.py      — SQLite を使った永続化 (init_orders_db 等)
    - order_manager.py         — 発注フロー（create/send/sync/cancel）
    - reconciler.py            — 起動時リコンシリエーション
    - execution_engine.py      — ExecutionEngine（セッション制御）
    - risk_manager.py          — RiskManager（Gate1/2/3）
  - data/
    - calendar_management.py   — マーケットカレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集 / 前処理
    - (その他: jquants_client など)
  - monitoring/
    - (監視用 DB 初期化や SystemMonitor 実装が想定される)
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ
    - process_priority.py      — プロセス優先度設定ユーティリティ

config ディレクトリ（プロジェクトルート）
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml

（validate_config は上記ファイルの存在と YAML パースをチェックします）

## 開発・拡張ポイント（参考）
- Live ブローカークライアントは KabuStationClient を拡張して切り替え可能です（BrokerClientFactory.create）。
- ExecutionEngine の時間帯や挙動は EngineConfig で調整可能（テスト時は直接メソッド呼び出しで制御）。
- リスク設定は RiskConfig でパラメータを調整できます（rate limit、circuit breaker、drawdown など）。
- カレンダーデータは DuckDB を使用。nightly ジョブ calendar_update_job を呼んでデータを同期します。

## トラブルシューティング
- validate_config が YAML パースエラーを報告する:
  - PyYAML がインストールされているか確認。未インストール時は警告でスキップされます。
- Settings が起動時に ValueError を投げる:
  - 必須環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など) が設定されているか確認してください。
- run_execution/run_monitoring が即時終了する:
  - data/kill.flag の存在を確認。存在すると起動を拒否する設定がデフォルトです（KILL_FLAG_CLEAR_ON_START による挙動に注意）。

---

この README はコードベース内のモジュール実装に基づいて作成しています。実運用時は各構成ファイル（config/*.yaml）と `.env` の内容をプロジェクトの運用ポリシーに合わせて適切に設定してください。必要であれば README の補足やデプロイ手順、SystemMonitor の詳細、監視 DB スキーマ等を追加できます。