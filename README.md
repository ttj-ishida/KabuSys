# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）。

以下はこのリポジトリの概要、セットアップ、使い方、主要機能とディレクトリ構成の説明です。

注意: .env 等に秘密情報（API トークン・パスワード）を含むため、.git にコミットしないでください。

## プロジェクト概要
KabuSys は日本株への自動売買を想定したシステム設計を含むサンプル実装です。  
主な要素は次の通りです。

- 設定管理（.env の自動ロード・対話式ウィザード）
- 設定検証 CLI（起動前に必須環境変数や YAML ファイルをチェック）
- ExecutionEngine（シグナル駆動の発注エンジン、発注フロー・リスクガード・WebSocket push 処理）
- ブローカークライアント抽象化（Mock / KabuStation 実装）
- 注文永続化（SQLite）と状態管理（OrderRecord 状態遷移）
- リコンシリエーション（クラッシュ復旧で OrderSent を突合）
- 監視ループ（SystemMonitor を定期実行して監視データを SQLite/ DuckDB に保存）
- データユーティリティ（マーケットカレンダー、ニュース収集等）

設計上、実際の取引に使用する場合は十分なレビュー・テストと本番向けブローカ実装（KabuStationClient の確認）が必要です。

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
  - 対話式に .env を作成 / 更新
- 設定検証（python -m kabusys.validate_config [--strict]）
  - 必須環境変数の有無、プレースホルダ検出、config/*.yaml の存在と YAML パース検査（PyYAML 必要）
- 実行エンジン（python -m kabusys.run_execution）
  - Signal Pull 型発注、3段階リスクガード（Gate1/Gate2/Gate3）
  - ペーパートレード用 MockBrokerClient をサポート（KABUSYS_ENV=paper_trading）
  - 停止フラグ（data/stop_requested.flag, kill.flag）に基づく安全停止
  - リコンシリエーションでクラッシュ後の注文整合性回復
- 監視ループ（python -m kabusys.run_monitoring）
  - モニタリング用のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - sqlite / duckdb への接続と監視 DB 初期化
- データ処理ユーティリティ
  - マーケットカレンダー管理（DuckDB を使用）
  - RSS ニュース収集（defusedxml 等で安全にパース）
- ブローカー抽象化（BrokerAPIProtocol）
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST API 実装、httpx + websocket-client）

## 必要要件（推奨）
- Python >= 3.10（コード内で | 型注釈等を使用しているため）
- 主要依存パッケージ（例）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML の内容検証を有効にする場合）
- 標準ライブラリ: sqlite3, threading, logging など

インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb httpx websocket-client defusedxml pyyaml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

## セットアップ手順（手順）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境（推奨）を用意して依存パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb httpx websocket-client defusedxml pyyaml

3. data ディレクトリ作成（必要な場合）
   - mkdir -p data

4. .env を作成
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
     → ウィザードは .env（デフォルトはプロジェクトルート/.env）を作成します。
   - または手動で .env を作成（最低限、必須環境変数を設定）。
     必須:
       JQUANTS_REFRESH_TOKEN=...
       KABU_API_PASSWORD=...
     推奨/任意:
       KABUSYS_ENV=development|paper_trading|live
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       KABU_API_BASE_URL=http://localhost:18080/kabusapi
       LINE_CHANNEL_ACCESS_TOKEN=...
       LINE_USER_ID=...
       KILL_FLAG_CLEAR_ON_START=0

   - 自動読み込み:
     config モジュールはプロジェクトルートで .env（→ override=False）と .env.local（→ override=True）を自動読み込みします。
     OS 環境変数より .env が優先されます。
     自動ロードを無効にするには環境変数を設定:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     python -m kabusys.validate_config --strict

6. 実行（開発 / ペーパートレード）
   - 監視ループ（常駐）:
     python -m kabusys.run_monitoring
     環境変数 MONITOR_POLL_INTERVAL で秒単位のポーリング間隔を変更可（デフォルト 60）。
   - 実行エンジン（発注処理）:
     python -m kabusys.run_execution
     KABUSYS_ENV=paper_trading のとき MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db など）に記録します。

注意:
- 本番（KABUSYS_ENV=live）を使用する場合は、LINE 通知設定や kill flag の扱い（KILL_FLAG_CLEAR_ON_START）を十分に確認してください。
- .env は決してバージョン管理にコミットしないでください（config_setup でも警告あり）。

## 主要 CLI / スクリプトの使い方

- 環境ウィザード
  - python -m kabusys.config_setup
  - .env を対話形式で生成/更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - 必須環境変数未設定や config/*.yaml の不備を検出します（PyYAML 未インストール時は YAML 検査をスキップして警告）。

- 実行エンジン起動
  - python -m kabusys.run_execution
  - ExecutionEngine をデフォルト設定で起動します（PID ファイルや stop フラグを利用）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更できます。

## 環境変数（主要一覧）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 設定例:
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL
  - KABU_API_BASE_URL — kabu station API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（live 中は要確認）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

## ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数の自動読み込みロジック、Settings クラス（アプリ設定の集中管理）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine の起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/ — 発注周りの実装
    - broker_api.py — BrokerAPIProtocol、データモデル、ファクトリ関数
    - kabu_client.py — kabu station REST/WebSocket クライアント（httpx / websocket-client）
    - mock_client.py — テスト用 MockBrokerClient（fill_mode 等を制御可能）
    - broker_factory.py — Settings に基づくクライアント生成ラッパ
    - order_record.py — 注文状態遷移と OrderRecord モデル（DB 非依存）
    - order_repository.py — SQLite 永続化層（orders テーブル + helper）
    - order_manager.py — 発注フロー（create/send/sync/cancel）を実装
    - execution_engine.py — セッションロジック（シグナル処理、push ドレイン、kill switch）
    - reconciler.py — 起動時リコンシリエーション（OrderSent の突合 → ポジション差分検査）
    - risk_manager.py — Gate1/2/3 のリスク管理ロジック
  - monitoring/ — 監視関連（monitoring_db, SystemMonitor 等）
  - data/ — データ関連モジュール
    - calendar_management.py — マーケットカレンダー（DuckDB）ロジック
    - news_collector.py — RSS ニュース収集（安全な XML パース・SSRF 対策等）

（上記は代表的なファイルと説明です。プロジェクトにはさらに補助モジュールが含まれます。）

## 運用上の注意
- .env は機密を含むため絶対にコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や kill switch の設定、KILL_FLAG_CLEAR_ON_START の扱い等を慎重に設定してください。
- KabuStationClient を本番で利用する場合は kabuステーション® がローカルで起動しており、API の挙動（状態コード等）に合わせた十分なテストを行ってください。
- DB（SQLite / DuckDB）のパスは環境変数で指定可能です。paper_trading モードでは SQLite を分離して運用します。

---

問題があれば、どの点をより詳しく README に追記したいか教えてください（例: 実行例、.env の具体的なテンプレート、監視 DB のスキーマなど）。