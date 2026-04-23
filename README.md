# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

> 本ドキュメントは、リポジトリ内の主要スクリプト・モジュール実装を元に作成した利用ガイドです。

---

## プロジェクト概要

KabuSys は、日本株向けの自動売買システムのコア部分を提供する Python パッケージです。  
主な目的はシグナルに基づく発注、発注状態管理、リスクガード、発注のリコンシリエーション（復旧）、システム監視、及びニュース／カレンダー等のデータ管理を行うことです。

設計上のポイント:
- 環境変数（.env）ベースの設定管理
- 発注のクラッシュ耐性を考慮した状態遷移と永続化（SQLite）
- 発注 API 層の抽象化（実運用は KabuStation、開発/テストは Mock）
- 3 段階のリスクガード（Gate1/2/3）
- 再起動時の自動リコンシリエーション
- DuckDB を用いた分析用データ管理

現在の実装では、paper_trading / development 環境では MockBrokerClient を利用できます。live 環境向けの完全なブローカークライアントは未実装（NotImplementedError）です。

---

## 主な機能一覧

- 環境設定ウィザード（.env の作成・更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）: python -m kabusys.validate_config
- 発注エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - セッション実行（シグナル処理 / push ドレイン）
  - kill flag による安全停止・全 active 注文のキャンセル
  - 発注状態管理（OrderManager, OrderRecord, OrderRepository）
  - リスク管理（RiskManager: Gate1/2/3）
  - Reconciler による再起動時の自動同期
- 監視ループ起動スクリプト（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング周期を変更可能
  - 監視用 SQLite / DuckDB を使用
- ブローカー抽象化（BrokerAPIProtocol）とモック実装（MockBrokerClient）
- データモジュール: カレンダー管理、ニュース収集など
- YAML ベースの設定ファイルを想定（config/*.yaml）

---

## セットアップ手順（開発者向け）

前提: Python 3.9+（実際の互換性は pyproject.toml を参照）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - ※ 実リポジトリに requirements.txt がない場合は次を参考にインストール:
     - duckdb, httpx, websocket-client, defusedxml, PyYAML（任意: YAML 検証）
   - 標準ライブラリに sqlite3 は含まれます
4. 環境変数ファイル作成
   - 対話式ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
   - 既に .env を手で作成する場合は .env.example を参考に記述する（リポジトリに例がある想定）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict
6. DB 初期化・データフォルダ
   - デフォルトの DB/ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - PID / flag ファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて `data/` ディレクトリを作成してください（多くの箇所で自動作成も行われます）

注:
- 自動的に .env を読み込む処理はデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- .env の読み込み順は OS 環境 > .env.local > .env（.env.local は .env を上書き）。

---

## 必須 / 任意 環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり／用途あり）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知用
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

Settings クラスに各値の既定値や検証ロジックがあります。PAPER_FILL_MODE（paper_trading 用挙動）なども Settings で参照されます。

簡易サンプル .env（参考）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

（.env は絶対にリポジトリにコミットしないでください）

---

## 使い方（主な CLI / スクリプト）

- 環境設定ウィザード（.env 生成／更新）
  - python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml の存在／パースをチェック）
  - python -m kabusys.validate_config
  - オプション:
    - --strict : 警告も失敗扱い（exit code 1）

- 発注エンジン起動（本番/ペーパートレード セッション）
  - python -m kabusys.run_execution
  - 動作:
    - Settings に従って DB 接続を作成
    - BrokerClientFactory により Mock（paper/dev）または live（未実装）クライアントを選択
    - ExecutionEngine.run_session() を別スレッドで実行
    - stop フラグ（data/stop_requested.flag）や kill.flag により安全停止

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング周期を秒単位で変更可（デフォルト 60）

- 開発用に Mock を直接使う場合はコード内で create_broker_api(mock=True, fill_mode=...) を利用

停止／制御:
- エンジン停止フロー:
  - data/stop_requested.flag を作成すると run_* スクリプトのループは検知して終了します
- kill.flag:
  - 実行時に kill.flag（デフォルト: data/kill.flag）が存在する場合、起動を拒否するか（KILL_FLAG_CLEAR_ON_START=0）、
    指示により自動でクリアして起動するか（=1）が選べます

ログ:
- LOG_LEVEL 環境変数で制御。Settings.log_level で検証されます。

注意:
- KABUSYS_ENV=live の場合は追加の本番向けチェックが行われます（LINE 通知設定など）。
- live ブローカークライアントは本実装では未完成で、BrokerClientFactory.create() は NotImplementedError を投げます。

---

## 主要モジュール（簡単な説明）

- kabusys.config
  - Settings クラス: 環境変数読み込み、既定値、バリデーション、.env 自動ロードロジック
- kabusys.config_setup
  - 対話式ウィザードで .env を生成／更新
- kabusys.validate_config
  - 起動前に .env と config/*.yaml を検査する CLI
- kabusys.run_execution
  - ExecutionEngine を組み立ててセッションを実行する起動スクリプト
- kabusys.run_monitoring
  - SystemMonitor のポーリングループを起動するスクリプト
- kabusys.execution
  - broker_api: BrokerAPIProtocol、データモデル、例外、create_broker_api ファクトリ
  - kabu_client: kabu station の REST / WebSocket クライアント実装
  - mock_client: テスト用 MockBrokerClient
  - order_record / order_repository / order_manager: 注文状態管理と永続化
  - execution_engine: シグナル読み込み→発注→push ドレインの全体ロジック
  - reconciler: 再起動時のリコンシリエーション処理
  - risk_manager: Gate1/2/3 のリスク検査
  - broker_factory: Settings に基づくブローカークライアント生成
- kabusys.data
  - calendar_management: 営業日判定、カレンダー更新ジョブ
  - news_collector: RSS からのニュース収集（正規化・前処理・SSRF 対策）
- kabusys.monitoring
  - 監視 DB 初期化、SystemMonitor（監視ロジックは別ファイルに実装されている想定）
- kabusys.utils
  - logging_setup, process_priority などのユーティリティ（ログ設定・プロセス優先度設定）

---

## ディレクトリ構成（抜粋）

プロジェクトルート（例）:
- .env
- .env.local
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - kabusys.duckdb (既定)
  - monitoring.db (既定)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- scripts/
  - generate_config.py  （config/*.yaml を生成する補助スクリプト）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
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
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (想定)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py

（実際のファイルは src/kabusys 以下を参照してください）

---

## 開発・運用上の注意

- .env に機密情報（API トークンやパスワード）を含めるため、決して Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では特に注意が必要:
  - LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。
  - live 用ブローカークライアントは実装が未完のため、本リポジトリのままでは稼働できません。
- 発注フローはクラッシュ耐性（OrderSent の永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を意識して実装されています。Reconciler はクラッシュ復旧を助けます。
- YAML パース検証は PyYAML がインストールされている場合に実行されます。インストールしていない場合は警告が表示されます。

---

## 参考コマンドまとめ

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 発注エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring

---

README は実装に合わせて随時更新してください。必要であれば、各モジュールの API ドキュメント（関数／クラスの説明や例）を追加できます。