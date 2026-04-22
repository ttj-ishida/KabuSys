KabuSys
======

日本株自動売買システムのコアライブラリ（簡易版）。
このリポジトリには発注エンジン、リスク管理、ブローカークライアント、監視ループ、環境設定ウィザード / 検証ツールなどの主要コンポーネントが含まれます。

プロジェクト概要
--------------
KabuSys はローカル環境やペーパートレード環境で安全に日本株の自動売買処理を実行できるよう設計されたライブラリ群です。  
主な設計方針は次のとおりです。

- 明確に分離された層 (API クライアント層 / 実行エンジン / 永続化 / リスク管理 / 監視)
- 発注フローのクラッシュ安全性（OrderSent の二相永続化や起動時のリコンシリエーション）
- 3段階のリスクガード（Gate1: シグナルレベル、Gate2: エグゼキューション、Gate3: ドローダウン監視）
- テスト・開発用の Mock ブローカ（paper_trading / development で利用）
- .env ベースの設定ウィザードと起動前検証ツール

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup で .env の作成・更新を対話的に行う
- 設定検証 CLI: python -m kabusys.validate_config で .env / config/*.yaml の妥当性をチェック（--strict で警告も FAIL 扱い）
- 実行エンジン: ExecutionEngine によるシグナル取得→発注→WebSocket ドレインのセッション実行（python -m kabusys.run_execution）
- 監視ループ: SystemMonitor を定期実行（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL で間隔を調整
- ブローカークライアント:
  - MockBrokerClient（テスト／ペーパートレード用）
  - KabuStationClient（kabuステーション REST API 実装、httpx / websocket-client 使用）
- 注文状態モデルと永続化（OrderRecord / OrderRepository、SQLite を使用）
- 起動時リコンシリエーション（Reconciler）で OrderSent の不確定注文を復旧
- リスクマネージャ（レート制限、サーキットブレーカー、ポジション上限、ドローダウン監視）
- データ周りのユーティリティ（DuckDB を使ったカレンダー管理、RSS ニュース収集等）
- 自動的な .env ロード（プロジェクトルートの .env / .env.local を読み込む。無効化可）

セットアップ手順
-------------
1. リポジトリをクローンして作業ディレクトリに移動します。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 必要なパッケージをインストール
   - 最低限必要となる主なパッケージ例:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config/*.yaml のパース検証を行いたい場合）
   - 例:
     python -m pip install duckdb httpx websocket-client defusedxml PyYAML

   ※ requirements.txt がない場合は上のパッケージをプロジェクトの用途に応じて追加してください。

4. .env を作成する
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - または自分で .env を作成し、以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - その他の環境変数（オプション）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
     - KABU_API_BASE_URL（kabu station のベース URL）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
     - PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）
     - KILL_FLAG_CLEAR_ON_START（0/1、本番で自動クリアさせたくない場合は 0 推奨）

5. 起動前検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

使い方
------
- 環境設定ウィザード
  - 実行: python -m kabusys.config_setup
  - 既存の .env があれば読み込み、Enter で既存値を再利用できます。
  - ウィザード完了後に .env を保存します。

- 設定検証
  - 実行: python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1) を返します。
  - PyYAML 未インストール時は YAML の中身検証はスキップしますがファイルの存在は警告されます。

- 実行エンジン（注文処理）
  - 実行: python -m kabusys.run_execution
  - KABUSYS_ENV によって挙動が変わります:
    - development / paper_trading: MockBrokerClient を使用（安全）
    - live: 本番ブローカクライアントを想定（現状未実装で NotImplementedError を返す箇所あり）
  - paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。

- 監視ループ
  - 実行: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用します。

- 停止制御 / PID / kill フラグ
  - 実行中に停止を促すためのフラグ:
    - data/stop_requested.flag（run_* スクリプトが検出して終了するためのフラグ）
    - data/kill.flag（ExecutionEngine が検査する kill switch のフラグ）
  - PID ファイル: data/execution.pid などにプロセスIDを書き出します（config でパス指定可）。

設定（主要な環境変数）
------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL（kabu station 用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート）
  - PAPER_FILL_MODE（instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START（0 or 1、本番は 0 を推奨）

ディレクトリ構成（主なファイル）
------------------------------
リポジトリの src/kabusys 以下の主要ファイル・モジュール:

- __init__.py
  - パッケージ定義、__version__

- config.py
  - .env 自動ロード（.env / .env.local）、Settings クラス（環境変数のラッパ）

- config_setup.py
  - 対話式 .env ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）

- execution/ （発注関連）
  - broker_api.py         — BrokerAPIProtocol、データモデル、ファクトリ
  - kabu_client.py        — KabuStationClient (httpx/websocket-client ベース)
  - mock_client.py        — MockBrokerClient（テスト用）
  - broker_factory.py     — Settings に応じてクライアントを生成
  - order_record.py       — 注文状態モデルと状態遷移ロジック
  - order_repository.py   — SQLite 永続化（orders テーブル）
  - order_manager.py      — 外向きの発注 API（create/send/sync/cancel）
  - execution_engine.py   — セッションの全体制御（シグナル処理 + push ドレイン）
  - reconciler.py         — 起動時のリコンシリエーション
  - risk_manager.py       — Gate1/2/3 によるリスク統制

- data/（データ関連）
  - calendar_management.py — DuckDB を用いたマーケットカレンダー管理
  - news_collector.py      — RSS ニュース収集（defusedxml 等を使用）

- monitoring/（監視関連）
  - monitoring_db.py       — SQLite での監視用テーブル初期化 / ログ書き込み
  - system_monitor.py      — システムメトリクス取得と監視ロジック（run_monitoring から使用）

注意事項 / 運用上のヒント
------------------------
- 本番運用時は KABUSYS_ENV=live とし、LINE の通知等必要なアラート設定を行ってください。validate_config が live の場合に追加警告を出します。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- 起動前に python -m kabusys.validate_config を実行して設定の不備を確かめることを強く推奨します。
- paper_trading / development 環境では MockBrokerClient を使うため、実際の送金や外部 API に影響を与えずテスト可能です。
- PyYAML をインストールしておくと config/*.yaml のパース検証が有効になります。未インストールだと検証をスキップしますが、存在チェックは行われます。
- .env の自動読み込みはデフォルトで有効。テストなどで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine は起動時に PID ファイルを書き、終了時に削除します。kill.flag が既に存在する場合、KILL_FLAG_CLEAR_ON_START によって挙動が変化します（0: 起動拒否、1: 自動クリアして起動）。

参考コマンドまとめ
-----------------
- .env 作成/更新: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース上の初期値）。  
ライセンス情報はリポジトリのルートに置いてください（このサンプルには含まれていません）。

追加情報・拡張
--------------
- Live 環境向けの実際の KabuStationClient の運用仕様（ネットワーク設定、認証、trade_password など）を詰める必要があります。現状コードはベース実装を備えていますが、運用前の十分な検証が必要です。
- 監視・アラート（LINE など）や DB マイグレーション処理、ログの集約（例: ローテート）などは運用環境に合わせて拡張してください。

問題報告・貢献
--------------
バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。テストとドキュメントを付けていただけると助かります。

以上。必要なら README にサンプル .env のテンプレートやより詳細な運用手順（systemd ユニットや Dockerfile の例など）を追加できます。追加を希望する内容を教えてください。