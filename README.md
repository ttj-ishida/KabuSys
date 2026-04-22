# KabuSys

日本株自動売買システムのコアライブラリ（README 日本語版）

※ 本 README はソースツリー内のスクリプト群（環境設定、検証、実行エントリポイント、実行ロジック、モック実装、監視など）に基づいて作成しています。

## プロジェクト概要

KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。  
主な設計方針は次のとおりです。

- 発注ロジックと永続化（SQLite）を分離し、再起動後の自動復旧（Reconciliation）をサポートする。
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を環境変数で切り替え可能。
- レート制限・サーキットブレーカー・ドローダウン監視などの多層リスクガードを備える。
- 本番に依存しない開発用モック（MockBrokerClient）を用意し、テスト実行が可能。
- DuckDB を利用したデータ処理（シグナル取得・ポジション管理）を想定。

## 機能一覧

- 環境設定ウィザード（.env 作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine（発注エンジン）: python -m kabusys.run_execution
  - シグナルプル型発注（指定時間帯）
  - WebSocket push ドレイン（kabu station push 想定）
  - kill-switch / PID 管理
- SystemMonitor（監視ループ）: python -m kabusys.run_monitoring
  - CPU/メモリ/ディスク閾値監視、監視DB（SQLite）へのログ
- Broker クライアント群
  - KabuStationClient: kabuステーション REST API 実装
  - MockBrokerClient: テスト用モック（fill_mode により即時／部分／保留／拒否を再現）
- 注文永続化（SQLite）: OrderRepository, init_orders_db
- 起動時リコンシリエーション: Reconciler（OrderSent 状態の突合、ポジション差分検出）
- マーケットカレンダー管理（DuckDB 上）: is_trading_day / next_trading_day 等
- RSS ニュース収集（安全対策付き）: news_collector（defusedxml 等で保護）

## 必要条件（推奨）

- Python >= 3.10
- pip
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の中身を検証したい場合）
  
インストール例:
  pip install duckdb httpx websocket-client defusedxml PyYAML

（requirements.txt は本リポジトリに含まれていない想定のため、必要に応じて追加してください）

## セットアップ手順

1. リポジトリをクローン／配置する

2. Python 仮想環境を作成してアクティブ化（任意）
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

3. 依存パッケージをインストール
   pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env 作成（対話式ウィザード）
   python -m kabusys.config_setup
   - 対話ウィザードは .env（デフォルト）を生成または更新します。
   - 生成後、必ず `python -m kabusys.validate_config` で検証してください。

5. 設定検証
   python -m kabusys.validate_config
   - --strict フラグを付けると警告も FAIL 扱いして exit(1) になります。

## 環境変数一覧（主要）

必須（起動前に設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（本番で推奨）
- LINE_USER_ID — LINE 通知先（本番で推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアする（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意事項:
- KABUSYS_ENV=live を使う場合は本番環境向けの設定（LINE トークン等）を確認してください。validate_config は live の場合に追加警告を出します。
- .env は絶対に Git へコミットしないでください（config_setup もその注意喚起を出します）。

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を生成/更新）
  python -m kabusys.config_setup
  - 対話式に必要項目を入力して .env を保存します。

