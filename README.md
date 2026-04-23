KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアコンポーネント群です。  
主にシグナルに基づく発注（ExecutionEngine）、発注の状態管理（OrderManager / OrderRepository / OrderRecord）、リスク管理（RiskManager）、リコンシリエーション（Reconciler）、監視ループ（SystemMonitor）やデータ処理（マーケットカレンダー、ニュース収集）などを含みます。

このリポジトリには実運用で想定される仕組みと開発／テスト用に使えるモック（MockBrokerClient）が実装されています。

主な機能
--------
- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup により対話的に .env を生成
- 設定検証 CLI
  - python -m kabusys.validate_config で .env と config/*.yaml の基本チェック
  - --strict オプションで警告も失敗扱いに
- 発注エンジン（ExecutionEngine）
  - シグナル読み取り → 2段階のリスクゲート → 発注管理（OrderManager）
  - WebSocket push ドレイン（kabu station push）対応
  - Paper trading（mock broker）対応
- ブローカー API 層
  - KabuStationClient（kabu station REST / WebSocket）、MockBrokerClient（テスト用）
  - Protocol / データモデル（OrderRequest/OrderResponse/OrderStatus/Position 等）
- 注文永続化
  - SQLite を用いた OrderRepository（orders テーブルの作成/CRUD）
- リスク管理
  - Gate 1: シグナルレベル（余力・重複・ポジション上限）
  - Gate 2: レート制限 / サーキットブレーカー
  - Gate 3: セッション中のドローダウン監視（キルスイッチ）
- リコンシリエーション（再起動時の復旧）
  - OrderSent 状態の注文をブローカーと突合して同期
  - ブローカーとローカル推定ポジションの差分検出
- 監視ループ（run_monitoring）
  - sqlite / duckdb を用いた監視データ蓄積、定期ポーリング
- データユーティリティ
  - カレンダー管理（JPX カレンダーの DuckDB 保存・営業日判定）
  - ニュース収集（RSS パース、前処理、raw_news への保存）

セットアップ手順
--------------
前提
- Python 3.10 以上（typing の | 記法、list[str] 等を使用）
- SQLite（Python 標準モジュール）
- duckdb ライブラリ

推奨依存パッケージ（例）
- duckdb
- httpx
- websocket-client
- PyYAML（config/*.yaml の内容検証に必要、任意）
- defusedxml（ニュース収集）
これらは requirements.txt がある場合は pip install -r requirements.txt を推奨します。なければ個別にインストールしてください。
例:
```bash
pip install duckdb httpx websocket-client pyyaml defusedxml
```

初期設定
1. プロジェクトルートに .env を作成します。対話的に作成するには:
   ```bash
   python -m kabusys.config_setup
   ```
   --env-file オプションで別パスを指定できます。

2. .env の必須項目（最低限）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   その他、KABUSYS_ENV（development / paper_trading / live）、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等を設定できます。

3. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```
   PyYAML が未インストールだと config/*.yaml のパース検証はスキップされます。

データベース初期化
- 実行・監視で使用する SQLite / DuckDB の親ディレクトリが存在しない場合は自動作成されないことがあります。README やウィザードで設定したパス（デフォルトは data/）に注意してください。OrderRepository や監視用テーブルは起動時に初期化処理を呼ぶことで作成されます（init_orders_db / init_monitoring_db 等）。

使い方
------
主要スクリプト（モジュールとして実行）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file <パス>

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit 1 扱い

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用して発注をシミュレートします
  - stop_flag（data/stop_requested.flag）を作成すると安全に停止処理が行われます
  - 起動時に PID ファイル（デフォルト data/execution.pid）を書きます

- 監視ループ
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60）

環境変数・重要設定（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabu station API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（live 実行時に推奨）
- KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 起動時の kill flag 設定

開発・テストのヒント
- MockBrokerClient は fill_mode（instant / partial / never / reject）をサポート。paper_trading のテストで発注成功/部分約定/保留/拒否を切り替えられます。
- ExecutionEngine は run_session() を呼ぶことでセッション全体（シグナル処理→push ドレイン→終了）を再現します。ユニットテストでは _process_signals() や _drain_push_queue() を直接呼ぶ設計になっています。
- Reconciler は起動時に OrderSent 状態の注文をブローカーと突合して復旧するため、クラッシュ後の状態回復が可能です。

ディレクトリ構成
----------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動ロード・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- execution/
  - __init__.py
  - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
  - broker_factory.py      — Settings に応じたブローカークライアント生成
  - kabu_client.py         — KabuStation REST/WebSocket クライアント
  - mock_client.py         — テスト用 MockBrokerClient
  - order_record.py        — OrderRecord（状態遷移ロジック）
  - order_repository.py    — SQLite 永続化層（orders テーブルの CRUD）
  - order_manager.py       — 発注フロー（create/send/sync/cancel）
  - execution_engine.py    — 実行エンジン（セッション制御）
  - reconciler.py          — 再起動時のリコンシリエーション
  - risk_manager.py        — 3段階リスクガード
- monitoring/
  - monitoring_db.py       — 監視DB 初期化 / ログ関係（参照コード内で使用）
  - system_monitor.py      — 監視ロジック（ポーリング等）
- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py      — RSS ニュース収集・前処理
- utils/
  - logging_setup.py       — ロギング設定ユーティリティ
  - process_priority.py    — プロセス優先度設定ユーティリティ
- その他: config/*.yaml（設定ファイル群; validate_config が存在チェック / YAML パースを行う）

注意事項 / 運用メモ
-----------------
- .env は絶対に Git 等にコミットしないでください（README の注記・config_setup でも警告あり）。
- KABUSYS_ENV=live にした場合は本番環境として慎重に設定・確認してください。現時点で Live ブローカークライアントの完全な実装は未実装（BrokerClientFactory は NotImplementedError を投げる場合があります）。
- validate_config は必須環境変数の未設定やプレースホルダ値、config/*.yaml のパースエラー、不適切な KABUSYS_ENV 値等を事前に検出できます。CI で --strict モードを使うことを推奨します。
- stop フラグ / kill flag / PID 管理により安全な停止・再起動が可能です。運用時は stop_requested.flag や kill.flag の取り扱いに注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ / 開発
-----------------
- 各モジュールは比較的独立にテストできる設計です（MockBrokerClient、ExecutionEngine の分離、OrderRecord の純粋ロジックなど）。ユニットテストや結合テストを追加して運用品質を高めてください。

以上。必要であれば README にサンプル .env テンプレートや CI 用の validate_config を組み込む手順、requirements.txt の例などを追記します。どの情報を追加しますか？