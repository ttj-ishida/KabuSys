KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ／実行スクリプト群です。
主に以下を提供します。

- 環境変数・設定管理（.env 自動ロード / Settings クラス）
- 環境設定ウィザード（.env 生成／更新）
- 設定検証ツール（.env / config/*.yaml の整合性チェック）
- 発注エンジン（ExecutionEngine）と注文状態管理（OrderRecord / OrderManager）
- ブローカークライアント（実運用向け KabuStationClient とテスト用 MockBrokerClient）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor 起動スクリプト）
- データユーティリティ（マーケットカレンダー管理、ニュース収集など）

主な特徴
--------
- 環境（development / paper_trading / live）に応じた挙動切替
- 発注フローのクラッシュ耐性（2相永続化、Reconciliation）
- 3段階のリスクガード（Gate1: シグナルレベル、Gate2: レート制限/CB、Gate3: ドローダウン）
- MockBrokerClient により kabuステーション を必要としないローカルテストが可能
- .env ウィザード & 検証ツールでセットアップを支援

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作る（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール（代表的な依存パッケージ）
   - pip install duckdb httpx websocket-client PyYAML defusedxml

   ※ 実装に応じて追加で必要なパッケージがある場合があります。
   - PyYAML がない場合、config/*.yaml の内容検証はスキップされます（validate_config が警告を出す）。

3. データディレクトリの準備（任意）
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要に応じて権限を調整してください。

4. 環境変数設定（.env 作成）
   - 下記「環境変数一覧」を参考に .env を作成します。
   - 対話式で作るには config_setup を利用してください（推奨）。

使い方
------

環境設定ウィザード（対話式 .env 作成）
- python -m kabusys.config_setup
  - 対話式に主要設定を入力して .env を生成します。
  - 生成後に validate_config を実行して検証することを推奨します。

設定検証
- python -m kabusys.validate_config
  - .env と config/*.yaml の存在や基本的整合性をチェックします。
- python -m kabusys.validate_config --strict
  - 警告も FAIL として扱い exit code 1 を返します（CI 用）。

実行スクリプト
- 実行エンジン（発注処理）起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV によって mock（paper_trading / development）かライブ（未実装）を選択します。
    - 停止フラグ: data/stop_requested.flag が作られると停止します。
    - PID ファイル: data/execution.pid（設定により変更可）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - 簡易的に SystemMonitor を定期実行します。
    - 環境に関わらず本番用の sqlite_path を使用します（監視 DB は一意に管理するため）。

主要ファイル / 実行時の挙動メモ
- .env の自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env を自動読み込みします。
  - 読込順: OS 環境 > .env.local > .env（.env.local は .env を上書き可能）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 停止・PID 管理
  - 停止フラグ: data/stop_requested.flag（存在を検出して安全停止）
  - kill.flag: settings.kill_flag_path（デフォルト data/kill.flag）で強制停止（起動時の挙動は KILL_FLAG_CLEAR_ON_START に依存）
  - PID ファイル: settings.pid_file_path（デフォルト data/execution.pid）

環境変数一覧（主要）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（任意）
- LINE_USER_ID — LINE 通知先（任意）
- PAPER_FILL_MODE — paper_trading の Mock の fill 動作（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL, など

注意:
- validate_config は必須環境変数が未設定の場合 ERROR を返します。プレースホルダ値（your_value や *_here）が残っている場合は警告を出します。
- KABUSYS_ENV=live の場合、LINE のトークンやユーザー ID 未設定などの警告が出ます（本番時の確認ポイント）。

ディレクトリ構成（src/kabusys の主要ファイルと説明）
---------------------------------------------------
- __init__.py
  - パッケージ定義（__version__ 他）

- config.py
  - Settings クラスによる環境変数アクセス、.env 自動ロードロジック、必須チェック
  - settings オブジェクトを通して利用することを想定

- config_setup.py
  - 対話式ウィザードで .env を作成／更新する CLI

- validate_config.py
  - .env と config/*.yaml の事前チェック CLI（--strict オプションあり）

- run_execution.py
  - ExecutionEngine を起動するスクリプト（発注処理）
  - 停止フラグ・PID 管理・DB 接続を行う

- run_monitoring.py
  - SystemMonitor を定期実行する監視スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）

- execution/
  - broker_api.py — BrokerAPIProtocol、OrderRequest/Response/Status、例外、create_broker_api()
  - kabu_client.py — kabuステーション REST クライアント実装（HTTP / WebSocket）
  - mock_client.py — テスト用 MockBrokerClient（fill_mode 等指定可能）
  - broker_factory.py — Settings に基づくクライアント作成ファクトリ
  - order_record.py — 注文の状態遷移ロジック（OrderRecord, OrderState）
  - order_repository.py — SQLite による永続化レイヤー、テーブル初期化関数
  - order_manager.py — OrderRecord と Repository / Broker をつないだ外向き API（create/send/sync/cancel）
  - execution_engine.py — 実際のセッション制御（シグナル処理 / push drain / kill switch）
  - reconciler.py — 起動時の自動復旧（OrderSent の突合、ポジション差分検知）
  - risk_manager.py — Gate1/2/3 の実装（レート制限・CB・ドローダウン等）

- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB を前提とした is_trading_day / next_trading_day 等）
  - news_collector.py — RSS ベースのニュース収集と前処理（SSRF対策、XML安全パース）

- monitoring/
  - （監視DB周り・SystemMonitor 実装ファイルが配置される想定）

その他の運用メモ
----------------
- DB ファイル
  - DuckDB: デフォルト data/kabusys.duckdb
  - SQLite(監視): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

- ローカル開発では KABUSYS_ENV=development または paper_trading を推奨
  - development / paper_trading は MockBrokerClient を用いるため kabuステーション が不要
  - live 用クライアント（KabuStationClient）を使うには実運用の実装・検証が必要（Factory にて未実装箇所が明示されている場合あり）

- リコンシリエーション
  - 再起動時には Reconciler が OrderSent の不確定状態を突合し、ポジション差異をログに出す設計です。

- セキュリティ
  - .env は絶対にリポジトリにコミットしないでください（config_setup にも同旨の注意文が含まれます）。
  - RSS パーサーは defusedxml を使用して XML 攻撃を緩和しています。
  - news_collector は SSRF 対策（スキーム検査・プライベートホストブロック）を含みます。

トラブルシューティング
----------------------
- validate_config で YAML のパースエラーが出る:
  - PyYAML がインストールされていない場合は YAML 検証がスキップされ、警告が出ます。PyYAML を入れて再チェックしてください。
- ExecutionEngine が起動しない（kill.flag が原因）:
  - settings.kill_flag_clear_on_start の設定によっては起動時に既存の kill.flag を消去して起動する動作があります。本番では 0（クリアしない）を推奨します。
- ブローカー API 周りの接続エラー:
  - KABU_API_BASE_URL / KABU_API_PASSWORD の設定と kabuステーション アプリの稼働を確認してください。開発時は mock モードを使うのが簡便です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報や配布パッケージ化はプロジェクトルートの pyproject.toml 等を参照してください（存在する場合）。

以上が本リポジトリの README に相当する概要です。README に追記したい箇所（例: requirements.txt の正確な内容、監視／メトリクス設計、デプロイ手順、CI 設定など）があれば追記用の情報を教えてください。