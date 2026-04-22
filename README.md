# KabuSys

日本株自動売買システム（KabuSys）。  
このリポジトリは、シグナルに基づく発注エンジン、ブローカークライアント（kabuステーション用 / モック）、リスクガード、監視機能、データ収集（マーケットカレンダー・ニュース）などを含む自動売買プラットフォームのコア実装です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群で構成されます。

- ExecutionEngine: シグナルを読み取り、Gate（リスクチェック）を通じて発注を行うメインエンジン。
- Broker Client 層: 実運用用の KabuStationClient とテスト用の MockBrokerClient を提供。
- Order 管理: OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（発注フロー）など。
- Reconciler: 再起動後の自動復旧（OrderSent の突合・ポジション差分検出）。
- RiskManager: 3 段階のリスクガード（シグナルチェック / 実行前チェック / 約定後監視）。
- Monitoring: 監視ループ・監視 DB（SQLite）へのログ記録。
- Data モジュール: J-Quants を用いたマーケットカレンダー管理、RSS ベースのニュース収集など。
- 設定ユーティリティ: .env ワークフロー支援（ウィザード）、起動前設定検証 CLI。

設計上、DB 操作とビジネスロジックは適切に分離されており、テスト容易性と障害復旧を意識しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml 検査）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
- 監視ポーリングループ起動スクリプト（SystemMonitor）: python -m kabusys.run_monitoring
- ブローカー抽象化（BrokerAPIProtocol）: 実運用 / モック切替可能
- 注文状態機械（OrderRecord）と SQLite 永続化（OrderRepository）
- リスク管理（Gate1/2/3）、サーキットブレーカー、レート制御
- 再起動時リコンシリエーション（OrderSent の照合、ポジション差分検出）
- DuckDB を使ったシグナル / ポートフォリオ参照、J-Quants 連携（カレンダー取得）
- RSS ニュース収集（SSRF 対策・トラッキング除去・ID 冪等性）

---

## セットアップ手順

以下はローカル開発環境での基本手順の例です。

