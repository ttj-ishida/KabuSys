KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。  
主に以下の目的を持ちます：

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアント抽象化（kabu station 実装と Mock 実装）
- 注文の状態管理と永続化（SQLite）
- 起動時リコンシリエーション（再起動後の自動復旧）
- 監視プロセス（SystemMonitor）によるシステム健全性チェック
- マーケットカレンダー / ニュース収集等のデータユーティリティ

このリポジトリは実運用設計を意識したコンポーネント分離（API 層、永続化層、ビジネスロジック層）を採用しています。

主な機能一覧
-------------
- 環境設定ウィザード（.env の対話式作成 / 更新）
- 起動前設定検証ツール（.env と config/*.yaml の基本チェック）
- ExecutionEngine（シグナルの読み取り→Gate検査→発注→push ドレイン）
- OrderManager / OrderRecord（注文状態遷移の管理）
- OrderRepository（SQLite による注文の永続化とインデックス・整合性）
- Broker API 抽象（Protocol）＋実装：
  - MockBrokerClient（テスト / ペーパートレード用）
  - KabuStationClient（kabuステーション REST API 実装）
- RiskManager（Gate1/2/3 のリスクガード：余力・ポジション上限・レート制限・サーキットブレーカー・ドローダウン）
- Reconciler（起動時の OrderSent 照合とポジション差分検出）
- データユーティリティ（マーケットカレンダー管理、ニュース収集など）
- 監視ループ（サーバーログやリソース監視を行う監視プロセス）

セットアップ手順
---------------
前提
- Python 3.10 以上（型アノテーションに PEP 604 等を使用）
- 標準ライブラリの sqlite3 は不要インストール
- 以下の外部パッケージ（最低限想定）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML のパース検証に利用、無くても検証はスキップ）
これらを requirements.txt がある場合は pip install -r requirements.txt で導入してください。
例（手動インストール）:
  pip install duckdb httpx websocket-client defusedxml PyYAML

プロジェクトの初期設定
1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 必要なライブラリをインストールする（上記参照）。
3. .env を作成する
   - 対話式ウィザードを使う（推奨）:
       python -m kabusys.config_setup
   - または手動でルートの .env ファイルを作成。最低限必要な環境変数:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_password_here
     - デフォルトの DB パス等は .env のデフォルトがあるため未設定でも動作する箇所がありますが、必須トークンは必ず設定してください。

自動 .env ロード
- 起動時に .env, .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効にするには環境変数を設定:
    KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD        — kabuステーション API パスワード（必須）
- 任意 / 設定推奨
  - KABUSYS_ENV（development|paper_trading|live） — 実行環境
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db） — 監視用 DB（paper_trading では切り分け）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知設定
  - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - PAPER_FILL_MODE（instant|partial|never|reject） — ペーパートレードの約定挙動
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1）

使い方（主要コマンド）
--------------------

環境設定ウィザード（.env の作成/更新）
  python -m kabusys.config_setup
- 対話式に項目を入力して .env を生成します。
- 終了後に python -m kabusys.validate_config で検証することを推奨します。

設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
- .env と config/*.yaml（存在する場合）の基本的な整合性チェックを行います。
- --strict を付けると警告も失敗扱い（exit code 1）になります。

Execution エンジン（取引実行）
- ペーパートレード（推奨テストモード）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 開発モード（Mock）
  KABUSYS_ENV=development python -m kabusys.run_execution
- run_execution は pid ファイル、stop flag（data/stop_requested.flag / kill.flag）を利用します。
- paper_trading は実運用用の SQLite とは別の PAPER_TRADING_SQLITE_PATH に書き込みます。

監視プロセス（SystemMonitor）
  python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意。

構成ファイル / DB の初期化
- orders テーブル等は起動時に init_*.py 的な関数で冪等作成されます（OrderRepository.init_orders_db など）。
- config/*.yaml はプロジェクトで利用される設定ファイル群（存在しない場合はウィザードや別スクリプトで生成する想定）。PyYAML がない場合は YAML の構文チェックはスキップされます。

停止 / 停止フラグ
- data/stop_requested.flag を作成すると run_execution / run_monitoring は次回ループで終了します。
- kill.flag による Kill Switch 機構があり、本番起動時は kill.flag の存在に注意（KILL_FLAG_CLEAR_ON_START=1 で自動クリアが可能だが本番では推奨されません）。

設計上のポイント（開発者向けメモ）
---------------------------------
- 注文状態管理は OrderRecord と OrderManager が分離しており、OrderRecord は DB に依存しない純粋ロジックです。
- send_order のフローはクラッシュ安全性を意識した 2 相永続化（OrderSent の永続化 → broker 送信 → broker_order_id の永続化 → OrderAccepted への更新）を採用しています。
- Reconciler は起動時に OrderSent 状態の注文をブローカーと突合し、可能な限り状態を復旧します。
- RiskManager は Gate1/2/3 を提供し、発注前・送信前・約定後のリスク制御を担います（サーキットブレーカー・トークンバケツ方式のレート制限等）。
- ブローカークライアントは Protocol（BrokerAPIProtocol）で抽象化され、環境に応じて Mock または本実装を切り替えます（BrokerClientFactory）。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - execution/
    - broker_api.py          — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings を使ったクライアント生成
    - kabu_client.py         — kabu station REST API 実装
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite を使った永続化層
    - order_manager.py       — 注文発行・送信・同期・キャンセルの上位 API
    - execution_engine.py    — ExecutionEngine（シグナル取り込み→発注フロー）
    - reconciler.py          — 起動時の自動復旧・突合
    - risk_manager.py        — Gate1/2/3 のリスク制御
  - data/
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — （外部データ取得用クライアント、実装想定）
  - monitoring/
    - monitoring_db.py       — 監視DB 初期化・API（参照）
    - system_monitor.py      — システム監視ロジック（参照）
  - utils/
    - logging_setup.py       — ロギングセットアップヘルパ
    - process_priority.py    — プロセス優先度設定
  - config/                  — YAML 設定ファイル群（system_config.yaml 等）
  - .env, .env.local         — 実行環境の設定（プロジェクトルート）
  - data/                    — DB、PID、flag ファイルの格納（data/kabusys.duckdb, data/monitoring.db 等）

注意事項 / 推奨
---------------
- .env は決して Git にコミットしないでください（README 内の .env は例示に留める）。
- 本番（KABUSYS_ENV=live）での使用は十分なテスト、通知（LINE 設定など）と監視を行ってください。validate_config の警告を必ず確認してください。
- paper_trading（ペーパートレード）モードは運用に近いテストを行うための推奨モードです。PAPER_FILL_MODE で約定挙動をシミュレートできます。
- YAML 設定ファイル（config/*.yaml）が必要な場合はプロジェクト内スクリプト（generate_config.py 等）が用意されている可能性があります。validate_config はこれらの有無・パースをチェックします（PyYAML がインストールされている場合）。

ライセンス、貢献
----------------
リポジトリ内に LICENSE がある場合はそちらを参照してください。バグ報告や機能提案は issue を作成してください。

最後に
------
この README はコードベースの主要機能と起動方法の要点をまとめたものです。各モジュールの詳細な設計意図や API 仕様はソースコード内の docstring やコメントに記載されています。初回セットアップ時は以下の順を推奨します：

1. 仮想環境を用意・依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で検証
4. KABUSYS_ENV=paper_trading python -m kabusys.run_execution でエンジン起動（テスト）

必要なら、README をベースに運用手順やデプロイ手順を追加してください。