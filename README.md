KabuSys
======

概要
----
KabuSys は日本株の自動売買を想定したシンプルなトレading エンジンのコードベースです。
主に以下を提供します。

- シグナルを読み込んで発注する ExecutionEngine（本番 / ペーパートレード対応）
- 発注状態の永続化と再起動時リコンシリエーション
- リスクガード（3段階: Gate1/2/3）
- 監視（SystemMonitor）用の簡易ポーリングループ
- 環境設定ウィザード (.env 作成) と起動前設定検証ツール
- DuckDB / SQLite を使ったデータ保存・マーケットカレンダー管理・ニュース収集基盤（骨組み）

設計方針の要点:
- ブローカー API 層は Protocol / ファクトリ化しており、MockBrokerClient により本番環境がなくてもローカルで動作確認ができます（paper_trading / development）。
- 注文ロジック（OrderRecord）は DB と分離して純粋なビジネスロジックを保つ設計です。
- 自動起動前に .env / config/*.yaml を検証する CLI を提供します。

主な機能
--------
- 環境設定ウィザード: python -m kabusys.config_setup で対話的に .env を生成/更新
- 設定検証: python -m kabusys.validate_config で .env と config/*.yaml の不備を検出
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading なら MockBrokerClient を使用して data/paper_trading.db に記録
- 監視プロセス起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）
- 注文管理: OrderManager / OrderRepository（SQLite） / OrderRecord（状態遷移検証）
- ブローカークライアント層:
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu-station REST API 実装、未テストの本番向け実装）
- リコンシリエーション（起動時に OrderSent の未解決注文を照合して同期）
- マーケットカレンダー管理（DuckDB 経由、J-Quants 連携想定）
- ニュース収集モジュール（RSS 収集、正規化、保存）

セットアップ手順
--------------
前提: Python 3.8+（typing、dataclasses 等を使用）。環境に合わせて仮想環境を作成してください。

1. リポジトリをクローンしてソースに移動
   - (例) git clone ... && cd <repo>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）
   - pip install duckdb httpx websocket-client defusedxml
   - 追加で YAML の検証をしたい場合: pip install pyyaml

   参考（requirements ファイルがあればそちらを使用してください）

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記「主要な環境変数」を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - Execution / Monitoring は起動時に必要なテーブルを作成する処理（init_monitoring_db、init_orders_db）を呼びますが、手動で準備する場合は sqlite3 / duckdb を使用して所定のファイルパスに空ディレクトリやファイルを書き込みできることを確認してください。

主要な環境変数（サマリ）
-----------------------
必須 (最低限設定が必要)
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")。デフォルト "development"
  - paper_trading: MockBrokerClient を使用（本番 DB と分離）
  - live: 本番（注意喚起メッセージあり）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- KABU_API_BASE_URL — kabu-station のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（本番では設定推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）

.env 自動読み込み
- .env（プロジェクトルート） と .env.local を自動で読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト等で使用）。

使い方（エントリポイント）
-------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env ファイルを対話生成／更新します

- 設定検証
  - python -m kabusys.validate_config
  - 警告を失敗扱いにする:
    - python -m kabusys.validate_config --strict

- 実行エンジン（発注）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて paper_trading（Mock）/ live（未実装） の振る舞いに分かれます。
  - stop 制御:
    - プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。
    - PID は data/execution.pid（デフォルト）に書かれます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能

ディレクトリ構成（主要ファイル）
------------------------------
以下はプロジェクト内の主なファイル/モジュール構成（src/kabusys 配下）です。実装の要点も併記します。

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — .env 自動ロード、Settings クラス（環境変数ラッパー）
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 起動前の設定検証 CLI（--strict オプション）
  - run_execution.py           — ExecutionEngine を起動するスクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト

  - data/
    - calendar_management.py   — マーケットカレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集（defusedxml 等使用）
    - jquants_client.py        — J-Quants API クライアント（参照される想定）

  - execution/
    - broker_api.py            — BrokerAPI Protocol / データモデル / ファクトリ
    - broker_factory.py        — Settings に応じたブローカークライアント生成
    - kabu_client.py           — kabu-station REST 実装（HTTP + WebSocket）
    - mock_client.py           — MockBrokerClient（テスト用）
    - order_record.py          — 注文状態遷移モデル（OrderRecord / OrderState）
    - order_repository.py      — SQLite による永続化（orders テーブル）
    - order_manager.py         — 発注 API（create/send/sync/cancel）
    - execution_engine.py      — メインの発注エンジン（シグナル処理 / push ドレイン）
    - reconciler.py            — 起動時リコンシリエーション、ポジション照合
    - risk_manager.py          — Gate1/2/3 のリスク統制

  - monitoring/
    - monitoring_db.py         — 監視 DB の初期化・ログ記録（SQLite）
    - system_monitor.py        — システムメトリクス監視（ログ収集等）

  - utils/
    - logging_setup.py         — ロギング初期化ヘルパー
    - process_priority.py      — プロセス優先度設定ユーティリティ

補足・運用上の注意
-----------------
- paper_trading（KABUSYS_ENV=paper_trading）は MockBrokerClient を使用し、本番の SQLite DB と分離して paper_trading 用 DB に記録します。
- monitoring プロセスは KABUSYS_ENV に関わらず監視用 sqlite_path（本番用）を使用する点に注意してください（run_monitoring の実装）。
- 起動前に validate_config を実行し、警告やエラーを解消してください。--strict を CI に組み込むとより安全です。
- .env は秘匿情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py でも注意喚起があります）。
- KabuStationClient は実装されていますが、ローカル環境で kabu-station® が稼働している前提です。テスト・開発は MockBrokerClient 推奨です。
- config/*.yaml（system_config.yaml 等）のテンプレートや生成スクリプト（scripts/generate_config.py）を用意している場合はそれを使用してください。PyYAML 未インストール時は validate_config は YAML 内容検証をスキップします。

開発・拡張のヒント
-----------------
- BrokerAPIProtocol を実装すれば別ブローカーの接続ロジックを追加できます。
- ExecutionEngine の run_session はテスト時に _process_signals / _drain_push_queue を直接呼ぶことで時間依存を排除できます。
- OrderRecord の transition_to による遷移検証は状態機械の中心です。DB と組み合わせることでクラッシュからの復旧性を高める設計になっています。

問い合わせ・貢献
----------------
バグ報告・機能提案は issue を立ててください。PR の際はテストと簡単な説明を添えてください。

以上。必要があれば README の英語版やさらに詳しい開発者向けドキュメント（アーキテクチャ図、シーケンス図、API 契約書など）を作成します。どの項目を優先して追加しましょうか？