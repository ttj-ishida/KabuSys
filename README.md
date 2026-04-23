KabuSys
=======

日本株自動売買システムのサンプル実装（ライブラリ + 実行スクリプト群）。

このリポジトリは、kabuステーション を想定した発注クライアント、発注エンジン、監視コンポーネント、データ収集ユーティリティなどを含みます。実運用を想定した安全ガード（リスク管理 / サーキットブレーカー / kill switch / Reconciliation）を備えています。

主な目的
- 発注フローの設計例（Signal → OrderManager → BrokerAPI → OrderRepository）
- 再起動後の自動復旧（Reconciler）や監視ループの実装例
- テスト用に使える Mock ブローカー（paper_trading / development 向け）
- データ基盤の一部（DuckDB を使ったシグナル / カレンダー処理、ニュース収集）

機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）による .env 生成・更新
- 設定検証ツール（python -m kabusys.validate_config）で起動前チェック（必須環境変数、YAML ファイル、パスなど）
- ExecutionEngine：Signal→発注の一連処理（Gate1..3 のリスクガード、WebSocket push ドレイン、kill switch）
- Broker API 抽象化（BrokerAPIProtocol）と実装:
  - MockBrokerClient：テスト／ペーパートレード用（PAPER_FILL_MODE による振る舞い）
  - KabuStationClient：kabuステーション REST API クライアント（httpx, websocket）
- 発注永続化（SQLite）と OrderRecord の状態遷移ロジック
- Reconciler：OrderSent 状態の復旧、ブローカーとのポジション突合
- 監視ループ（SystemMonitor をポーリング）を起動する run_monitoring スクリプト
- データ系ユーティリティ（マーケットカレンダー管理、RSS ニュース収集等）
- ログ設定とプロセス優先度設定（utils 内モジュール参照）

セットアップ手順（ローカル開発用）
- 前提
  - Python 3.9+（コードは型注釈に Path | None などを使っています）
  - 標準ライブラリ: sqlite3 等は組み込み
  - 推奨パッケージ（別途インストールしてください）:
    - duckdb
    - httpx
    - websocket-client
    - defusedxml
    - PyYAML（config/*.yaml の中身検証を行いたい場合）
  - 例: pip install -r requirements.txt（本リポジトリに requirements.txt がある場合）
    あるいは個別に: pip install duckdb httpx websocket-client defusedxml PyYAML

- プロジェクトルートの確認
  - 自動で .env を読み込む仕組みがあり、プロジェクトルートは .git または pyproject.toml を基準に自動判定されます。
  - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- .env 作成（対話式）
  - 実行: python -m kabusys.config_setup
  - 対話形式で .env（デフォルト: プロジェクトルート/.env）を生成・更新します。
  - ウィザード終了後に .env を保存すると、次に validate_config で検証できます。

- 設定検証
  - 実行: python -m kabusys.validate_config
  - オプション:
    - --strict: 警告も FAIL として扱う（exit code 1）
  - 返り値 / 終了コード:
    - 0: OK（エラーなし、警告なしまたは警告のみ）
    - 1: エラーあり、または --strict として警告あり

使い方（主要スクリプト）
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を作成/更新します（J-Quants トークンや kabu API パスワードなど秘密情報はマスク表示されます）。
  - 保存後は python -m kabusys.validate_config で検証してください。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- 実行エンジン（本番・ペーパートレード）
  - 実行: python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV によって動作が変わります。
    - paper_trading / development: MockBrokerClient を使用（本番 DB と分離して data/paper_trading.db を使用）。
    - live:（未実装）将来 KabuStationClient を本番で利用する想定。
  - 起動時の動作:
    - PID ファイルを書き出し（デフォルト: data/execution.pid）
    - kill.flag の存在チェック（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアも可能）
    - Reconciler によるリカバリ（OrderSent の同期、ポジション差分ログ）
    - Signal の処理（8:50-9:10 にシグナル処理ループ）、WebSocket push のドレイン（9:10-15:30）

- 監視ループ
  - 実行: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を使用します（KABUSYS_ENV に依存せず）。

主要環境変数
- 必須（validate_config によりチェックされる）
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）

- 任意 / 推奨
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
  - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番通知用（live でのアラートに必要）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)（本番は 0 推奨）
  - PAPER_FILL_MODE — paper_trading 時のモックの振る舞い:
    - instant（デフォルト）: 即時全量約定
    - partial: 部分約定（手動で fill_order を呼んで全量約定させることが可能）
    - never: 注文は pending（OrderSentPendingError）となる
    - reject: 発注拒否

.env 読み込みルール
- 自動ロード順: OS 環境 > .env.local（上書き） > .env（未上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化
- .env の形式は export KEY=val / KEY=val / コメント（#）に対応。クォートやエスケープに配慮したパーサを採用。

データベース初期化
- Order / Monitoring DB は接続時にテーブル作成関数（例: init_orders_db, init_monitoring_db）を呼ぶことで冪等に初期化されます。
- DuckDB（分析用）と SQLite（監視・注文履歴）を使用します。デフォルトパスは data/ 配下。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ローダ／Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に基づくクライアント生成
    - kabu_client.py         — KabuStation REST/WebSocket 実装（httpx/websocket）
    - mock_client.py         — テスト用 MockBrokerClient
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 発注フロー（create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine（シグナル処理＋push ドレイン）
    - reconciler.py          — リコンシリエーション（起動時復旧）
    - risk_manager.py        — Gate1..3 のリスクガード
    - ...（その他実装ファイル）
  - data/
    - calendar_management.py — カレンダー管理（DuckDB ベース）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — （参照される外部クライアント実装想定）
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite スキーマ / ログ機能（参照）
  - utils/
    - logging_setup.py      — ログ設定ヘルパ（参照）
    - process_priority.py   — プロセス優先度設定（参照）
  - config/
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml
    （validate_config.py が存在をチェックします。内容の検証には PyYAML が必要）
- data/
  - （実行時に作成されるファイル群: *.db, *.flag, *.pid など）

注意事項・運用上のポイント
- live 環境は慎重に扱ってください。validate_config は KABUSYS_ENV=live のとき追加警告（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START=1 等）を出します。
- .env ファイルは絶対に Git にコミットしないでください（config_setup.py の冒頭コメント参照）。
- ExecutionEngine は kill.flag により安全に停止できます。起動時に既に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START によって起動挙動が変わります。
- Reconciler により起動時に OrderSent 状態の注文をブローカー側と突合して同期します。これによりクラッシュ後の不整合を軽減します。
- Paper trading / development 環境では MockBrokerClient が利用できます。PAPER_FILL_MODE を変更して挙動を試験してください。

例: よく使うコマンド
- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実際にエンジンを起動（ローカルテスト）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=10 などで間隔を変更

その他
- YAML 設定（config/*.yaml）はプロジェクトの挙動を細かく制御するため想定されています。validate_config は存在とパース可否をチェックします（PyYAML がインストールされている場合）。
- 本リポジトリは実稼働向けテンプレート／サンプルを兼ねていますが、本番でそのまま使う前に必ずコードレビュー・セキュリティ監査を行ってください（特に API キー管理、ネットワーク設定、DB の権限等）。

ライセンス / 貢献
- （ここにプロジェクトのライセンスや貢献方法を記載してください）

以上。必要であれば README に「環境変数の完全一覧」「.env.example のサンプル」「詳細な DIAGRAM（フロー図）」「各モジュールの API/戻り値説明」などを追加できます。どれを追記しましょうか？