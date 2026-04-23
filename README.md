# KabuSys

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
このリポジトリには、設定管理・検証、発注エンジン、ブローカークライアント、リスクガード、監視ジョブ、データ処理（カレンダー／ニュース収集）など、売買システムの主要コンポーネントが含まれています。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env の対話式ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
- 起動前の設定検証 CLI（.env と config/*.yaml の存在・整合性チェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine（シグナルベースの発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - 発注フローの2相永続化、Reconciliation（再突合）対応
  - 3段階のリスクガード（Gate1: シグナル／ポジション、Gate2: レート／CB、Gate3: ドローダウン）
- Broker クライアント層
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST + WebSocket 実装）
  - 抽象的な Protocol とファクトリ（create_broker_api）
- 注文永続化（SQLite）
  - orders テーブルの初期化 / CRUD（OrderRepository）
- リコンシリエーション（起動時に OrderSent を突合）
- 監視ループ（SystemMonitor）と監視 DB 初期化
- データ処理
  - マーケットカレンダー管理（DuckDB）
  - ニュース収集モジュール（RSS 取得／正規化／保存）

---

## 必要要件

- Python >= 3.10
- 推奨パッケージ（一部機能で必須）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証に使用。未インストールでも動作はするが検証がスキップされます）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

インストール例（仮）:
- 仮想環境作成・有効化
- pip install -r requirements.txt もしくは必要パッケージを個別にインストール

（requirements.txt は本リポジトリに含まれていないため、上記パッケージを手元で用意してください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml

4. 対話式ウィザードで .env を作成（推奨）
   - python -m kabusys.config_setup
   - オプション: --env-file でファイルパスを指定可能

   ウィザードは既存の .env を読み込み、Enter で既存値／デフォルトを再利用できます。生成された .env は Git に含めないでください（README・ウィザード内でも警告あり）。

5. 設定を検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化等は実行スクリプト（run_execution / run_monitoring）で必要に応じて自動作成される箇所がありますが、data ディレクトリの整備や権限を確認してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（デフォルトあり or オプション）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - live に設定すると本番向け挙動（警告や追加チェック）になります
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（live 環境では未設定だと警告）

その他:
- PAPER_FILL_MODE — paper_trading モードでのモック約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=自動クリア、デフォルト 0）

注意:
- .env は OS 環境変数より優先されません。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して .env を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主要コマンド）

- .env 作成 / 更新（対話ウィザード）
  - python -m kabusys.config_setup
  - python -m kabusys.config_setup --env-file path/to/.env

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60）

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します

- 実装上の留意点
  - run_execution / run_monitoring はプロセス優先度設定や PID / stop flag ファイルを使います（data ディレクトリ下にファイルを作成）。
  - 本番運用時は KABUSYS_ENV=live での注意（LINE の通知設定、KILL_FLAG_CLEAR_ON_START の値等）を必ず確認してください。

---

## .env の最小例

以下は最低限設定が必要な項目の例（実際の値はウィザードで入力してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

注意: 上記はプレースホルダです。実運用では秘密情報を適切に管理してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み（.env 自動読み込み）と Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングスクリプト

src/kabusys/execution/
- broker_api.py
  - BrokerAPI の Protocol / データモデル / 例外 / ファクトリ
- broker_factory.py
  - Settings からクライアント生成
- kabu_client.py
  - kabuステーション REST/WebSocket クライアント（httpx / websocket-client）
- mock_client.py
  - テスト用 MockBrokerClient
- order_record.py
  - 注文状態モデルと遷移ロジック（状態遷移の検証）
- order_repository.py
  - SQLite による永続化層（orders テーブル初期化含む）
- order_manager.py
  - 注文フローの外向き API（create/send/sync/cancel）
- execution_engine.py
  - Signal Queue Pull 型発注エンジン（セッション管理・push ドレイン）
- reconciler.py
  - 起動時のリコンシリエーション（OrderSent 照合・ポジション差分検出）
- risk_manager.py
  - 3段階リスクガード（Gate1/2/3）

src/kabusys/data/
- calendar_management.py
  - マーケットカレンダー管理（DuckDBベース）
- news_collector.py
  - RSS 取得／前処理／保存ロジック（defusedxml 等を使用）
- jquants_client.py (参照あり: J-Quants API クライアントはここに実装されている想定)

src/kabusys/monitoring/
- monitoring_db.py (参照あり: 監視用 DB 初期化 / ログ記録等)
- system_monitor.py (参照あり: システムメトリクスの収集)

（上記は本リポジトリ内の主要モジュールを抜粋した一覧です。実際の他ファイルやサブモジュールも含まれます。）

---

## 運用上の注意

- .env ファイルは機密情報を含むため絶対に Git 管理（コミット）しないでください。
- KABUSYS_ENV=live の際は特に注意（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の値、DB のパス確認など）。
- ExecutionEngine は停止フラグ（data/stop_requested.flag や kill.flag）と PID ファイルを使ってプロセス管理を行います。運用スクリプトと組み合わせて適切に扱ってください。
- Reconciliation（起動時の突合）は OrderSent の不確定な注文を復旧するため重要です。DB の整合性が取れていることを前提に設計されています。

---

必要であれば、README に追加するサンプル .env.example、起動スクリプトの systemd ユニットサンプル、あるいは開発用のテスト手順（ユニットテスト・統合テストの実行方法）も作成できます。どの情報を補足しましょうか？