# KabuSys

日本株向け自動売買システムのコア部分（ライブラリ + 起動スクリプト群）。

このリポジトリは、発注フロー（ExecutionEngine）、リスクガード、ブローカークライアント（kabu station 用の実装およびモック）、マーケットカレンダーやニュース収集などのデータユーティリティ、監視プロセス等を含みます。ローカル開発・ペーパートレードから本番環境までを想定した設計です。

## 機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（OS 環境変数優先）
  - 対話式の .env 作成ウィザード（kabuys.config_setup）
  - 設定検証 CLI（env / config/*.yaml の存在と簡易検証、--strict）
- 実行エンジン（発注）
  - Signal Queue Pull 型の ExecutionEngine（発注ループ / WebSocket push ドレイン）
  - 発注状態管理（OrderRecord の状態遷移）
  - 発注永続化（SQLite: orders テーブル）
  - ブローカー抽象化（BrokerAPIProtocol）→ Mock / KabuStation 実装
  - リスク管理（Gate1/2/3：余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン）
  - リコンシリエーション（再起動時の OrderSent 照合 / ポジション差分検出）
- 監視プロセス
  - SystemMonitor を定期ポーリングして監視データを監視 DB（SQLite）へ保存
- データユーティリティ
  - JPX カレンダー管理（DuckDB）
  - RSS ニュース収集（XML の安全処理、URL 正規化、raw_news 保存ロジック）
- 開発向けモック
  - MockBrokerClient（fill_mode による振る舞い制御：instant / partial / never / reject）

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL（開発用の差し替えなど）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知用

その他:
- PAPER_FILL_MODE — ペーパートレード時のモック約定挙動（instant, partial, never, reject）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（プロセス制御／kill スイッチ関連）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

※ .env.example を参考に .env を作成してください。

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ移動

2. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合の主要パッケージ例:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (設定検証に使用)
     - defusedxml
     - (必要に応じて) pytest 等

4. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
     - オプション: --env-file を指定して別名で保存可能
   - もしくは手動で .env を作成（.env は絶対に Git にコミットしないこと）

5. 初期 DB 準備
   - data ディレクトリを作成（.env の DUCKDB_PATH / SQLITE_PATH に合わせる）
   - 監視DB / orders テーブルなどは起動スクリプト内で初期化される箇所があります（init_monitoring_db, init_orders_db 等）

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - python -m kabusys.config_setup --env-file path/to/.env

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注プロセス）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには MONITOR_POLL_INTERVAL 環境変数を設定（秒）

- 注意
  - KABUSYS_ENV=live を設定した場合、本番向けの注意喚起や追加チェックが有効になります。現状、Live broker client は未実装で NotImplementedError を投げる箇所があります（BrokerClientFactory の設計に依存）。

## 重要な設計上の挙動・注意点

- .env 自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env`、`.env.local` を自動で読み込みます。
  - OS 環境変数が優先され、.env.local は .env の上書きとして読み込まれます。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- 発注の堅牢性（OrderManager の永続化戦略）
  - 発注は「OrderCreated → OrderSent の永続化 → ブローカー API 呼び出し → broker_order_id の永続化 → OrderAccepted の永続化」の順で行われ、クラッシュ時に状態が不整合になってもリコンシリエーションで復旧できるように設計されています。

- 危険な実行防止
  - kill.flag（デフォルト: data/kill.flag）が存在する場合、ExecutionEngine は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリアするオプションあり）。
  - KABUSYS_ENV=live の場合、LINE 通知設定が未設定だと警告が出ます。

- ペーパートレード分離
  - paper_trading モードでは専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離されます。
  - MockBrokerClient の PAPER_FILL_MODE により注文の約定挙動を変えられます（instant / partial / never / reject）。

## ディレクトリ構成（主要ファイル）

（リポジトリルート / src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine を起動するエントリポイント
  - run_monitoring.py        — SystemMonitor をポーリング起動するエントリポイント
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPIProtocol, データモデル, ファクトリ
    - kabu_client.py         — kabu station REST API 実装
    - mock_client.py         — テスト用 MockBrokerClient
    - broker_factory.py      — Settings に応じたクライアント生成
    - order_record.py        — Order 状態遷移ロジック（DB 非依存）
    - order_repository.py    — SQLite を使った注文永続化
    - order_manager.py       — 発注フロー（State Machine の外向き API）
    - execution_engine.py    — ExecutionEngine（シグナル処理 / push ドレイン）
    - reconciler.py          — リコンシリエーション（OrderSent 照合・ポジション差分）
    - risk_manager.py        — Gate1/2/3 リスクガード
    - ...（他に order_history, order_utils 等が存在する場合あり）
  - data/
    - calendar_management.py — JPX カレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants API クライアント（参照される想定）
  - monitoring/
    - monitoring_db.py       — 監視DB初期化・記録（参照）
    - system_monitor.py      — システム監視ロジック（参照）
  - utils/
    - logging_setup.py       — ログ設定
    - process_priority.py    — プロセス優先度設定
  - config/                  — 設定用 YAML ファイル群（system_config.yaml 等）
  - data/                    — デフォルトの DB / PID / フラグ置き場（実行時に作成）

## サンプル .env（例）

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

※ 実際の値は config_setup のウィザードで入力することを推奨します。

## よくある操作フロー（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. 監視プロセス起動（python -m kabusys.run_monitoring）
4. 実行エンジン起動（python -m kabusys.run_execution）

## 開発・テストに関して

- MockBrokerClient を用いれば kabu station を起動せずに発注フローやリスクロジックをローカルでテストできます。
- .env の自動ロードを無効にしてテストケース専用の環境操作を行うには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

この README はコードベースの主要なモジュールと起動手順を簡潔にまとめたものです。各モジュールの詳細な API や内部仕様はソースコードの docstring・コメントを参照してください。必要であれば、セットアップの手順をさらに具体化した「クイックスタート」やサンプル .env.example を追加できます。