# KabuSys

日本株向け自動売買システムの Python 実装（リポジトリ内簡易版）。  
この README はコードベースに含まれる主要なスクリプト／モジュールを説明し、ローカルでのセットアップ・実行手順を示します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、kabu ステーション等のブローカ API と連携してシグナルに基づく自動発注を行うためのコンポーネント群です。  
設計上は次を重視しています。

- 発注フローのクラッシュ耐性（状態遷移・2相永続化など）
- 発注ガード（3 段階のリスクチェック: Signal / Execution / Metrics）
- 起動時のリコンシリエーション（OrderSent 状態の同期）
- paper_trading（モック）と本番を切り替え可能
- 監視用プロセス（SystemMonitor）と独立した実行プロセス

この抜粋には、環境設定、実行エンジン、ブローカークライアント（KabuStation / Mock）、注文管理、リスク管理、カレンダー管理、ニュース収集などの主要ロジックが含まれます。

---

## 主な機能一覧

- .env 対応の設定管理と自動ロード（Settings）
- 対話式の `.env` 生成ウィザード（kabusys.config_setup）
- 起動前に環境設定／YAML を検証する CLI（kabusys.validate_config）
- ExecutionEngine：シグナルに基づく一連の発注処理（発注、同期、キャンセル、kill switch）
- ブローカ API 層（BrokerAPIProtocol）と実装
  - KabuStationClient（kabu ステーション REST / WebSocket 実装）
  - MockBrokerClient（テスト用）
- 注文永続化（SQLite）と OrderRecord（状態遷移ロジック）
- リスク管理（3 層: Gate1/2/3、トークンバケツ、サーキットブレーカー、ドローダウン）
- Reconciler：再起動時の注文・ポジション突合
- DuckDB を利用したデータ分析・シグナル読み込み
- 監視プロセス（run_monitoring）での定期チェック（SystemMonitor）
- データ処理モジュール（市場カレンダー管理、RSS ニュース収集など）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型記法と union 演算子（|）使用のため）
- 標準ライブラリ: sqlite3, sqlite3 は組み込み
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の検証を行う場合）
  - defusedxml（RSS パーシングの安全対策）
- その他、実稼働では kabu ステーション（ローカル） や J-Quants API の利用に必要な情報

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client PyYAML defusedxml
```

（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください）

---

## 環境変数（.env）

自動ロード順序: OS 環境 > .env.local > .env  
自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` によって無効化できます。

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV （有効値: development / paper_trading / live）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （デフォルト: data/monitoring.db）
- LOG_LEVEL （DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- KILL_FLAG_CLEAR_ON_START （起動時 kill.flag を自動クリアするか）

設定ミスや欠落は `python -m kabusys.validate_config` で起動前に検出できます。

簡単な .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. `.env` を作成（手動またはウィザード）
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - これにより `.env` を生成・更新できます（保存時にファイルへ書き込み）。
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. (必要に応じて) DuckDB や SQLite の初期テーブル作成やデータ投入を行う

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env の作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（注文エンジン）
  - paper_trading / development 環境では MockBrokerClient を使用します（DB は paper_trading 用 SQLite を使用して本番 DB と分離）。
  ```bash
  python -m kabusys.run_execution
  ```
  実行中の停止は `data/stop_requested.flag` を作成するか、プロセスに SIGINT（Ctrl+C）を送ります。プロセスは `data/execution.pid` を書きます。

- 監視プロセス起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で変更できます。監視プロセスは本番 sqlite_path を利用します。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - Settings クラス：環境変数から設定を取得。自動で .env をロード。
  - _load_env_file / _parse_env_line により POSIX 風 .env を安全に読み込む。

- kabusys.config_setup
  - 対話式ウィザードで .env を作成／更新する。

- kabusys.validate_config
  - 起動前に必須環境変数や config/*.yaml の整合性をチェックする CLI。

- kabusys.run_execution
  - ExecutionEngine を立ち上げるエントリポイント。KABUSYS_ENV により paper_trading モードでは MockBrokerClient を利用。

- kabusys.run_monitoring
  - SystemMonitor のポーリングループを実行するエントリポイント。

- kabusys.execution.*
  - broker_api: ブローカ API の Protocol、データモデル、ファクトリ
  - kabu_client: kabu ステーションの REST / WebSocket 実装（実プロダクション向け）
  - mock_client: テスト／開発用の MockBrokerClient（fill_mode 等を指定可能）
  - order_record: 注文の状態遷移ロジック（OrderState, OrderRecord）
  - order_repository: SQLite による永続化層（init_orders_db を含む）
  - order_manager: 外向き API（create/send/sync/cancel）と DB 連携
  - execution_engine: シグナル処理ループ、push ドレイン、kill switch 等
  - reconciler: 再起動時の OrderSent 同期とポジション突合
  - risk_manager: Gate1/2/3 のリスク検査

- kabusys.data.*
  - calendar_management: JPX カレンダー管理、営業日判定、カレンダー更新ジョブ
  - news_collector: RSS からニュースを収集・前処理して DB に保存（defusedxml 使用）

- kabusys.monitoring (コード抜粋には一部のみ)
  - 監視 DB 初期化や SystemMonitor 実装（run_monitoring から呼び出される）

---

## ディレクトリ構成（抜粋）

以下は本コードベースに含まれる主なファイル・モジュール（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - __init__.py
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
    - data/
      - calendar_management.py
      - news_collector.py
      - (jquants_client.py 等の補助モジュールが想定される)
    - monitoring/
      - monitoring_db.py (参照あり)
      - system_monitor.py (参照あり)
    - utils/
      - logging_setup.py (参照あり)
      - process_priority.py (参照あり)

data/ ディレクトリ（実行時に生成／使用されるファイル群）:
- data/kabusys.duckdb （DuckDB のデフォルトパス）
- data/monitoring.db （監視用 SQLite）
- data/paper_trading.db （paper_trading 用 SQLite）
- data/execution.pid （実行 PID）
- data/kill.flag, stop_requested.flag （制御フラグ）

---

## 運用上の注意 / ヒント

- KABUSYS_ENV=live を設定する場合は十分に設定内容（LINE 通知、KILL_FLAG 周り）を確認してください。validate_config は live に対して追加チェックを行います。
- 本番稼働では kill.flag の扱いに注意してください。KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険です（起動時に自動クリアされる）。
- ExecutionEngine の動作時間帯（シグナル処理時間や市場の閉場時間）は EngineConfig で設定できます（既定値は 8:50, 9:10, 15:30）。
- 再起動・クラッシュ耐性を担保するために Reconciler の動作を理解しておくと良いです（OrderSent の突合など）。
- YAML の内容検証には PyYAML が必要です。インストールしていない場合は警告が出て検証はスキップされます。

---

## 参考コマンドまとめ

- .env を作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```

- 監視起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

---

README に書かれている内容はコードの抜粋に基づく概要です。実運用前には必ずローカルで十分に動作確認を行い、外部 API（kabu ステーション、J-Quants 等）の認証情報や接続先を適切に設定してください。エラーや不明点があれば該当モジュールのソースを参照して下さい。