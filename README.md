KabuSys
=======

注意: 下記はこのリポジトリのコードをもとに作成した README です。実際の配布パッケージでは pyproject.toml や requirements.txt を参照してください。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買システムの骨組み（エンジン・ブローカー抽象・リスクガード・監視・データ処理）を提供する Python コードベースです。  
主な設計方針は次のとおりです:

- ExecutionEngine によるシグナル駆動の発注フロー（シグナル処理 + push ドレイン）
- OrderRecord（状態遷移）と OrderRepository（SQLite 永続化）による堅牢な注文管理
- 3 段階のリスクガード（Gate1: シグナルレベル、Gate2: レート制限／CB、Gate3: ドローダウン監視）
- Paper trading（モックブローカー）と開発用のサポート。Live（kabu station）クライアントは将来的な実装対象
- .env ベースの設定（config ウィザード / 検証ツール付き）
- DuckDB / SQLite を使ったデータ管理（カレンダー、ニュース、position_entries、orders 等）

機能一覧
--------
- .env 対話ウィザード（kabusys.config_setup）での初期設定生成・更新
- 設定検証 CLI（kabusys.validate_config）で起動前の必須設定チェック（--strict オプションあり）
- ExecutionEngine（run_execution）: シグナル処理 → 発注 → push ドレイン → セッション終了のワークフロー
- MockBrokerClient によるペーパートレード（fill_mode: instant/partial/never/reject）
- 注文永続化（SQLite）と状態遷移の厳格管理（OrderRecord）
- 再起動時の自動リコンシリエーション（Reconciler）
- RiskManager によるレート制限／サーキットブレーカー／ポジション制約／ドローダウン検知
- SystemMonitor（監視ループ）（run_monitoring）: システムリソースや監視イベントの定期ログ／DB 保存
- データ系ユーティリティ（マーケットカレンダー管理、RSS ニュース収集 等）

前提条件
--------
- Python 3.9+（コード上の型ヒントと一部機能より）
- 以下の主要パッケージ（最低限、環境によって追加が必要）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config の YAML 検証：任意だが推奨）
  - defusedxml（ニュース収集モジュールで使用）
- 標準ライブラリの sqlite3, logging など

セットアップ手順
---------------
1. リポジトリをクローンする／展開する。
2. 仮想環境を作成して有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストールする（requirements.txt がある場合はそれを利用）。無ければ最低限下記を pip で入れてください。
   - pip install duckdb httpx websocket-client PyYAML defusedxml
4. .env を用意する（次節参照）。初回はウィザードを推奨。
5. 必要な DB 用ディレクトリ（data）を作成：
   - mkdir -p data

環境変数 / .env（主なキー）
--------------------------
このプロジェクトは .env（プロジェクトルート）または環境変数から設定を読み込みます。自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な必須キー:
- JQUANTS_REFRESH_TOKEN  — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（必須）

その他主要キー（任意 / 既定値あり）:
- KABUSYS_ENV            — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL      — kabu station API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 任意（本番時のアラート通知）
- KILL_FLAG_CLEAR_ON_START — 0 / 1（起動時に kill.flag を自動クリアするか）

簡易 .env 例（実運用では機密情報は適切に保護してください）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

設定ウィザード
-------------
対話式ウィザードで .env を生成・更新できます:
- python -m kabusys.config_setup
ウィザード終了後に .env を保存するか確認されます。生成後は validate_config でチェックすることを推奨します。

設定検証
--------
起動前に設定を検証するための CLI:
- python -m kabusys.validate_config
- 警告も失敗扱いにする: python -m kabusys.validate_config --strict