- 設定検証（.env と config/*.yaml の存在／簡易検証）
  python -m kabusys.validate_config
  - --strict をつけると警告で exit(1) となる。

- 実行エンジン（発注）を起動（通常は systemd 等で運用）
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading のときは MockBrokerClient を使い、paper_trading 用 SQLite（data/paper_trading.db）を使用します。
  - 起動前に data ディレクトリの書き込み権限を確認してください。
  - stop は data/stop_requested.flag を作成することで行います（スクリプトはこのファイルを監視します）。

- 監視ループを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）。
  - 監視は settings.sqlite_path を使用（環境にかかわらず本番 sqlite_path を参照する設計）。

- 開発・テスト用の MockBroker 操作
  - MockBrokerClient には fill_mode（instant/partial/never/reject）があり、PAPER_FILL_MODE 環境変数で設定できます（Settings.paper_fill_mode）。
  - MockBrokerClient にはテスト操作メソッド（fill_order 等）もあります。ユニットテストでの利用を想定。

## 安全と運用上の注意

- kill.flag（KILL_FLAG_PATH、デフォルト data/kill.flag）は手動停止や Kill Switch のトリガとなります。KILL_FLAG_CLEAR_ON_START=1 を本番で使うと起動時にこれを自動クリアしてしまうため注意してください。
- config_setup の出力メッセージにもある通り、.env をリポジトリに含めないこと。
- KABUSYS_ENV=live は本番発注を行います。十分な検証と監査の上で使用してください。
- validate_config は PyYAML 未インストール時に YAML パース検証をスキップします。config/*.yaml の検証を行う場合は PyYAML を入れてください。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数読み取り・Settings クラス、自動 .env ロードロジック
- config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py — 起動前設定検証ツール（python -m kabusys.validate_config）
- run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
- run_monitoring.py — SystemMonitor 起動スクリプト（python -m kabusys.run_monitoring）

サブパッケージ（主要）
- execution/
  - broker_api.py — Broker API の Protocol / データモデル / 例外 / create_broker_api ファクトリ
  - kabu_client.py — kabuステーション REST API 実装（KabuStationClient）
  - mock_client.py — MockBrokerClient（開発用）
  - broker_factory.py — Settings から Broker クライアントを生成するファクトリ
  - order_record.py — 注文状態モデルと状態遷移ロジック（純粋ビジネスロジック）
  - order_repository.py — SQLite 永続化層（orders テーブルの初期化関数含む）
  - order_manager.py — Order 管理（発注ワークフロー）
  - execution_engine.py — ExecutionEngine（セッション管理・シグナル処理・push ドレイン等）
  - reconciler.py — 起動時リコンシリエーション（OrderSent の突合、ポジション差分）
  - risk_manager.py — 3段階リスクガード（Gate1/2/3）
- data/
  - calendar_management.py — 市場カレンダー（DuckDB）管理ロジック
  - news_collector.py — RSS ニュース収集（XML セキュリティ・SSRF 対策含む）
  - jquants_client.py (想定) — J-Quants API 用クライアント（ソース内で参照）
- monitoring/
  - monitoring_db.py (想定) — 監視用 SQLite テーブル初期化 / ログ関数
  - system_monitor.py (想定) — システムリソース監視ロジック
- utils/
  - logging_setup.py (想定) — ロギング初期化ユーティリティ
  - process_priority.py (想定) — プロセス優先度設定ユーティリティ
- strategy/, data/ etc. — 戦略/データ処理用コード（本リポジトリ全体の構成に依存）

（注）上の "(想定)" とあるファイルはソース内参照があることから実際のリポジトリに存在するはずのモジュールです。実行前に当該ファイルが存在することを確認してください。

## 開発メモ / よくある操作

- DB 初期化
  - monitoring DB の初期化は run_execution/run_monitoring 内で init_monitoring_db(sqlite_conn) が呼ばれるため、通常は個別実行で不要です。
  - orders テーブルの初期化関数 init_orders_db(conn) は order_repository.py にあります。手動で初期化したい場合は Python REPL で呼び出してください。

- ログレベル
  - LOG_LEVEL 環境変数で調整（INFO デフォルト）。開発時は DEBUG を推奨。

- モック動作確認
  - KABUSYS_ENV=paper_trading または development で MockBroker を利用。PAPER_FILL_MODE で挙動（instant/partial/never/reject）を制御。

## トラブルシュート

- validate_config がエラーを返す
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定の可能性があります。.env を確認し、config_setup で再設定してください。
  - config/*.yaml が見つからない／パースエラーがある場合は警告／エラーが出ます。PyYAML が入っているか確認してください。

- 実行がすぐ終了する / 起動しない
  - data/ ディレクトリと指定された DB ファイルパス（DUCKDB_PATH/SQLITE_PATH）に対する書き込み権限を確認してください。
  - kill.flag（data/kill.flag）が残っていると起動が拒否されることがあります。KILL_FLAG_CLEAR_ON_START を 1 にすることで自動クリアできますが、本番では推奨しません。

---

その他の詳細は各モジュールの docstring / ソース内コメント（日本語）を参照してください。必要に応じて README を追記し、運用手順や systemd ユニット、監視・バックアップ方針などを補完してください。