# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + CLI 起動スクリプト群）

---

## プロジェクト概要
KabuSys は日本株自動売買のための小規模フレームワークです。シグナルを読み込んで発注処理を行う ExecutionEngine、システム監視用の Monitoring、起動時のリコンシリエーションやリスクガード、kabuステーション接続用クライアント（およびモック）などを備えています。設計は以下を重視しています。

- 発注フローのクラッシュ耐性（2相永続化・リコンシリエーション）
- 3段階リスクガード（Gate1〜3）
- Paper Trading 用の MockBrokerClient による安全なローカル検証
- .env ベースの設定管理と起動前検証ツール

バージョン: 0.1.0

---

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）による .env 作成/更新
- 起動前設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数のチェック、config/*.yaml の存在・パース確認、LOG_LEVEL / KABUSYS_ENV の妥当性チェック
- ExecutionEngine
  - シグナル読み込み（DuckDB）→ Gate1/2 を経て発注 → WebSocket push ドレイン
  - kill.flag / stop_requested.flag による安全停止
  - Paper Trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- Reconciler（起動時の OrderSent 照合・ポジション差分検出）
- Order 管理（OrderRecord/OrderRepository/OrderManager）
  - 状態遷移の検証（OrderState）、SQLite による永続化
- Broker クライアント群
  - KabuStationClient（httpx + websocket-client）
  - MockBrokerClient（テスト/開発用）
- Monitoring
  - SystemMonitor のポーリングループ（run_monitoring）
- データ処理ユーティリティ
  - マーケットカレンダー管理（duckdb）
  - ニュース収集（RSS）の前処理・保存（defusedxml 等を使用）

---

## 必要条件（推奨）
- Python 3.10+
- OS 標準の SQLite（組み込み）
- 推奨パッケージ（機能に応じて必要）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の検証に使用）
  - defusedxml
- その他、requirements.txt があれば仮想環境にインストールしてください。

例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate (Windows: .venv\Scripts\activate)
- インストール（プロジェクトで用意されている場合）:
  - pip install -r requirements.txt
- 主要依存のみ例:
  - pip install duckdb httpx websocket-client pyyaml defusedxml

---

## セットアップ手順
1. リポジトリをクローン／展開
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数ファイルを作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env（デフォルト）を生成／更新します
   - あるいは手動で .env を作成（例は下記）
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit code 1）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な設定キー（.env）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB、デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（任意）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

.env の例（テンプレート）
JQUANTS_REFRESH_TOKEN=your_value
KABU_API_PASSWORD=your_value
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

注意: .env は決して Git にコミットしないでください（README ヘッダーにも記載されています）。

---

## 使い方（主要コマンド）
- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - オプション: --strict（警告を失敗扱いにする）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading / development では MockBrokerClient を使用
    - paper_trading は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離
    - 起動時に PID ファイルを書き込みます（デフォルト: data/execution.pid）
    - 停止指示:
      - ディレクトリプロジェクトの data/stop_requested.flag を作成するとループを検知して停止します
      - kill.flag（data/kill.flag）を作成すると kill_switch を発動（注文キャンセル等）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL 環境変数（秒、デフォルト 60）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（設定値）を使用

- 例（paper_trading で起動）
  - export KABUSYS_ENV=paper_trading
  - export JQUANTS_REFRESH_TOKEN=...
  - export KABU_API_PASSWORD=...
  - python -m kabusys.run_execution

ログレベルは LOG_LEVEL で調整できます。実行スクリプトは内部で setup_logging を呼び出します。

---

## 停止と保護フラグ
- stop_requested.flag
  - run_execution / run_monitoring のループはプロジェクトルート/data/stop_requested.flag の存在を監視しています。これを作成するとループを終了します。
- kill.flag（KILL_FLAG_PATH）
  - ExecutionEngine は設定された kill.flag を参照し、存在すると即座に kill_switch を発動するか、起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリア可能（開発用。実運用では 0 推奨）。
- PID ファイル
  - 実行時に PID を data/*.pid に書き込みます（デフォルト data/execution.pid / data/monitoring.pid など）。起動後は自動的に削除されます。

---

## ディレクトリ構成（抜粋）
プロジェクトルート（_PROJECT_ROOT）を基準にした主要ファイル／ディレクトリ:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数の自動読み込み・Settings クラス
    - config_setup.py           — .env ウィザード CLI
    - validate_config.py        — 起動前検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - execution/                — 発注・注文管理・ブローカー層
      - broker_api.py
      - kabu_client.py
      - mock_client.py
      - broker_factory.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconcilier.py
      - risk_manager.py
      - ...（他モジュール）
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照)
      - ...（データ関連）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - config/                    — 設定用 YAML（テンプレートを配置する想定）
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml
- .env (推奨: プロジェクトルートに配置、.gitignore 推奨)
- data/                        — デフォルトの DB・PID・フラグファイル配置（自動作成されることがある）

（README に記載したファイルはコードベースの代表例です。実際のリポジトリにはさらにモジュールが含まれる場合があります。）

---

## 注意点 / 運用メモ
- 本番（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は live 時に追加チェック（LINE 通知設定等）を行います。
- Paper Trading は MockBrokerClient を利用し、本番 DB から分離して動作します（PAPER_TRADING_SQLITE_PATH）。
- config/*.yaml は optional ですが、存在しない場合は警告になります。PyYAML がインストールされているとパース検証を行います。
- .env の自動ロード:
  - OS 環境変数 > .env.local > .env の順で読み込まれます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化できます（テスト用途）。
- 発注フローはクラッシュ耐性を考慮した設計（OrderSent の状態を DB に残し、起動時に Reconciler が broker と照合して復旧）です。

---

必要であれば、環境別のデプロイ例（systemd unit、Dockerfile、docker-compose のサンプル）やテストの実行方法、さらに詳細な設定項目説明（各 config/*.yaml のスキーマ）を追加で作成します。どの情報を優先して追加しますか？