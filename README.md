KabuSys — 日本株自動売買システム (README)
=====================================

概要
----
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。  
主に下記を提供します。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカークライアント抽象化（実際の kabuステーション or モック）
- 注文状態管理・永続化（SQLite）
- 発注リスクガード（3段階：Gate1/Gate2/Gate3）
- 起動前設定検証と対話式 .env 作成ウィザード
- 監視プロセス（SystemMonitor）用のポーリング起動スクリプト
- データ処理用のユーティリティ（DuckDB を想定）

特徴
----
- 明確に分離されたレイヤ（API クライアント / Execution / Persistence / Risk）
- ブローカークライアントはモック実装を用意しており、kabuステーション不要でテスト可能
- 起動時の自動リコンシリエーション機能（OrderSent の照合）
- kill flag / stop flag による安全な停止機構
- .env ウィザード（config_setup）と静的検証ツール（validate_config）

前提
----
- Python 3.9 以上（list[str] 等の構文を使用）
- SQLite（標準ライブラリ）
- 推奨／必要なサードパーティライブラリ（用途別）:
  - duckdb — 分析用 DB 接続
  - httpx — kabu station REST 呼び出し（同期）
  - websocket-client — kabu station WebSocket push
  - PyYAML — config/*.yaml のパース（任意だが推奨）
  - defusedxml — RSS パースの安全化
  - その他: typing 等は標準

インストール例
--------------
仮想環境を作成して依存をインストールする例:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（例）
   - pip install duckdb httpx websocket-client PyYAML defusedxml

セットアップ手順
----------------
1. プロジェクトルートに移動（pyproject.toml または .git がある場所がプロジェクトルートになります）。

2. .env を作成する（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは既存の .env を読み込み、Enter で既存値を維持できます。
   - ウィザード後は python -m kabusys.validate_config で検証することを推奨。

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL として exit(1) で終了します。
   - PyYAML がインストールされていれば config/*.yaml のパース検証も行います。

使い方（起動/停止）
------------------

環境変数の主な項目
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意／重要:
  - KABUSYS_ENV : development | paper_trading | live
  - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH （デフォルト: data/monitoring.db）
  - LOG_LEVEL （DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番の通知用）
  - KILL_FLAG_CLEAR_ON_START（起動時の kill.flag 自動クリア: "0" または "1"）

エントリポイント
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録されます。

- 監視プロセス（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に production sqlite_path を使用（KABUSYS_ENV に依らず本番 DB を参照）。

プロセス停止 / 制御
- stop 依頼:
  - data/stop_requested.flag を作成するとループ中に検知して安全停止します。
- kill スイッチ:
  - data/kill.flag を作成すると ExecutionEngine は kill_switch() を呼び、全 active 注文をキャンセルします。
  - KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に既存の kill.flag を自動クリアします（開発用）。

注意点
- 本番モード（KABUSYS_ENV=live）での使用は慎重に。validate_config は live を検出すると警告を出します。
- Live broker client（実際の KabuStationClient）を production で使用するには適切な設定と kabuステーションの稼働が必要です。現在のファクトリは development/paper_trading 向けにモックを返しますが、将来的に Live 実装で切り替え可能です。
- .env は絶対にリポジトリにコミットしないでください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なモジュールと簡単な説明です。

- __init__.py
  - パッケージ定義・バージョン情報

- config.py
  - 環境変数の読み込み（.env 自動ロード）と Settings クラス
  - 必須環境変数チェック用の _require 等

- config_setup.py
  - .env の対話式ウィザード生成スクリプト

- validate_config.py
  - 起動前に .env と config/*.yaml を検証する CLI

- run_execution.py
  - ExecutionEngine を組み立てて実行する起動スクリプト
  - ブローカーファクトリ / OrderRepository / RiskManager / Reconciler を初期化

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、Factory
  - kabu_client.py — kabuステーション REST/WebSocket クライアント
  - mock_client.py — テスト用モックブローカー
  - broker_factory.py — Settings に基づくクライアント生成
  - execution_engine.py — 発注のメインロジック（シグナル処理・push ドレイン等）
  - order_record.py — 注文状態遷移の純粋モデル
  - order_repository.py — SQLite 永続化層（orders テーブル操作）
  - order_manager.py — 外向け発注 API（作成・送信・同期・キャンセル）
  - reconciler.py — 起動時のリコンシリエーション（OrderSent の復旧）
  - risk_manager.py — Gate1/2/3 のリスクガード

- monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化 / ログ関係
  - system_monitor.py — システムリソース監視（CPU/MEM/DISK など）
  - run_monitoring.py — 監視ポーリングループ起動スクリプト（前述）

- data/
  - （実行時に生成されるデータファイル）
  - default: data/kabusys.duckdb, data/monitoring.db, data/execution.pid, data/kill.flag, data/stop_requested.flag

- data/（モジュール）
  - calendar_management.py — マーケットカレンダー関連（DuckDB を想定）
  - news_collector.py — RSS ニュース収集モジュール（defusedxml を使用）

ログと監視
----------
- ログ出力は utils/logging_setup を経由（setup_logging）して行われます（アプリ名を指定して起動）。
- LOG_LEVEL で出力レベルを制御（デフォルト: INFO）。
- 監視 DB（SQLite）にトレードイベントやレイテンシーを記録できます（MonitoringDB の実装に依存）。

追加情報 / 開発者向け
--------------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます（config.py）。
- ExecutionEngine は内部で PID ファイルを書き、停止時に削除します（設定は Settings.pid_file_path）。
- Reconciler は起動時に OrderSent 状態の注文をブローカーと照合して安全に復旧します。

ライセンス / 貢献
----------------
- この README にライセンス情報は含まれていません。実プロジェクトでは LICENSE ファイルを追加してください。  
- バグ修正や機能追加は PR を歓迎します。テストと簡潔な変更説明を添えてください。

お問い合わせ
-----------
実装上の質問や使い方に関する質問があれば、プロジェクトの issue 管理やメンテナンス担当者にお問い合わせください。

以上。