KabuSys — 日本株自動売買システム（README）
概要
- KabuSys は日本株の自動売買（エグゼキューション）とシステム監視を目的とした Python ベースの小規模フレームワークです。
- モジュール構成は「設定管理」「データ処理」「発注/ブローカー抽象化」「実行エンジン」「監視」などに分かれており、開発（development）、ペーパートレード（paper_trading）、本番（live）の環境を想定しています。
- 本リポジトリは、kabuステーション（実ブローカー）接続用クライアントや、テスト用の MockBrokerClient を含み、起動前の設定検証・対話式 .env 作成ウィザードも備えます。

主な機能
- 環境設定の自動読み込みと対話式ウィザード（.env の生成 / 更新）
- 起動前の設定検証 CLI（環境変数・config/*.yaml の存在/パース検査）
- ExecutionEngine：Signal→発注フロー（Gate1/2/3 のリスクガード、リコンシリエーション、WebSocket push 処理）
- Broker 抽象化：KabuStationClient（実装）と MockBrokerClient（テスト用）
- 注文管理：OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（発注ワークフロー）
- リスク管理：3 段階（シグナルレベル / エグゼキューションレベル / メトリクスレベル）
- リコンシリエーション（起動時に OrderSent 状態の注文をブローカーと突合）
- データユーティリティ：マーケットカレンダー管理（DuckDB ベース）、ニュース収集（RSS）
- 監視用プロセス（run_monitoring）と監視 DB 初期化ユーティリティ

動作要件（概略）
- Python 3.9+（型アノテーション等を利用）
- 推奨パッケージ（機能により必要）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証に必要）
  - defusedxml（news_collector で使用）
- OS 環境変数や .env/.env.local ファイルを利用して設定します。

セットアップ手順（例）
1. リポジトリをクローン
   - git clone <repo> && cd <repo>
2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ requirements.txt が無い場合は上記の必須パッケージを個別にインストールしてください。
4. データディレクトリ作成
   - mkdir -p data
   - （初回起動時に自動作成されるケースもありますが、手動作成を推奨）
5. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（.env を絶対に Git にコミットしないでください）
6. 設定の検証
   - python -m kabusys.validate_config
   - 警告やエラーを確認。--strict を付けると警告も失敗扱いで exit(1) になります:
     - python -m kabusys.validate_config --strict
7. 実行
   - 実際にエンジンを起動する前に .env と DB の準備を必ず確認してください（monitoring / orders テーブルは起動スクリプトで自動作成されます）。

使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話式に生成 / 更新します。
    - 作成後、python -m kabusys.validate_config で検証してください。
- 設定検証 CLI
  - python -m kabusys.validate_config
  - オプション:
    - --strict : 警告も FAIL として exit(1) を返す
  - 主に .env の必須環境変数・KABUSYS_ENV の妥当性・config/*.yaml の存在と YAML パース（PyYAML が必要）をチェックします。
- 実行エンジン（Trading）
  - python -m kabusys.run_execution
    - ExecutionEngine を開始します。KABUSYS_ENV により挙動が変わります。
    - paper_trading / development では MockBrokerClient が使われ、本番 DB とペーパートレード DB は分離されます。
    - stop フラグ: data/stop_requested.flag が存在すると停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）
- 監視プロセス
  - python -m kabusys.run_monitoring
    - SystemMonitor のポーリングループを動かします（デフォルト 60秒間隔）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
    - 同様に stop フラグ data/stop_requested.flag を見て停止します。

主な環境変数（validate_config / config.py より）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（デフォルトあり/無くても動作するもの）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN（本番でのアラートに必要）
  - LINE_USER_ID（本番でのアラート先）
  - KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0）
- その他:
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数）
  - PAPER_FILL_MODE（ペーパートレードでの約定モード: instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite）

設定ロードの挙動
- 自動ロード順序:
  - OS 環境変数（既存の環境変数） を最優先
  - プロジェクトルート/.env をロード（既定では override=False、未設定キーのみセット）
  - プロジェクトルート/.env.local をロード（override=True、既存 OS 環境変数は protected）
- 自動ロードを無効にする:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

動作・設計上の重要点（運用メモ）
- KABUSYS_ENV=live の場合は本番運用となり、LINE 通知設定や Kill Switch の確認を徹底してください。
- kill.flag（Settings.kill_flag_path）:
  - ExecutionEngine 起動時に存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動可能）
  - 运行中に検出されると kill_switch() が発動し、全 active 注文をキャンセルして停止します
- Paper trading:
  - settings.is_paper の場合、MockBrokerClient を使用し data/paper_trading.db に記録／本番 DB と分離
- 発注の耐障害設計:
  - OrderManager は OrderCreated → OrderSent → broker 呼び出し → broker_order_id 永続化 → OrderAccepted といった 2 相永続化を採用し、クラッシュ時の復旧（Reconciler）を考慮しています。
- YAML 設定ファイル:
  - config/*.yaml（system_config.yaml 等）が必要な場合があります。validate_config は PyYAML が無い場合は YAML 検証をスキップします。
  - config ファイル生成スクリプト（generate_config.py）に関するメッセージが出ます（該当スクリプトがプロジェクトにある場合はそれを利用）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings（アプリ全体の設定取得）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前の設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - broker_api.py — Broker API のデータモデル、Protocol、ファクトリ
    - kabu_client.py — KabuStationClient（実 API クライアント）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づきブローカークライアント生成
    - order_record.py — Order の状態マシン（遷移ロジック）
    - order_repository.py — SQLite 永続化（orders テーブル定義・CRUD）
    - order_manager.py — 発注ワークフロー（Order 作成・送信・同期・キャンセル）
    - execution_engine.py — ExecutionEngine（シグナル処理、push ドレイン、セッション制御）
    - reconciler.py — 起動時リコンシリエーション（OrderSent 照合、ポジション差分検出）
    - risk_manager.py — 3 段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集と前処理
    - jquants_client.py — （参照あり。J-Quants API クライアント実装を想定）
  - monitoring/
    - monitoring_db.py — 監視DB 初期化 / ログ記録（run_* で使用）
    - system_monitor.py — システム監視ロジック（run_monitoring で使用）
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

注意事項 / ベストプラクティス
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- 本番環境（KABUSYS_ENV=live）を利用する際は LINE 通知等の監視経路、KILL_FLAG 設定を十分確認してください。validate_config の警告・注意メッセージに従ってください。
- ペーパートレードと本番 DB は分離されています。paper_trading を使うことで本番に影響を与えずに動作検証が可能です。
- 依存ライブラリ（httpx / websocket-client / duckdb / PyYAML / defusedxml 等）は各機能で必要になります。CI やデプロイ環境では required パッケージを適切にインストールしてください。

この README はコードベースの主要な使い方と設計上のポイントをまとめたものです。詳細な API 仕様や追加のユーティリティ（generate_config.py、モニタリング詳細、J-Quants クライアント等）は該当モジュールのドキュメントやソースコメントを参照してください。質問や補足が必要であれば教えてください。