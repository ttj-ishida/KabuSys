README
======

概要
----
KabuSys は日本株自動売買を想定したモジュール群です。  
主に以下を提供します。

- 環境変数/.env ベースの設定管理と対話型ウィザード
- 起動前の設定検証 CLI
- 発注エンジン（ExecutionEngine）とその周辺の注文管理・リスクガード・リコンシリエーション
- kabuステーション向けクライアント実装（同期 HTTP + WebSocket）およびテスト用モック
- 監視プロセス（SystemMonitor）起動スクリプト
- データ処理（マーケットカレンダー、ニュース収集）等のユーティリティ

設計方針の要点：
- DB は SQLite（監視・注文永続化）と DuckDB（分析・シグナルソース）を併用
- 環境により MockBrokerClient を使い分けて本番 API と分離（paper_trading / development は mock）
- 発注の耐障害性（2相永続化、リコンシリエーション）を重視

主な機能
--------
- .env 作成/更新ウィザード（python -m kabusys.config_setup）
- .env および config/*.yaml の起動前検証（python -m kabusys.validate_config）
  - --strict オプションで警告もエラー扱いに
- ExecutionEngine（run_execution.py）
  - シグナル処理（8:50–9:10）および WebSocket プッシュドレイン（9:10–15:30）
  - OrderManager / OrderRepository / RiskManager / Reconciler を組合せて発注フローを管理
- Monitoring（run_monitoring.py）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
- Broker クライアント群
  - KabuStationClient（実装、HTTP + WebSocket）
  - MockBrokerClient（テスト用、fill_mode 制御）
  - create_broker_api / BrokerClientFactory により環境に応じて生成
- データ関連
  - calendar_management: 営業日判定、next_trading_day など
  - news_collector: RSS 収集と前処理（SSRF 対策、正規化、ID 生成 等）

セットアップ
----------
必須（最低限）
- Python 3.9+（型ヒントに | 記法や typing の最新機能を使用）を推奨
- duckdb, httpx, websocket-client, defusedxml などの外部パッケージ（下記参照）

推奨インストール例
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使う）
   - pip install duckdb httpx websocket-client defusedxml
   - 任意（validate_config の YAML 検証を有効にする場合）: pip install PyYAML

環境変数 / .env
- 自動ロード
  - 起動時に .env（先にロード）→ .env.local（上書き）をプロジェクトルートから自動で読み込みます。
  - OS 環境変数が優先され、.env/.env.local はそれを上書きしません（.env.local は override=True だが protected により OS 環境は保護）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/推奨環境変数（デフォルト値あり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知用
- PAPER_FILL_MODE — paper_trading 用のモック挙動: instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1。デフォルト 0）

使い方
------
1) .env を対話的に作る（ウィザード）
   - python -m kabusys.config_setup
   - 実行後、.env に保存されます（保存前に確認があります）。

2) 起動前に設定を検証する
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict
   - validate_config は .env/.env.local と config/*.yaml の存在や値を確認します（PyYAML 未インストールなら YAML 検証はスキップされ警告が出ます）。

3) 実際の実行プロセス
   - Execution（発注エンジン）を起動:
     - python -m kabusys.run_execution
     - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使われます。
   - Monitoring（監視）を起動:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（デフォルト 60）。

4) 停止制御
   - stop_requested.flag（data/stop_requested.flag）を作成すると多くのループは検知して終了します。
   - kill.flag による起動時の安全チェックと実行中の kill_switch（全 active 注文のキャンセル）をサポート。

実装上の注意
- 本番用クライアント（KabuStationClient）は実装されているが、BrokerClientFactory は live 環境は NotImplementedError を投げるように設計される箇所があります。利用時はリリースノート／コード内メッセージに従ってください。
- 発注フローの耐障害性:
  - send_order 前に DB に OrderSent を書き込み（Step1）
  - broker から order_id が返れば先に broker_order_id を保存（Step3a）、その後 OrderAccepted に遷移（Step3b）
  - クラッシュ時に OrderSent のまま残るケースをリコンシリエーションで回復可能に設計されています
- ExecutionEngine のセッション時間は EngineConfig のデフォルトで調整可能（target_date は必須）

ディレクトリ構成（概要）
---------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数ロード/Settings
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor 起動スクリプト

- execution/                 — 発注周り
  - __init__.py
  - broker_api.py            — Protocol / データモデル / 例外 / ファクトリ
  - broker_factory.py        — Settings に基づくクライアント生成
  - kabu_client.py           — KabuStationClient（HTTP / WebSocket 実装）
  - mock_client.py           — MockBrokerClient（テスト用）
  - order_record.py          — OrderRecord と状態遷移ロジック（純粋モデル）
  - order_repository.py      — SQLite を用いた永続層
  - order_manager.py         — 外向け注文 API（create/send/sync/cancel）
  - execution_engine.py      — ExecutionEngine 本体（セッション管理）
  - reconciler.py            — 起動時リコンシリエーション
  - risk_manager.py          — Gate1/2/3 のリスクガード

- data/                      — データ処理関連
  - calendar_management.py   — マーケットカレンダー管理
  - news_collector.py        — RSS ニュース収集（正規化・SSRF対策）

- monitoring/
  - monitoring_db.py         — 監視用 SQLite テーブル初期化・ログ機能
  - system_monitor.py        — SystemMonitor（ポーリングでメトリクス収集）  ※参照のみ（実装ファイルあり）

- utils/
  - logging_setup.py         — ロギング初期化ユーティリティ
  - process_priority.py      — プロセス優先度設定ユーティリティ

補足（開発・運用）
-----------------
- SQL テーブルの初期化は各起動スクリプト内で実行される（例: init_orders_db, init_monitoring_db）。
- テストや開発では KABUSYS_ENV=paper_trading を設定すると本番 DB と分離して PAPER_TRADING_SQLITE_PATH に記録します。
- config/*.yaml（system_config.yaml 等）はプロジェクトの config ディレクトリで管理され、validate_config で存在・YAML パースチェックを行います（PyYAML が必要）。
- ロギングや PID ファイル、kill.flag の取り扱いは run_execution/run_monitoring 内で管理します。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）

お問い合わせ・貢献
-----------------
バグ報告や機能要望、プルリクエストはリポジトリの issue/pr フローに従ってください。README に含めるべき追加情報（CI、テスト手順、requirements.txt 参照等）があれば教えてください。