# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
このリポジトリは発注ロジック、リスクガード、リコンシリエーション、監視ループ、データ処理（カレンダー・ニュース収集）等を含む設計を提供します。実際の本番接続は想定せず、ペーパートレード用のモック実装で動作確認が可能です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - .env 設定ウィザード
  - 設定検証
  - 実行（Execution / Monitoring）
- 環境変数（重要項目）
- ディレクトリ構成
- その他の注意点 / トラブルシュート

---

プロジェクト概要
- 発注エンジン（ExecutionEngine）: シグナルを読み込み Gate1/2/3 のリスクチェックを通して発注を行います。WebSocket の push を受け取り約定同期も行います。
- 注文永続化: SQLite を用いた OrderRepository（orders テーブル）。
- ブローカークライアント: MockBrokerClient（テスト／ペーパートレード用）と実装予定の KabuStationClient（kabuステーションAPI）の抽象化。
- リスク管理: 3 段階リスクガード（シグナル・実行・メトリクス）。
- リコンシリエーション: 再起動時に OrderSent 状態の注文を突合し復旧。
- 監視（Monitoring）: SystemMonitor ポーリングループ（SQLite + DuckDB 使用）。
- データ: マーケットカレンダー管理、RSS ニュース収集などのユーティリティ。

機能一覧
- .env 対話式ウィザード（kabusys.config_setup）
- 起動前の設定検証 CLI（kabusys.validate_config）
- ExecutionEngine（発注セッションの実行）
- Monitoring ポーリングループ（システム監視）
- Mock ブローカークライアント（ペーパートレード用）
- 注文状態モデル（OrderRecord）と状態遷移の厳密管理
- リスクマネージャ（レート制限、サーキットブレーカー、ドローダウン監視）
- カレンダー管理（J-Quants API 連携想定）
- ニュース収集（RSS、SSRF/XML 対策を考慮）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 必要なパッケージ例（プロジェクトに requirements.txt が無い場合の目安）:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (YAML 検証用、任意)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml
   - 標準ライブラリ: sqlite3, logging 等は追加インストール不要
4. .env を作成（下記ウィザード参照）または環境変数を設定
5. 必要なら data ディレクトリを作成:
   - mkdir -p data

使い方

- .env 設定ウィザード（対話形式）
  - コマンド:
    - python -m kabusys.config_setup
  - 説明:
    - 対話で必須/任意の環境変数を埋め、.env を生成します。
    - 生成された .env は Git にコミットしないでください（README 内にも警告あり）。
  - 主要な項目（ウィザードで扱う）:
    - KABUSYS_ENV (development / paper_trading / live)
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意）
    - LOG_LEVEL
    - KILL_FLAG_CLEAR_ON_START

- 設定検証 CLI
  - コマンド:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict  （警告を FAIL 扱い）
  - 概要:
    - .env と config/*.yaml を起動前にチェックします。
    - 必須環境変数の未設定、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・YAML パース（PyYAML インストール時）等を出力します。
  - 返り値 / 終了コード:
    - エラーがあると exit(1)
    - 警告のみで --strict を付けると exit(1)
    - 正常なら exit(0)

- 実行（ExecutionEngine）
  - コマンド:
    - python -m kabusys.run_execution
  - 概要:
    - Settings から環境を読み取り、DB 接続、BrokerClient（mock）生成、各コンポーネント組み立てを行いセッションを実行します。
    - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient が使われます。live は未実装で例外となります。
    - 実行中は data/execution.pid（デフォルト）に PID を書き、data/stop_requested.flag により停止できます。
  - 注意:
    - kill.flag（設定で指定されたパス）が存在すると起動拒否または自動クリア挙動が設定に依存します。

- 監視（Monitoring）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 概要:
    - SystemMonitor のポーリングループを起動し、指定間隔でシステム情報を収集して監視 DB に格納します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

環境変数（重要）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 任意かつ推奨:
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
  - KABU_API_BASE_URL — kabu station のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知用
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1）
- 注意:
  - 自動で .env を読み込む仕組みが内蔵されています（プロジェクトルートに .env/.env.local がある場合）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要なファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動
  - execution/
    - __init__.py
    - broker_api.py          — Broker API のデータモデル・Protocol・ファクトリ
    - kabu_client.py         — kabu station REST API クライアント実装
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に基づくクライアント生成
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 上位 API（発注フロー）
    - execution_engine.py    — 発注エンジン（セッション制御）
    - reconciler.py          — 再起動時のリコンシリエーション
    - risk_manager.py        — 3 段階のリスクガード
  - data/
    - calendar_management.py — 営業日判定・カレンダー更新ロジック
    - news_collector.py      — RSS ニュース収集
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・書き込み（参照のみ）
    - system_monitor.py      — SystemMonitor（参照）
  - utils/
    - logging_setup.py       — ログ設定（参照）
    - process_priority.py    — プロセス優先度設定（参照）

サンプル .env（.env の例）
- .env の主要な行例:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_api_password
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0

その他の注意点 / トラブルシュート
- PyYAML がインストールされていない場合、validate_config は config/*.yaml の中身チェックをスキップします（存在確認のみ）。
- run_execution は paper_trading / development で MockBrokerClient を利用します。live は現状未実装（BrokerFactory が NotImplementedError を投げます）。
- stop/kill フラグ:
  - data/stop_requested.flag: 監視・実行ループを外部から停止するためのフラグファイル
  - KILL_FLAG (設定により異なる): 発注停止（kill switch）のトリガー
- DB ファイルの親ディレクトリが存在しない場合、起動時に自動作成される場合がありますが、事前に data ディレクトリを作成しておくと安心です。
- ログレベルや各種閾値は環境変数で変更できます（LOG_LEVEL, CPU_THRESHOLD_PCT 等）。

ライセンス / 責任
- 本リポジトリは教育・実験目的を想定したサンプル実装です。実際の資金での運用は十分なレビュー・テストを実施してください。実運用に際しては法令遵守・取引所規約・ブローカー条件を確認してください。

---

この README はソース内の docstring・実装に基づき作成しました。実際に使う際はプロジェクト固有の README や仕様書（DataPlatform.md 等）があれば併せて参照してください。