# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株の自動売買システム「KabuSys」の実装です。  
本 README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

注意：実行にはローカル環境に合わせた設定（.env / config/*.yaml）と外部ライブラリが必要です。まずは設定ウィザードと設定検証ツールを使って環境を整えてください。

---

目次
- プロジェクト概要
- 機能一覧
- 要求事項・依存関係
- セットアップ手順
- 使い方（主要コマンド）
- 重要な環境変数
- ディレクトリ構成（主なファイル説明）

---

プロジェクト概要
- KabuSys は kabuステーション（kabu API）や J-Quants 等を利用した証券取引の自動売買フレームワークです。
- 発注フロー、注文状態管理（状態遷移）、リスクガード（Gate1/2/3）、起動時のリコンシリエーション、監視（Monitoring）などのコンポーネントを備えています。
- 実運用（live）、ペーパートレード（paper_trading）、開発（development）に合わせて挙動を切り替え可能。ペーパートレード時は MockBrokerClient を使用して本番環境と分離します。

機能一覧
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の存在/妥当性チェック）: kabusys.validate_config
- 実行エンジン（ExecutionEngine）: シグナルの読み込み→Gate検査→発注→push/drainループ
- 注文管理:
  - OrderRecord（状態遷移を厳格に管理）
  - OrderRepository（SQLite による永続化）
  - OrderManager（発注・同期・キャンセル等の順序保証）
- ブローカー抽象化:
  - BrokerAPIProtocol（Protocol によるインターフェース）
  - MockBrokerClient（テスト/ペーパー用）
  - KabuStationClient（kabuステーション REST/WebSocket 実装）
- リスク管理（RiskManager）:
  - Gate1（余力・重複・ポジション上限）
  - Gate2（レート制限・サーキットブレーカー）
  - Gate3（ドローダウン監視 → kill_switch）
- リコンシリエーション（Reconciler）: 再起動時に OrderSent の注文をブローカーと照合、ポジション差分検出
- 監視プロセス（SystemMonitor のポーリングループ）: kabusys.run_monitoring

要求事項・依存関係（代表）
- Python 3.9+（型アノテーション・Pathlib 等を利用）
- 推奨パッケージ（実行に必要／推奨）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config YAML の中身を検証したい場合）
  - defusedxml（ニュース収集モジュールの安全な XML パース）
- 標準ライブラリ: sqlite3, threading, logging, json 等
- 注意: 実際に kabuステーション を利用する場合はローカルで kabuステーションアプリが起動している必要があります（デフォルト base_url は http://localhost:18080/kabusapi）。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb httpx websocket-client defusedxml
   - （YAML 検証を利用する場合）pip install pyyaml

   ※ requirements.txt がある場合はそれを利用してください。

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークン、kabu API パスワードなどを入力して .env を生成します。
     - 途中で Enter を押すと既存値 / デフォルトを利用できます。
   - 生成後は .env を絶対に Git にコミットしないでください（ウィザードも注意喚起します）。

5. 設定の検証
   - python -m kabusys.validate_config
   - 重要な環境変数が未設定・不正な場合はエラー／警告が出ます。
   - --strict を付けると警告も失敗扱い（exit code 1）になります:
     - python -m kabusys.validate_config --strict

6. DB 初期化（orders テーブル等の作成は起動時に自動で行われます）
   - 実行前に data/ ディレクトリを作成しておくと便利です。デフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - Execution/Monitoring 起動時に必要なテーブルが初期化されます（init_orders_db / init_monitoring_db 等）。

使い方（主要コマンド）
- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン（注文フローを実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって動作が変わります:
    - development / paper_trading → MockBrokerClient を使用
    - live → 本番ブローカー（現在未実装。設定によってはエラー）

- 監視プロセス（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔 (秒) を上書き可能（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は共有）

主な環境変数（必須 / 代表）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- オプション（重要）:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB（分析DB）パス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（paper_trading 時に使用）
  - LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番環境での通知用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

注意点（運用上）
- KABUSYS_ENV=live は本番動作になります。validate_config は live の場合に追加警告を出します。LINE 通知設定などを必ず確認してください。
- stop_requested.flag / kill.flag / pid ファイル:
  - 実行プロセスは data/stop_requested.flag を検出すると安全停止します。
  - PID ファイル: data/execution.pid（ExecutionEngine が起動時に書きます）
  - kill.flag が存在すると ExecutionEngine は原則起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 を使うと強制クリアして起動可能）。
- Paper trading（KABUSYS_ENV=paper_trading）は MockBroker で本番 DB と分離して動作します（paper_sqlite_path を使用）。

ディレクトリ構成（主要ファイルと概要）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py — .env を対話式で作るウィザード
  - validate_config.py — 起動前チェック CLI（必須 env や config/*.yaml の検証）
  - run_execution.py — ExecutionEngine 起動スクリプト（メインの注文エンジン）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - kabu_client.py — kabu station REST/WebSocket 実装（KabuStationClient）
    - mock_client.py — MockBrokerClient（テスト／ペーパー用）
    - broker_factory.py — Settings から適切なブローカークライアントを生成
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite による永続化層（orders テーブル）
    - order_manager.py — 発注フロー（作成・送信・同期・キャンセル）
    - execution_engine.py — ExecutionEngine（シグナル処理と push/drain ループ）
    - reconciler.py — 起動時のリコンシリエーション（OrderSent 照合・ポジション差分）
    - risk_manager.py — Gate1/2/3 によるリスク制御
  - data/
    - calendar_management.py — マーケットカレンダー管理（JPX カレンダー / next_trading_day 等）
    - news_collector.py — RSS からのニュース収集（前処理・安全対策あり）
    - jquants_client.py — （参照されるがここに含まれる想定の J-Quants クライアント）
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ記録（init_monitoring_db 等）
    - system_monitor.py — システム監視ロジック（使用される run_monitoring）
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ（各プロセスで使用）
    - process_priority.py — プロセス優先度設定ユーティリティ

補足・ヒント
- YAML 検証：validate_config は PyYAML がインストールされている場合に config/*.yaml をパースして中身の妥当性をチェックします。未インストール時は YAML 検証をスキップして警告を出します。
- 自動 .env 読み込み：config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ペーパートレードの約定挙動：PAPER_FILL_MODE（instant | partial | never | reject）で Mock の約定動作を切替え可能です。これにより動作検証やユニットテストが容易になります。

---

お問い合わせ・貢献
- バグ報告や改善提案は issue を送ってください。プルリク歓迎です。
- 実稼働を行う場合は十分な監視・アラート設定、リスクテストを行ってから運用してください（特に KABUSYS_ENV=live）。

以上。必要であれば README にサンプル .env.example や docker / systemd の起動例（サービス定義）、詳細な開発者向けドキュメントを追記できます。どの情報がさらに必要か教えてください。