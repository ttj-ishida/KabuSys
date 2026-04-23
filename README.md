KabuSys
=======

概要
----
KabuSys は日本株の自動売買システムのための軽量フレームワークです。
主にローカル / 検証（ペーパートレード）用途を想定しており、kabuステーション API（またはモック実装）を通じて発注、発注状態の管理、リコンシリエーション（再整合）、監視、マーケットカレンダー管理、ニュース収集などの基本機能を提供します。

主な設計ポイント
- 明確に分離された層（API クライアント、注文状態ロジック、永続化、実行エンジン、リスク管理、監視）
- ペーパートレード用の MockBrokerClient を用意（development / paper_trading で使用）
- 再起動時の自動復旧（Reconciler）を備え、OrderSent の不確実状態へ対応
- 設定は .env / 環境変数と config/*.yaml で管理。設定ウィザード・検証ツール付き

機能一覧
--------
- 環境設定ウィザード（.env を対話式作成 / 更新）
  - python -m kabusys.config_setup
- 起動前設定検証ツール（環境変数・config/*.yaml の検証）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine（シグナル取り込み → 発注 → WebSocket ドレイン）
  - python -m kabusys.run_execution
- SystemMonitor（監視ループ）
  - python -m kabusys.run_monitoring
- ブローカー API 層
  - KabuStationClient（kabuステーション用クライアント、HTTP/WebSocket）
  - MockBrokerClient（テスト・ペーパートレード用）
- 注文状態管理（OrderRecord の状態遷移保護）
- 注文永続化（SQLite を使った OrderRepository、スキーマの初期化関数あり）
- リスク管理（Gate1/2/3: シグナル検査・レート/CB・ドローダウン）
- リコンシリエーション（起動時に不確実な注文を突合）
- データ系ユーティリティ（マーケットカレンダー、ニュース収集など）

セットアップ手順
--------------
※以下は推奨手順のサンプルです。実際の依存はプロジェクトの requirements.txt や pyproject.toml を参照してください。

1. Python 環境の用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb pyyaml httpx websocket-client defusedxml
   - 必要に応じて他のパッケージも追加してください（プロジェクトの依存情報参照）。

3. プロジェクトルートに移動（README と同じレベル）
   - .env / data ディレクトリなどは自動的に作成されますが、書き込み権限を確認してください。

4. 初期設定（推奨）
   - python -m kabusys.config_setup
     - 対話式に .env を作成します（.env を絶対に Git にコミットしないでください）

5. 設定検証（必須）
   - python -m kabusys.validate_config
   - 本番運用前は --strict オプションで警告も失敗扱いにすることを推奨します:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - Execution/Monitoring を動かす前に必要なテーブル（orders など）を init_* 関数で作成してください。
   - 例: run_execution や run_monitoring が起動時に init_monitoring_db / init_orders_db を呼ぶ箇所があります。

使い方（主要コマンド）
---------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します。完了後に validate_config を実行してください。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit code 1（FAIL）になります。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更できます（デフォルト 60）。

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading 用 SQLite に記録します。

主な環境変数（抜粋）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN  — J-Quants API 用トークン
  - KABU_API_PASSWORD      — kabuステーション API パスワード

- 推奨 / 省略可（デフォルトあり）
  - KABUSYS_ENV            — 実行環境: development / paper_trading / live（default: development）
  - DUCKDB_PATH            — duckdb ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH            — 監視 DB（default: data/monitoring.db）
  - LOG_LEVEL              — ログレベル（DEBUG/INFO/...、default: INFO）
  - KABU_API_BASE_URL      — kabu station base URL（default: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番通知用（live 時に推奨）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1, default: 0）
  - PAPER_FILL_MODE        — paper_trading 時の fill モード（instant/partial/never/reject; default: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）

注意点
-------
- KABUSYS_ENV=live の場合は細心の注意が必要です（validate_config で警告が出ます）。現状 Live broker client は未実装の箇所があります（BrokerClientFactory の NotImplementedError）。
- .env は決してリポジトリにコミットしないでください（config_setup はその旨を明示）。シークレットはマスク表示されますが実ファイルはローカルで管理してください。
- PyYAML がインストールされていない場合、config/*.yaml のパースチェックはスキップされます（validate_config が警告を出す）。
- kill.flag / stop_requested.flag の存在により起動やループ停止の振る舞いが制御されます。KILL_FLAG_CLEAR_ON_START は本番で 1 にしないことを推奨します。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトのソースは src/kabusys 以下に配置されています。代表的なファイル・モジュールを示します。

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / .env ロードと Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - execution/                 — 実行・発注周り
    - __init__.py
    - broker_api.py            — Protocol / データモデル / ファクトリ
    - kabu_client.py           — kabu station 実装（HTTP/WebSocket）
    - mock_client.py           — MockBrokerClient（テスト用）
    - broker_factory.py        — 設定に応じたクライアント作成
    - order_record.py          — OrderState / OrderRecord（状態遷移ロジック）
    - order_repository.py      — SQLite 永続化層（init_orders_db 等）
    - order_manager.py         — 外向き注文 API（create/send/sync/cancel）
    - reconciler.py            — 起動時リコンシリエーション
    - execution_engine.py      — ExecutionEngine（シグナル処理 + push ドレイン）
    - risk_manager.py          — Gate1/2/3 リスク管理
  - data/                      — データ処理モジュール
    - calendar_management.py   — マーケットカレンダー管理
    - news_collector.py        — RSS ベースニュース収集
    - (その他 jquants_client 等)
  - monitoring/                — 監視周り（DB 初期化・SystemMonitor 等）
  - utils/                     — ロギング設定・プロセス優先度設定などユーティリティ

開発者向けメモ
--------------
- 設定自動ロードは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から行います。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト用）。
- ExecutionEngine は DuckDB から signals / portfolio_targets を読み発注します。テスト時は MockBrokerClient を使い、paper_trading 用 DB を分離してください。
- Reconciler は OrderSent の不確実状態を broker と照合して自動回復します。起動時に実行することでクラッシュ後の整合性を保ちます。
- WebSocket の受信（kabu push）は blocking な stream_push を別スレッドで実行し、_push_queue を介してメインスレッドに通知します。

よくあるトラブルシュート
-----------------------
- validate_config がエラーを返す
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定か確認してください。
  - KABUSYS_ENV の値は development / paper_trading / live のいずれかでなければなりません。
  - PyYAML を入れておくと config/*.yaml のパースチェックもできます。

- run_execution が起動しない / 即終了する
  - data/kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 ならクリアして起動）。
  - PID ファイルの書き込み先に権限があるか確認してください。

- WebSocket 接続エラー
  - KabuStationClient は base_url を http://... の形式で受け取り、WebSocket 用に ws:// に変換します。kabuステーションが起動しているか、ネットワークやトークンを確認してください。

最後に
-----
本 README はコードベースの主要な点をまとめた簡易説明です。詳細な仕様や運用手順はコード内ドキュメント（docstrings）およびプロジェクトの設計文書（存在する場合）を参照してください。ご不明点があれば該当モジュールの docstring を確認するか、リポジトリ管理者に問い合わせてください。