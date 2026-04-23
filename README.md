KabuSys — 日本株自動売買システム (README)
========================================

概要
----
KabuSys は日本株向けの自動売買システムのコア部分（設定管理、実行エンジン、監視、ブローカークライアント、データ処理ユーティリティ等）を提供する Python パッケージです。  
設計は本番（live）・ペーパートレード（paper_trading）・開発（development）を区別し、安全性（Kill Switch、リスクゲート、リコンシリエーション等）を重視しています。

主な機能
--------
- 環境変数 / .env の対話式セットアップ（config_setup）
- 起動前に設定を検証する CLI（validate_config）
  - 必須環境変数の確認、KABUSYS_ENV やログレベルの妥当性、データベースパス、config/*.yaml の存在と YAML パース（PyYAML がある場合）
- 実行エンジン（run_execution）
  - シグナルに基づく発注フロー（Signal Pull）と WebSocket push のドレイン
  - 3段階リスクガード（Gate1: シグナル、Gate2: 実行/レート制限/サーキットブレーカー、Gate3: ドローダウン監視）
  - ペーパートレード時は MockBrokerClient を用い、本番 DB と分離して動作
  - 起動時のリコンシリエーション（OrderSent の同期、ポジション差分検査）
  - Kill Switch（ファイルベース）による安全停止と全 active 注文のキャンセル
- 監視ループ（run_monitoring）
  - 定期的にシステムリソースや監視イベントを記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能
- ブローカークライアント層
  - 実装: KabuStationClient（kabuステーション REST API）および MockBrokerClient（テスト用）
  - BrokerAPIProtocol に従うファクトリ create_broker_api
- データユーティリティ
  - DuckDB を用いたマーケットカレンダー管理、ニュース収集等
- 注文永続化: SQLite を用いた orders テーブル（order_repository）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb httpx websocket-client defusedxml
   - pyYAML は validate_config の YAML 内容検証を有効にする場合に必要:
     - pip install PyYAML
   - （プロジェクトで requirements.txt があれば）pip install -r requirements.txt

4. .env の初期作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を配置
   - 重要: .env は決してリポジトリにコミットしないでください（.env は Git 管理対象外に）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

基本的な使い方
-------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を作成・更新します。シークレット項目はマスク表示されます。

- 設定検証
  - python -m kabusys.validate_config
  - 必須環境変数や config/*.yaml の存在・パースなどをチェックします。

- 実行エンジンを起動（本番/ペーパー共通起動スクリプト）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient を使用（development / paper_trading）または（未実装）Live ブローカを使用
  - 起動前に data/stop_requested.flag が存在すると起動を中止します
  - 実行中、data/execution.pid に PID を書き込みます
  - kill.flag（設定で指定）により kill_switch を発動可能

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）を環境変数で上書き可能（デフォルト 60）
  - 監視は SQLite（settings.sqlite_path）および DuckDB を用います（monitoring は環境にかかわらず本番 sqlite_path を使用）

主要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - live を指定すると本番向けの注意喚起や追加チェックが行われます
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL: kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（本番では設定推奨）
- KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 を推奨。1 は起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）

.env 例（最低限の必須項目）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

重要な挙動メモ
---------------
- Paper trading（KABUSYS_ENV=paper_trading）は MockBrokerClient を使用し、履歴は PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
- ExecutionEngine は以下の時間で動作を想定:
  - シグナル処理: 08:50 ～ 09:10
  - WebSocket ドレイン: 09:10 ～ 15:30
- Kill Switch はファイルベース（settings.kill_flag_path）。存在すると発注ループを止め、全 active 注文をキャンセルします。
- リコンシリエーション（Reconciler）は起動時に OrderSent の未確定注文をブローカーと突合して同期します。
- validate_config は PyYAML が無ければ YAML 内容検証をスキップしますが、ファイルの存在は警告します。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数/.env 自動ロードと Settings クラス
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
- execution/
  - __init__.py
  - broker_api.py            — Broker API のデータモデル・Protocol・ファクトリ
  - broker_factory.py        — Settings に基づくクライアント生成
  - kabu_client.py           — kabu station REST API クライアント
  - mock_client.py           — MockBrokerClient（テスト用）
  - order_record.py          — 注文状態モデルと遷移ロジック
  - order_repository.py      — SQLite 永続化層（orders テーブル）
  - order_manager.py         — 発注フローの外向け API（create/send/sync/cancel）
  - execution_engine.py      — セッション管理・シグナル処理・push ドレイン
  - reconciler.py            — 起動時リコンシリエーション
  - risk_manager.py          — 3段階リスクチェック
  - ...（その他関連モジュール）
- data/
  - calendar_management.py   — マーケットカレンダー管理（DuckDB）
  - news_collector.py        — RSS 収集 / raw_news 保存（セキュリティ対策あり）
  - ...（J-Quants クライアント等）
- monitoring/
  - monitoring_db.py         — 監視用 DB 初期化・書き込み
  - system_monitor.py        — システム監視ロジック
- utils/
  - logging_setup.py         — ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度設定ユーティリティ
  - ...（その他ユーティリティ）

運用上の注意
------------
- .env を誤ってコミットしないこと（README 内でも強調）。秘匿情報は適切に管理してください。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の設定を必ず確認してください（validate_config は live で追加チェックを行います）。
- 実機のブローカークライアント（KabuStationClient）を使う場合は kabu ステーションが PC 上で稼働している必要があります。
- リソースや DB のパスは環境変数で柔軟に変更可能です。必要に応じて監視や監査ログを整備してください。

開発者向けメモ
---------------
- MockBrokerClient は fill_mode（instant / partial / never / reject）をサポートし、ユニットテスト用に細かい挙動を制御できます。
- OrderManager の send_order フローはクラッシュ安全性を考慮した「2相永続化」設計（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）になっています。
- DuckDB を用いたデータアクセスは SQL で記述されており、バックテストや分析への拡張が容易です。

貢献・ライセンス
-----------------
プロジェクトの貢献やライセンス情報がある場合はここに追記してください。

以上。ソースコード内のドキュメント（docstring）に詳細な実装方針や注意事項が記載されていますので、実行や拡張の際に参照してください。必要であれば README を英語化する、またはセットアップスクリプトや requirements.txt を整備する手伝いもできます。