1. リポジトリをクローンする
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell 等)
   ```

3. 依存パッケージをインストール（例）
   ここでは主要な依存を示します。プロジェクト固有の requirements.txt がある場合はそれを利用してください。
   ```
   pip install duckdb httpx websocket-client pyyaml defusedxml
   ```
   - duckdb: データ分析 / カレンダー・シグナル参照
   - httpx, websocket-client: KabuStation API / WebSocket
   - pyyaml: config/*.yaml の構文チェック（インストールされていないと検証はスキップされます）
   - defusedxml: RSS 解析の安全対策

4. data ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
   （デフォルトの DB パスは data/kabusys.duckdb と data/monitoring.db）

5. .env を用意
   - 対話式ウィザードで作成するのが簡単です（下の使い方参照）。

注意:
- .env は絶対にバージョン管理にコミットしないでください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読み込みを無効化できます（テスト用途等）。

---

## 必要 / 推奨環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL: kabu station の base URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番でのアラート通知

KABUSYS_ENV の挙動:
- development: 開発用（MockBrokerClient）
- paper_trading: ペーパートレード（MockBrokerClient、専用 SQLite に記録）
- live: 本番（実運用のブローカークライアントを利用する想定。現状未実装の箇所あり）

---

## 使い方

1. .env を対話式で作る（推奨、初回のみ）
   ```
   python -m kabusys.config_setup
   ```
   - プロンプトに従って値を入力すると .env を生成します。
   - 完了後に次のコマンドで検証することを推奨します。

2. 設定を検証する
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```
   - .env の必須項目未設定や config/*.yaml の欠如、KABUSYS_ENV の不正値などを検出します。
   - PyYAML が未インストールの場合、YAML の内容検証はスキップされます（警告）。

3. 実行エンジンを起動する（通常は systemd 等でプロセス管理）
   - 実行（paper_trading / development では MockBrokerClient が使われます）:
     ```
     python -m kabusys.run_execution
     ```
   - 起動時に data/stop_requested.flag が存在すると起動しません。
   - PID ファイルはデフォルト data/execution.pid（環境変数 PID_FILE_PATH で変更可）。

4. 監視ループを起動する
   ```
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
   - 監視は常に本番 sqlite_path を使用します（環境に依らず監視 DB を参照）。

停止・運用補助:
- 停止フラグ: data/stop_requested.flag を作成するとループが検知して終了します。
- Kill Switch（致命的なリスク検出時に発動）:
  - kill.flag（デフォルト data/kill.flag）で Kill Switch のトリガーや動作が制御されます。
  - KILL_FLAG_CLEAR_ON_START 環境変数で起動時に自動クリアするか制御できます（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py ...................... 環境変数読み込み / Settings
- config_setup.py ............... .env 対話式ウィザード
- validate_config.py ............ 起動前設定検証 CLI
- run_execution.py .............. ExecutionEngine 起動スクリプト
- run_monitoring.py ............. SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_api.py .................. ブローカープロトコル・データモデル・ファクトリ
- kabu_client.py ................. kabuステーション用 HTTP/WebSocket クライアント
- mock_client.py ................. テスト用 MockBrokerClient
- broker_factory.py .............. Settings に基づくクライアント生成
- order_record.py ................ 注文状態マシン（状態遷移ロジック）
- order_repository.py ............ SQLite 永続化層（orders テーブル）
- order_manager.py ............... 発注フロー（作成・送信・同期・取消）
- execution_engine.py ............ ExecutionEngine（シグナル処理・push ドレイン）
- reconciler.py .................. 再起動時の同期・ポジション照合
- risk_manager.py ................ 3 段階リスクガード（Gate1/2/3）

src/kabusys/data/
- calendar_management.py ........ マーケットカレンダー管理（J-Quants 連携）
- news_collector.py ............. RSS ニュース収集・前処理
- (jquants_client.py 等が存在する想定)

src/kabusys/monitoring/
- monitoring_db.py .............. 監視 DB 初期化 / ロギングユーティリティ
- system_monitor.py ............. SystemMonitor 実装（run_monitoring が使用）

src/kabusys/utils/
- logging_setup.py .............. ロギング設定ユーティリティ
- process_priority.py ........... プロセス優先度設定ユーティリティ

その他:
- config/*.yaml .................. 各種設定ファイル（存在しない場合ウィザード/スクリプトで生成）

（注）上記はリポジトリ内の主要モジュールを抜粋した構成です。実際のファイル一覧はリポジトリのツリーを参照してください。

---

## サンプル .env（最小例）

.env.example（対話ウィザードの出力イメージ）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）は実運用では適切に設定してください。

---

## 運用上の注意 / トラブルシューティング

- .env を絶対にリポジトリへコミットしないでください（README 内にも警告が書かれます）。
- python -m kabusys.validate_config は起動前に実行して設定漏れや不整合を検出してください。--strict を使うと警告も失敗扱いになります（CI 等で有用）。
- PyYAML 未インストール時は config/*.yaml の構文チェックがスキップされ、validate_config は警告を出します。CI では pyyaml をインストールしてください。
- DB の親ディレクトリが存在しない場合、警告が出ます。起動時に自動作成されることもありますが、事前に data ディレクトリを作成しておくことを推奨します。
- KABUSYS_ENV=live の設定は本番挙動となります。LINE 通知等の設定が未設定だとアラートが届きません。validate_config の live 向けガードをよく確認してください。
- run_execution / run_monitoring は永続プロセスとしてデプロイすることを想定しています（systemd / supervisor 等での管理を推奨）。stop は stop_requested.flag と kill.flag により制御できます。

---

## 貢献 / 変更履歴

- 現在、Live broker client に関する一部は将来の実装（NotImplementedError）があります。開発・テストは paper_trading / development（MockBrokerClient）で行ってください。
- バグ報告・機能提案は Issue を立ててください。

---

README は以上です。実際のデプロイや CI に組み込む際は、プロジェクト固有の requirements.txt / packaging 情報・運用手順に合わせてコマンドや依存を調整してください。必要であれば README の補足（例: systemd ユニットファイル、Dockerfile、詳しい DB 初期化手順）を作成します。どの情報がさらに必要か教えてください。