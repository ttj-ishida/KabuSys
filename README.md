# KabuSys

日本株自動売買システムの一部（設定管理・実行エンジン・監視・データユーティリティ等）。  
このリポジトリはモジュール群として設計されており、ローカル開発やペーパートレードで動作するようモッククライアントを提供します。

主な目的
- 環境変数 / YAML 設定の検証
- 実行エンジン（ExecutionEngine）によるシグナル駆動の発注処理（本番 / ペーパー）
- モニタリングループ（SystemMonitor）
- ブローカークライアント（kabu station 実装とモック実装）
- 注文状態管理・永続化・リコンシリエーション
- マーケットカレンダー・ニュース収集等のデータユーティリティ

---

## 主な機能一覧

- 設定ウィザード: .env を対話式に作成 / 更新する（kabusys.config_setup）
- 設定検証: .env / config/*.yaml の不足や不整合を起動前に検出（kabusys.validate_config）
- 実行エンジン: Signal Queue を読み取り発注フローを実行（kabusys.run_execution / ExecutionEngine）
  - Gate1/Gate2/Gate3 による 3 段階リスクガード
  - 発注の2相永続化、同期・リコンサイル機能
  - paper_trading 環境では MockBrokerClient を使用
- 監視ループ: システム監視（CPU/メモリ/ディスク閾値など）を定期記録（kabusys.run_monitoring）
- ブローカー API 層:
  - KabuStationClient（httpx + websocket）
  - MockBrokerClient（テスト/開発用）
- 注文永続化: SQLite を利用（OrderRepository, init_orders_db）
- データユーティリティ:
  - カレンダー管理（DuckDB）
  - ニュース収集（RSS パーサ、SSRF 対策、前処理）

---

## 動作要件（推奨）

- Python 3.10 以上（型記法に `X | Y` を使用）
- SQLite（組み込み）
- DuckDB（ローカル DB）
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml（config YAML 内容の検証に利用。未インストールでも動作するが検証が省略される）
- その他: 標準ライブラリ（sqlite3, threading, logging 等）

インストール例（仮に requirements.txt を用意している場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
必要なパッケージのみ個別に入れる場合:
```
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / 配置
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env ファイルを作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードが .env を生成・更新します（.env は決して Git にコミットしないでください）。
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な任意 / 追加変数（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - KABU_API_BASE_URL: http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知用）
     - PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）
4. 設定の検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

- 設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔を上書き可能（デフォルト 60 秒）。
  ```
  python -m kabusys.run_monitoring
  ```
  実行中にリポジトリ直下の data/stop_requested.flag を作成すると、次のポーリングで停止します。

- 実行プロセス起動（ExecutionEngine）
  - KABUSYS_ENV により実行挙動が変わります（paper_trading なら MockBrokerClient）。
  ```
  python -m kabusys.run_execution
  ```
  実行中の停止は data/stop_requested.flag の作成で検知してクリーンに停止します。起動時に data/execution.pid（PID ファイル）が作成されます。

- 開発 / テスト向けユーティリティ
  - MockBrokerClient を用いた単体テストや ExecutionEngine の直接呼び出しが可能です（モジュール化されているためインポートして利用できます）。

---

## 重要なファイル・環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABU_API_BASE_URL: kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用
- PID_FILE_PATH: PID ファイル
- KILL_FLAG_PATH: kill.flag（起動中に検査して kill スイッチ発動の有無を判定）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするフラグ（1=クリア）

---

## 運用上の注意

- KABUSYS_ENV=live の場合は本番扱いになります。validate_config は live 設定での警告（LINE 設定未登録など）を出しますので、慎重に設定を行ってください。
- .env はセキュアな取り扱い（Git 管理に含めない）を徹底してください。
- ExecutionEngine の発注フローはクラッシュ耐性（2相永続化）を考慮して実装されていますが、本番運用では十分な監視と事前チェックを行ってください。
- run_monitoring は（コード上）KABUSYS_ENV に関係なく本番 sqlite_path を使用します。監視 DB は本番向けの一貫した保存先を想定しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み・Settings（アプリ設定）
  - config_setup.py
    - .env の対話式ウィザード生成
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py — Broker API のデータモデル、Protocol、ファクトリ
    - kabu_client.py — KabuStation REST/WebSocket 実装
    - mock_client.py — テスト用モック
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — 注文状態モデル（状態遷移ロジック）
    - order_repository.py — SQLite による永続化
    - order_manager.py — 外向き発注 API（OrderRecord + OrderRepository 組合せ）
    - execution_engine.py — ExecutionEngine（シグナル処理／WebSocket ドレイン）
    - reconciler.py — リコンシリエーション（再起動時の同期）
    - risk_manager.py — 3 段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（前処理・保存）
    - （jquants_client は参照箇所あり、別ファイルとして存在を想定）
  - monitoring/
    - monitoring_db.py (参照)
    - system_monitor.py (参照)
  - utils/
    - logging_setup.py (参照)
    - process_priority.py (参照)
  - その他: scripts/generate_config.py（config/*.yaml 生成参照）

（上記はコードベースの主要ファイルと責務の要約です。実際のファイルはリポジトリを参照してください。）

---

## 開発・拡張のポイント

- ブローカークライアントは Protocol で抽象化されており、Mock と実装を切り替え可能です。live クライアント（KabuStationClient）を本番環境向けに拡張できます。
- ExecutionEngine はテスト可能な分離設計（_process_signals / _drain_push_queue を直接呼べる）になっています。
- リコンシリエーション（Reconciler）は OrderSent の不確定状態を復旧するための中心ロジックです。再現性のあるテストが書きやすい構造です。
- calendar_management は DuckDB を利用し、外部 API（J-Quants）から夜間バッチでデータを取り込みます。

---

## トラブルシューティング

- validate_config が YAML のパースエラーを出す場合:
  - PyYAML がインストールされていないと内容検証はスキップされますが、存在チェックは行われます。インストールする場合は pyyaml を pip で追加してください。
- ExecutionEngine が起動時に kill.flag を検出すると、KILL_FLAG_CLEAR_ON_START の値により起動を拒否またはクリアして起動します。運用方針に合わせて設定してください。
- WebSocket の接続は websocket-client を使っています。接続エラーはログに出力され、再接続ロジックがあります。

---

必要があれば、README に以下を追加できます：
- 具体的な .env のテンプレート（機密情報はマスキング）
- 例: duckdb スキーマの初期化手順
- CI / テスト方法（ユニットテスト・統合テストのサンプル）
- 実行時のログ出力例とトラブルシュート事例

ご希望があれば追加で追記します。