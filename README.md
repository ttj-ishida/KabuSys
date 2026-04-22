# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）。

以下はこのリポジトリに含まれる主要な機能と、ローカルでのセットアップ・実行方法の説明です。

注意: 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。実運用での利用は慎重に行ってください（特に KABUSYS_ENV=live 時）。

---

プロジェクト概要
- KabuSys はシグナルに基づいて発注を行う ExecutionEngine、発注状態の永続化・管理、リスクガード、リコンシリエーション、監視（Monitoring）やデータ収集（マーケットカレンダー・ニュース収集）などを提供するモジュール群です。
- 開発・テスト向けに kabuステーション API を模した MockBrokerClient を備え、Paper Trading（ペーパートレード）モードで本番 DB を汚さずに動作させられます。

主な機能一覧
- 設定ウィザード（.env 自動生成）: kabusys.config_setup
- 設定検証 CLI (.env と config/*.yaml の整合性チェック): kabusys.validate_config
- ExecutionEngine: シグナルを読み取り発注・監視するエンジン（run_execution）
- Monitoring: SystemMonitor のポーリングループ起動スクリプト（run_monitoring）
- Broker クライアント層:
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST API 実装、未実装箇所あり）
- 注文永続化（SQLite）: OrderRepository（orders テーブルの作成/操作）
- 注文状態管理: OrderRecord（状態遷移のバリデーション）
- リスク管理: RiskManager（Gate1/2/3 の多段ガード）
- リコンシリエーション: Reconciler（起動時に OrderSent を broker と照合）
- データモジュール:
  - calendar_management（JPX 営業日管理、next_trading_day など）
  - news_collector（RSS 収集・正規化）

セットアップ手順（ローカル開発用）
1. リポジトリをクローンしてワークディレクトリへ
   - （例）git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 必要なパッケージをインストール
   - 以下はソースで使用されている主な依存例です。実際の requirements.txt が無い場合は適宜インストールしてください。
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（YAML 検証を行いたい場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env に設定（プロジェクトルートに配置）。Git にコミットしないこと。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります:
     - python -m kabusys.validate_config --strict

6. データベース等の準備
   - デフォルトの DB パス（.env を未設定時のデフォルト）:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視 DB): data/monitoring.db
     - Paper Trading 用 SQLite: data/paper_trading.db
   - 必要に応じてディレクトリを作成（スクリプト実行時に自動作成されることもありますが、手動作成しておくと確実です）。

使い方（主要コマンド）
- 環境ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
  - 対話形式で入力し、最終確認で Y を選ぶと .env を書き出します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

- 実際の ExecutionEngine を起動（セッション実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使われます。live は未実装または要注意。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。

設定項目（主な環境変数）
- 必須 (validate でもチェックされる)
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、default: INFO）
  - KABU_API_BASE_URL — kabu station API の base URL（default: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、default: 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

挙動に関する重要なポイント
- KABUSYS_ENV:
  - development / paper_trading: MockBrokerClient を使い、実取引は行わない（開発・検証向け）
  - live: 本番想定（注意）。validate_config は live の場合に注意を促す警告を出します。
- Paper trading:
  - PAPER_FILL_MODE 環境変数で MockBrokerClient の挙動を指定できます（instant / partial / never / reject）。Settings.paper_fill_mode で取得。
- Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）を検出すると ExecutionEngine が発注を停止・キャンセルします。
  - 起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START が 1 の場合のみ自動的にクリアされて起動します（本番での自動クリアは推奨されません）。
- Reconciliation:
  - 起動時に OrderSent の不確定注文を broker と照合し、状態を復旧しようとします（Reconciler）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings 定義（.env 自動ロード機能有り）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI（.env / config/*.yaml 検証）
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI のデータモデル・Protocol・ファクトリ
    - kabu_client.py         — kabuステーション REST API クライアント（httpx）
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に応じた broker client 生成
    - order_record.py        — OrderRecord 型と状態遷移ロジック
    - order_repository.py    — SQLite を用いた永続化層（orders テーブル）
    - order_manager.py       — OrderManager（外向け API: create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine（セッション・発注ループ）
    - reconciler.py          — 起動時のリコンシリエーション処理
    - risk_manager.py        — Gate1/2/3 によるリスク制御
    - ...（その他補助モジュール）
  - data/
    - calendar_management.py — マーケットカレンダー管理（next_trading_day など）
    - news_collector.py      — RSS ニュース収集
    - ...（J-Quants クライアント等がある想定）
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・ログ用 API（実装あり）
    - system_monitor.py      — システムメトリクス収集（実装あり）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

開発メモ / トラブルシューティング
- .env 自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を起点）を探索して .env と .env.local を自動でロードします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- YAML 検証:
  - validate_config は PyYAML が無い場合 YAML の中身検証をスキップします。YAML 検証が必要なら PyYAML をインストールしてください。
- 実行中の停止:
  - run_execution および run_monitoring はプロジェクトルート data ディレクトリ内に stop_requested.flag を置くことで外部からループを終了できます（run_* の実装内で参照）。
- 本番（live）に関して:
  - KABUSYS_ENV=live では LINE 通知や監視の設定が重要になります。validate_config は live 時に注意喚起を行います。live 向けの broker クライアント（KabuStationClient）については実装と接続先の確認を必ず行ってください。

ライセンス / コントリビュート
- 本リポジトリのライセンス・貢献ルールは省略されています。利用・改変・配布はリポジトリに含まれる LICENSE / CONTRIBUTING を参照してください（無い場合はリポジトリ管理者に問い合わせてください）。

最後に
- まずは仮想環境を作り、python -m kabusys.config_setup で .env を作成、python -m kabusys.validate_config で検証してから python -m kabusys.run_execution（または run_monitoring）を実行して動作確認することを推奨します。