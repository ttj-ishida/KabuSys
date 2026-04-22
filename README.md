KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリおよび実行スクリプト群です。  
主に以下を提供します。

- 環境変数/.env 管理ウィザード（対話式）および起動前検証ツール
- 発注エンジン（ExecutionEngine）と実行ループ
- ブローカークライアント抽象化（Mock / kabu station クライアント）
- 注文状態管理（OrderRecord の状態機械）と永続化（SQLite）
- リコンシリエーション（クラッシュ復旧）機能
- リスクガード（Gate1/2/3）
- 監視ループ（SystemMonitor）を起動するランナー
- データ関連モジュール（マーケットカレンダー管理、ニュース収集など）

特徴
----
- 明示的な環境設定（.env）と自動ロード機構（プロジェクトルートの .env / .env.local）
- 発注フローのクラッシュ耐性（OrderSent の 2 相永続化など）
- 3 段階リスクガード（シグナル、実行、約定後メトリクス）
- 開発/ペーパートレード向けに MockBrokerClient を用意（本番クライアントは将来実装予定）
- 起動前設定検証ツール（PyYAML があれば config/*.yaml のパース検証も実施）
- 起動時リコンシリエーションにより OrderSent 状態の注文をブローカーと突合

セットアップ
----------
前提
- Python 3.10 以上（Path|None や型ヒントの表記から）
- sqlite3 は標準モジュール、その他いくつか外部パッケージが必要

推奨パッケージ（主な依存）
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（任意、validate_config で YAML 検証を行いたい場合）

例: pip インストール
```
python -m pip install "duckdb" "httpx" "websocket-client" "defusedxml" "PyYAML"
```

プロジェクトルート
- リポジトリをクローン後、プロジェクトルートに .env を配置します。
- .env は Git 管理しないこと（config_setup はヘッダで注意を出します）。

.env の初期作成（対話式）
```
python -m kabusys.config_setup
```
ウィザードは既存の .env を読み込み、対話式で値を更新して保存します。

起動前検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
```
validate_config は必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在と（PyYAML がある場合）パースをチェックします。

重要な環境変数（代表）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（よく使われるもの）:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - KABU_API_BASE_URL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番通知用）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）

主要な使い方
----------

1) 監視プロセス起動（SystemMonitor のポーリング）
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視DBは常に本番 DB を参照）。

停止方法
- data/stop_requested.flag ファイルを作成すると各ランナーは検知して終了します。

2) ExecutionEngine 起動（取引セッション）
```
python -m kabusys.run_execution
```
- KABUSYS_ENV によって挙動が変わります：
  - development / paper_trading -> MockBrokerClient を用いる（実際の発注文は行われない）
  - paper_trading -> paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録
  - live -> 現状 NotImplementedError（本番クライアントは未実装。将来対応）
- エンジンはシグナル処理（8:50–9:10）→ WebSocket ドレイン（9:10–15:30）というセッションフローを持ちます。
- 起動時に kill.flag が存在すると設定により起動拒否または自動クリアされます。

3) .env の自動ロード
- config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  .env（上書き不可）→ .env.local（上書き可）の順で自動ロードします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

内部の主要コンポーネント（概要）
--------------------------------
- kabusys.config
  - .env 読み込みロジック、Settings クラス（各種設定をプロパティで提供）
  - 必須チェックで未設定なら ValueError を発生させます

- kabusys.config_setup
  - 対話式ウィザードで .env を生成/更新する

- kabusys.validate_config
  - 起動前に環境変数や config/*.yaml を検証する CLI

- kabusys.run_execution
  - ExecutionEngine 組み立てと実行ループ起動スクリプト

- kabusys.run_monitoring
  - SystemMonitor ポーリングループ起動スクリプト

- kabusys.execution
  - broker_api: BrokerAPIProtocol、データモデル（OrderRequest/Response/Status/Position）、例外、create_broker_api ファクトリ
  - kabu_client: kabu station REST API 実装（httpx、WebSocket 対応）
  - mock_client: テスト用の MockBrokerClient（fill_mode を指定可能）
  - broker_factory: Settings に基づいて適切なクライアントを返す
  - order_record: OrderState（状態機械）と OrderRecord データモデル（純粋ロジック）
  - order_repository: SQLite ベースの永続化。init_orders_db でテーブル作成
  - order_manager: 作成→送信→同期→取消 のフローを実装（クラッシュ耐性を意識）
  - execution_engine: シグナル読み込み、Gate1/2 のチェック、発注・push ドレイン、kill_switch 等
  - reconciler: 起動時の OrderSent リカバリとポジション差分の照合
  - risk_manager: Gate1/2/3（余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン）

- kabusys.data
  - calendar_management: JPX カレンダー管理（DuckDB ベース）、next_trading_day 等のユーティリティ
  - news_collector: RSS 収集・正規化・DB 保存ロジック（SSRF 対策・XML デフューズ等）

- kabusys.monitoring
  - 監視用 DB 初期化や SystemMonitor 実装（run_monitoring から利用）

- kabusys.utils
  - logging_setup, process_priority など（各ランナーで呼ばれるユーティリティ）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

src/kabusys/execution/
- __init__.py
- broker_api.py
- kabu_client.py
- mock_client.py
- broker_factory.py
- order_record.py
- order_repository.py
- order_manager.py
- execution_engine.py
- reconciler.py
- risk_manager.py
- order_record.py
- order_repository.py
- ...（その他補助モジュール）

src/kabusys/data/
- calendar_management.py
- news_collector.py
- ...（jquants_client 等を含む想定）

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- ...（監視関連）

注意事項 / 運用上のポイント
------------------------
- .env は決してリポジトリにコミットしないでください（config_setup にも注意書きあり）。
- KABUSYS_ENV=live を使う場合は特に注意してください（validate_config は live で警告を出します）。ただし現状 live 用ブローカークライアントは未実装です。
- 停止は data/stop_requested.flag を作ることで実現します（run_execution / run_monitoring はこれを監視）。
- ExecutionEngine は起動時に PID ファイルを書き、終了時に削除します（Settings で pid_file_path を設定可能）。
- 発注のクラッシュ耐性: OrderManager は OrderSent 状態を先に永続化し、broker_order_id を永続化→OrderAccepted 更新という流れで 2 相の安全性を確保します。リコンシリエーションで残留状態を復旧します。

サンプル .env（最小）
--------------------
以下は .env の最小例です（実際は config_setup を使うことを推奨します）。
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

トラブルシューティング
----------------------
- validate_config で警告やエラーが出る場合は、指示に従って .env を修正してください。
- PyYAML が未インストールだと config/*.yaml の中身チェックはスキップされます（警告が出ます）。YAML 検証を有効にしたい場合は PyYAML をインストールしてください。
- run_execution の起動で「停止フラグを検知」と出る場合、data/stop_requested.flag や kill.flag が残っていないか確認してください。
- Live ブローカー実装は現状未実装の箇所があるため、本番運用前に十分なテストとレビューを行ってください。

さらに詳しく
--------------
各モジュール（execution/*.py、data/*.py、monitoring/*.py）に詳細なドキュメント文字列と設計注記が含まれています。実装の挙動やデータモデル（OrderRequest、OrderStatus、Position など）はソースコード内の docstring を参照してください。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を記載してください。リポジトリに LICENSE があれば参照する旨を追記してください）

問い合わせ
----------
不明点やバグ報告はリポジトリの Issue を使ってください。README の追加要望・改善提案も歓迎します。