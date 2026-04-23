README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは次を含みます:

- 環境設定のウィザード（.env 作成/更新）
- 起動前チェック（環境変数・config/*.yaml の検証）
- ExecutionEngine：シグナルに基づく発注エンジン（paper_trading / development 用モックあり）
- Monitoring：システム監視ループ
- Broker クライアント抽象化（実運用では kabuステーション API を利用、開発/テストは Mock）

主な設計方針は安全第一（3段階のリスクガード、リコンシリエーション、kill switch 等）です。

主な機能
--------
- .env 対話ウィザード（kabusys.config_setup）
  - 初期 .env 作成 / 既存 .env の更新を対話式に実施
- 起動前設定検証（kabusys.validate_config）
  - 必須環境変数の未設定検出、プレースホルダ検出、config/*.yaml の存在と YAML パース確認（PyYAML がある場合）
  - --strict オプションで警告も失敗扱いにできる
- ExecutionEngine（kabusys.run_execution）
  - Signal の読み込み → Gate1/2 の検査 → 発注 → push のドレイン処理
  - paper_trading では MockBrokerClient を使用し、本番 DB と分離された paper_trading 用 SQLite に記録
  - kill.flag を用いた安全停止、PID ファイル管理
- Monitoring ループ（kabusys.run_monitoring）
  - 定期ポーリングでシステム指標を記録・監視（MONITOR_POLL_INTERVAL で間隔変更可）
- Broker 抽象化（kabusys.execution.broker_api）
  - MockBrokerClient と KabuStationClient（kabuステーション REST）を同じインターフェースで利用可能
- 注文永続化（SQLite）と状態管理（OrderRecord の状態遷移検証）
- リコンシリエーション（再起動時の OrderSent 照合とポジション差分確認）
- データ処理ユーティリティ（マーケットカレンダー、ニュース収集など）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone で取得してください。

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 主要依存（例）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML （任意：config/*.yaml の内容検証に使用）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   （requirements.txt があれば pip install -r requirements.txt を推奨）

4. データディレクトリ作成
   - デフォルトで data/ に DB やフラグファイルを置きます。必要に応じて作成してください。
     - mkdir -p data

5. .env を作成
   - 対話ウィザードで簡単に作成できます（次のコマンド参照）。

使い方
------
1. 環境設定ウィザード（.env 作成 / 更新）
   - python -m kabusys.config_setup
   - 対話式に値を入力するとプロジェクトルートの .env に保存されます（--env-file で別パス指定可）。
   - 実行後は python -m kabusys.validate_config で検証することを推奨。

2. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict
   - exit code:
     - 0: 問題なし / 警告のみ（strict なし）
     - 1: エラーあり、あるいは strict かつ警告あり

3. 実行エンジン（発注）
   - python -m kabusys.run_execution
   - 実行前に .env の KABUSYS_ENV を設定してください（development / paper_trading / live）。
   - paper_trading では MockBrokerClient を用います（本番は未実装で NotImplementedError を出します）。
   - 停止: data/stop_requested.flag を作成するとループが終了します。
   - PID ファイル: data/execution.pid（設定により変更可）。既存の kill.flag がある場合、KILL_FLAG_CLEAR_ON_START に基づき起動可否が決まります。

4. 監視ループ（Monitoring）
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更する場合:
     - export MONITOR_POLL_INTERVAL=30  # 秒
   - 停止フラグ: data/stop_requested.flag
   - 監視は常に本番用 sqlite_path を使用（監視データは本番 DB と共有する仕様）

主要環境変数（代表）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 主要オプション
  - KABUSYS_ENV               : 実行環境（development / paper_trading / live）, default=development
  - DUCKDB_PATH               : DuckDB ファイルパス, default=data/kabusys.duckdb
  - SQLITE_PATH               : 監視用 SQLite, default=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH : paper_trading 用 SQLite（上書き）
  - LOG_LEVEL                 : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）, default=INFO
  - KILL_FLAG_CLEAR_ON_START  : 起動時に kill.flag を自動クリアする (0/1), default=0
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 本番アラート用（任意）
  - PAPER_FILL_MODE           : paper_trading 用の約定モード（instant/partial/never/reject）

- 自動 .env 読み込み
  - 起動時に自動でプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数を優先）。
  - 無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

環境変数のサンプル (.env)
-------------------------
以下は .env の例（機密情報は実際の値で置換してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

注意点 / 運用メモ
-----------------
- 本番モード（KABUSYS_ENV=live）は慎重に。validate_config は live を検出すると警告を出します。
- kill.flag（KILL_FLAG_PATH、デフォルト data/kill.flag）は手動での緊急停止スイッチです。起動時に存在する場合、KILL_FLAG_CLEAR_ON_START が 1 でなければ起動を拒否します。
- stop_requested.flag（data/stop_requested.flag）はプロセス間の優雅な停止トリガーとして run_execution / run_monitoring で用いられます。
- config/*.yaml（system_config.yaml 等）は検証対象です。PyYAML があれば内容のパース検証を行います。validate_config の _CONFIG_FILES に対象ファイル名が定義されています:
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
- ExecutionEngine のデフォルト動作は「シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）」です（コード内で変更可能）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースルート内の主要モジュール構成（src/kabusys 以下）です。実際のプロジェクトでは追加ファイルやサブモジュールが存在する場合があります。

- src/kabusys/
  - __init__.py                 — パッケージ初期化（バージョン等）
  - config.py                   — 環境変数 / .env のロードと Settings クラス
  - config_setup.py             — .env 対話ウィザード CLI
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py           — Monitoring ポーリングループ起動スクリプト
  - execution/
    - broker_api.py             — Broker API のデータモデル / Protocol / ファクトリ
    - broker_factory.py         — Settings に基づく Broker クライアント生成
    - kabu_client.py            — kabuステーション REST クライアント（httpx）
    - mock_client.py            — テスト用 MockBrokerClient
    - order_record.py           — 注文状態モデルと遷移ロジック（純粋ビジネスロジック）
    - order_repository.py       — SQLite による永続化層（orders テーブル）
    - order_manager.py          — 外向き API（Order 作成 / 送信 / 同期 / キャンセル）
    - execution_engine.py       — セッション制御・シグナル処理・push ドレイン
    - reconciler.py             — 再起動時のリコンシリエーション
    - risk_manager.py           — Gate1/2/3 のリスクチェック
  - data/
    - calendar_management.py    — マーケットカレンダー（J-Quants 連携）ユーティリティ
    - news_collector.py         — RSS ニュース収集・正規化ロジック
    - (jquants_client 等 他ユーティリティ)
  - monitoring/
    - monitoring_db.py          — 監視 DB 初期化 / ログ書き込み
    - system_monitor.py         — システム指標収集ロジック
  - utils/
    - logging_setup.py          — ロガー設定ユーティリティ
    - process_priority.py       — プロセス優先度設定ユーティリティ

ライセンス / 貢献
-----------------
- 本 README はコードから推測して記述しています。実運用や配布時はライセンス表記や CONTRIBUTING ガイドを追加してください。

補足（開発者向け）
-----------------
- validate_config は PyYAML がない場合に YAML 内容検証をスキップします。CI で厳密に検査したい場合は PyYAML をインストールしてください。
- MockBrokerClient は paper_trading の挙動確認・単体テストに便利です。fill_mode により即時約定 / 部分約定 / 永遠に未約定 / 拒否 をシミュレートできます。
- ExecutionEngine の主要ループとリソース（PID/flag/DB）はテスト用に差し替え可能な設計です（duckdb_conn / sqlite_conn / pid_file / monitoring_db を注入可能）。

以上。設定ウィザードと validate_config を使ってまず .env を整え、development / paper_trading で動作確認することを推奨します。