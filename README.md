# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
シグナルに基づく発注エンジン、モニタリング、リコンシリエーション、ブローカークライアント（実装済み: Mock / 実運用クライアントは未実装）などの主要コンポーネントを含みます。

---

## 主な機能

- 環境設定ウィザード（.env を対話式に作成・更新）
- 設定検証 CLI（.env と config/*.yaml の存在・整合性チェック）
- ExecutionEngine（シグナルプル発注・WebSocket push ドレイン・Risk ガード）
- Order 管理（OrderRecord 状態遷移、OrderRepository による SQLite 永続化）
- リコンシリエーション（起動時に OrderSent を broker と突合）
- RiskManager（Gate1〜Gate3 による多層リスク統制）
- Mock ブローカークライアント（paper_trading / development 用）
- SystemMonitor（監視ループ、SQLite／DuckDB を利用）
- Data モジュール（マーケットカレンダー管理、ニュース収集等）

---

## 要求環境 / 依存

- Python >= 3.10
- 推奨（主要）パッケージ（例）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の中身検証に必要）
  - defusedxml
- 実行前に依存を requirements.txt などからインストールしてください（リポジトリに requirements.txt がない場合は上記を個別に pip install）。

例:
```
pip install duckdb httpx websocket-client pyyaml defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／取得する

2. Python 仮想環境を作成・有効化（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   ```
   pip install duckdb httpx websocket-client pyyaml defusedxml
   ```

4. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabu API パスワード、DB パス等を入力して .env を生成します。
   - .env の自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - .env は絶対に Git 等へコミットしないでください。

5. 設定検証（任意・推奨）
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗に扱いたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

---

## 主要環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要オプション
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視DB）ファイルパス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL: kabu station API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリア（0/1）

- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス（デフォルト data/*.）

補足:
- config モジュールはプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数より優先度は低い）。
- KABUSYS_ENV の値が `live` の場合は注意喚起や追加チェックが入ります。現時点で live のブローカークライアントは未実装です（BrokerClientFactory 参照）。

---

## 使い方（実行例）

- .env を作成・更新（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループを実行（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- エンジン（ExecutionEngine）を実行
  - ペーパートレード（Mock ブローカー使用）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 開発モード（同様に Mock 使用）
    ```
    KABUSYS_ENV=development python -m kabusys.run_execution
    ```
  - live は未実装（BrokerClientFactory は NotImplementedError を投げます）

停止方法:
- それぞれのプロセスはプロジェクトの data ディレクトリにある stop / kill フラグファイルを監視しています。
  - run_execution/run_monitoring は data/stop_requested.flag を、ExecutionEngine は data/kill.flag を利用します。
  - 停止はこれらのフラグを作成するか、Ctrl+C（KeyboardInterrupt）で行います。

---

## コンポーネント概要（簡易）

- config.py
  - .env の読み込みロジック、Settings クラス（アプリ設定の取得）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証ツール（必須環境変数・config/*.yaml・パス等）
- run_execution.py
  - ExecutionEngine の起動スクリプト（発注ループ）
- run_monitoring.py
  - SystemMonitor の起動スクリプト（監視ループ）
- execution/
  - broker_api.py: BrokerProtocol、データモデル、ファクトリ
  - kabu_client.py: kabu station 実装（HTTP + WebSocket）
  - mock_client.py: モック Broker（fill_mode 等を変更可能）
  - order_record.py, order_repository.py, order_manager.py: 注文状態と永続化、管理ロジック
  - execution_engine.py: 発注エンジン（Signal 処理、push drain、kill switch）
  - reconciler.py: 再起動時のリコンシリエーション
  - risk_manager.py: Gate1〜3 のリスク統制
  - broker_factory.py: 設定に応じたブローカークライアント生成
- data/
  - calendar_management.py: マーケットカレンダー管理
  - news_collector.py: RSS ニュース収集（正規化・SSRF 対策等）
- monitoring/
  - monitoring_db.py, system_monitor.py 等（監視機能）
- utils/
  - logging_setup.py, process_priority.py などのユーティリティ

---

## ディレクトリ構成（抜粋）

プロジェクトルートの src/kabusys を例に主要ファイルを列挙します:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - __init__.py
    - broker_api.py
    - kabu_client.py
    - mock_client.py
    - broker_factory.py
    - order_record.py
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - reconciler.py
    - risk_manager.py
  - data/
    - calendar_management.py
    - news_collector.py
    - jquants_client.py (参照される想定)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
  - utils/
    - logging_setup.py
    - process_priority.py

（リポジトリ全体の正確な木構成は実際のプロジェクト内ファイルを参照してください）

---

## 注意点・トラブルシューティング

- .env は機密情報を含みます。絶対にバージョン管理に含めないでください。
- validate_config は PyYAML がない場合 YAML の中身検証をスキップします。YAML 検証を行う場合は PyYAML をインストールしてください。
- KABUSYS_ENV=live のときは追加警告やチェックが入ります。現状 live ブローカークライアントは未実装です。
- run_execution は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- ExecutionEngine の停止は kill.flag によって制御されます。起動時に既に kill.flag が存在する場合は KILL_FLAG_CLEAR_ON_START の設定により挙動が変わります（デフォルトはクリアしない）。
- 実行中の PID は PID ファイルに書き出されます（デフォルト data/execution.pid など）。プロセス管理に利用できます。

---

## 開発・拡張ポイント

- live 向けの KabuStationClient の完全実装（BrokerClientFactory の live サポート）
- tests: ユニットテスト、統合テストの追加
- config/*.yaml の雛形生成スクリプト（validate_config は存在しないファイルを警告）
- 監視・アラートの拡充（LINE 連携など）

---

README の内容やサンプルコマンドで不明点があれば、どの部分を詳しく知りたいか教えてください。具体的なセットアップ環境（OS、Python バージョン）を教えていただければより細かい手順も提示できます。