このツールは必須環境変数の有無、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ有無、config/*.yaml の存在と（PyYAML があれば）パースチェック、本番環境 (live) 時の追加ガード等をチェックします。

実行方法（運用）
----------------
- 実行エンジン（発注フロー）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使います（paper_trading は paper_trading 用 SQLite に保存して本番 DB と分離）。
  - KILL/STOP: data/stop_requested.flag および kill.flag（settings.kill_flag_path）により起動制御や強制停止が行われます。
  - PID ファイルは data/execution.pid（デフォルト）に記録されます。

- 監視ループ:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を参照（環境にかかわらず）。

注意点:
- Live ブローカークライアント（kabu station 実装）の使用は本リポジトリの一部で未実装・未検証の箇所があります。デフォルトでは MockBrokerClient が利用されます。
- stop_requested.flag が存在すると起動しない／実行中に検知して安全に停止する挙動があります。
- kill.flag（KILL スイッチ）については設定に応じて自動クリアを行うかどうかが制御されます（KILL_FLAG_CLEAR_ON_START）。

主要コマンドまとめ
-----------------
- .env の対話式作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（発注）:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

開発者向け（主要コンポーネント説明）
-----------------------------------
- config.py / Settings:
  - .env 自動ロード（.env, .env.local）と Settings クラス（プロパティ経由の型検証）。
- config_setup.py:
  - .env を対話的に生成・更新するウィザード。
- validate_config.py:
  - 起動前チェック用の CLI。
- execution/:
  - broker_api.py: BrokerAPI のデータモデル、Protocol、例外、ファクトリ（Mock / KabuStation）
  - kabu_client.py: kabu station REST API 実装（httpx ベース）
  - mock_client.py: テスト用 MockBrokerClient（fill_mode サポート）
  - order_record.py: 注文状態機械（OrderRecord）と遷移検証
  - order_repository.py: SQLite ベースの永続化層
  - order_manager.py: DB と Broker を組み合わせて発注・同期・キャンセルを行う高レベル API
  - reconciler.py: 再起動時の照合・復旧ロジック
  - risk_manager.py: Gate1/2/3 によるリスク統制
  - execution_engine.py: シグナル処理と push ドレインを行うセッション実行エンジン
  - broker_factory.py: Settings に基づいて適切な broker client を返す
- data/:
  - calendar_management.py: JPX 営業日カレンダー管理（DuckDB ベース）
  - news_collector.py: RSS ニュース収集（安全対策多数）
  - （jquants_client 等の補助モジュールが存在する想定）
- monitoring/:
  - monitoring_db.py, system_monitor.py（監視 DB 初期化、監視ループなど、run_monitoring で利用）
- utils/:
  - logging_setup.py, process_priority.py などのユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    execution/
      __init__.py
      broker_api.py
      broker_factory.py
      kabu_client.py
      mock_client.py
      order_record.py
      order_repository.py
      order_manager.py
      reconciler.py
      execution_engine.py
      risk_manager.py
      # ...（その他補助モジュール）
    data/
      calendar_management.py
      news_collector.py
      # jquants_client 等
    monitoring/
      monitoring_db.py
      system_monitor.py
    utils/
      logging_setup.py
      process_priority.py
    # config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）

運用上の注意 / ベストプラクティス
--------------------------------
- .env は機密情報を含むため Git にコミットしないこと。
- 本番（KABUSYS_ENV=live）での運用時は LINE 通知設定など必須アラート経路を必ず設定してください（validate_config が警告を出します）。
- 実際のブローカー連携（kabu station）を行う場合は API の挙動・レート・エラー条件を現場で十分にテストしてください。MockClient は補助ツールであり、本番保証はしません。
- Kill Switch（kill.flag）／停止フラグ（stop_requested.flag）は安全停止フローに組み込まれているため、運用時の手動停止・自動監視と連携させることを推奨します。
- DuckDB / SQLite のファイルパスは環境に合わせて設定し、バックアップ・アクセス制御を行ってください。

ライセンス / 著作権
------------------
（ここにライセンス情報を記載してください。リポジトリに LICENSE ファイルがある場合はそちらに従ってください。）

付録: 便利な環境変数一覧
------------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: (必須)
- KABU_API_PASSWORD: (必須)
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時 kill.flag 自動クリア）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動ロードを無効化

以上。導入・カスタマイズにあたり不明点があれば該当モジュールのソース（上記ファイル）を参照してください。