# KabuSys

日本株自動売買システム（KabuSys）のコードベース用 README（日本語）

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド一覧と実行例）
- 環境変数（主要項目）
- ディレクトリ構成（主要ファイルとモジュールの説明）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株向けの自動売買エンジンを構成するライブラリ／実行スクリプト群です。
- 発注ロジック、注文管理、リスクガード、リコンシリエーション（再同期）、監視ループ、カレンダー管理、ニュース収集など運用に必要な主要コンポーネントを備えています。
- 実運用（live）モードのクライアントは未実装の箇所がありますが、paper_trading / development 向けの Mock ブローカーで完全にローカル検証が可能です。

主な機能一覧
- 環境設定ウィザード（.env を対話式生成）: kabusys.config_setup.run_wizard
- 起動前設定検証 CLI（.env と config/*.yaml の検証）: kabusys.validate_config
- ExecutionEngine: シグナルプル型発注ループ（発注窓・push ドレイン・PID / kill フラグ連携）
- Order マネージャ / 永続化（SQLite）: 注文の状態遷移、DB 永続化、再送・同期ロジック
- Broker 抽象化: BrokerAPIProtocol による実装分離（MockBrokerClient と KabuStationClient）
- RiskManager: 3段階のリスクガード（Gate1: シグナルレベル、Gate2: レート/CB、Gate3: ドローダウン監視）
- Reconciler: 再起動時の自動復旧（OrderSent の照合・ポジション差分検出）
- 監視（monitoring）ループ: SystemMonitor をポーリングして監視用 DB へ格納
- データ機能: JPX の営業日管理（calendar_management）、RSS ニュース収集（news_collector）
- WebSocket push 処理（kabu station の push を受信し注文同期を行う）

セットアップ手順
1. 必要な Python バージョン
   - Python 3.10 以上（typing の | 演算子や最新構文に依存するためを想定）

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML は config/*.yaml のパース検証に使用（任意）:
     - pip install PyYAML

   ※ 実プロジェクトでは requirements.txt / poetry / pyproject.toml を用意してください。

4. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

5. .env の作成（推奨: 対話式ウィザードを利用）
   - python -m kabusys.config_setup
   - もしくは .env を手動作成 (後述の主要環境変数を設定)

6. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付与（警告も exit(1)）

使い方（コマンド一覧と実行例）
- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
  - 実行後、.env を保存するか確認されます。

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗とする: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて paper_trading は Mock ブローカーを使用します。
  - 停止はプロセスに対して stop_requested.flag を data ディレクトリに作成することで指示できます（スクリプトは data/stop_requested.flag を監視します）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可（デフォルト60秒）。

- 開発 / テスト用の Mock ブローカー利用
  - .env の KABUSYS_ENV を development または paper_trading に設定すると MockBrokerClient が利用されます。
  - MockBrokerClient の動作モード: PAPER_FILL_MODE（instant, partial, never, reject）

主要環境変数（要点）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 推奨／任意:
  - KABUSYS_ENV — 実行環境（development | paper_trading | live）
  - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB のパス（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）
  - KABU_API_BASE_URL — kabu station API のベース URL（ローカルでの公開先）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知設定
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1）
  - PAPER_FILL_MODE — paper_trading 用の fill モード（instant|partial|never|reject）
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 経由で参照可能

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py
    - パッケージ初期化、バージョン定義
  - config.py
    - .env 自動読み込みロジック（.env, .env.local）、Settings クラス（環境変数アクセス）
  - config_setup.py
    - .env の対話式ウィザード生成スクリプト
  - validate_config.py
    - 起動前に .env / config/*.yaml の妥当性検査を行う CLI
  - run_execution.py
    - ExecutionEngine 用のトップレベル起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、create_broker_api ファクトリ
    - kabu_client.py
      - kabu station REST クライアント（httpx）
    - mock_client.py
      - テスト用 MockBrokerClient（fill_mode を指定可能）
    - broker_factory.py
      - Settings に応じた Broker クライアント生成
    - order_record.py
      - 注文状態遷移ロジック（OrderRecord、OrderState）
    - order_repository.py
      - SQLite を用いた orders テーブルの永続化層（init_orders_db, CRUD）
    - order_manager.py
      - 外向けの注文操作 API（create/send/sync/cancel）
    - execution_engine.py
      - 発注エンジン本体（シグナル処理・push drain・kill switch）
    - reconciler.py
      - 再起動時のリコンシリエーション（OrderSent の照合・ポジション差分検出）
    - risk_manager.py
      - 3 段階のリスク制御（Gate1/2/3）
  - data/
    - calendar_management.py
      - マーケットカレンダー管理（DuckDB と J-Quants 連携想定）
    - news_collector.py
      - RSS ニュース収集（正規化、SSRF 対策、defusedxml 利用）
    - jquants_client (参照)
      - J-Quants API 連携用クライアント（コード内で参照されています）
  - monitoring/
    - monitoring_db.py (参照元あり)
    - system_monitor.py (参照元あり)
    - 監視系の DB 初期化・ポーリング処理
  - utils/
    - logging_setup.py
    - process_priority.py
    - ロギング設定やプロセス優先度設定補助

運用上の注意
- KABUSYS_ENV=live は本番動作を意味し、設定ミスが致命的になる可能性があります。validate_config の警告や警報をよく確認してください（--strict を利用可能）。
- .env は決して Git 等にコミットしないこと。config_setup でも注意喚起してあります。
- ExecutionEngine は PID ファイルと kill.flag を利用して安全起動・停止を行います。運用時はこれらのファイルの居場所（デフォルト: data/ 以下）を運用設計に合わせて管理してください。
- 本リポジトリ内の KabuStationClient は HTTP/WS ベースの通信を行います。ローカルで kabuステーション® が稼働していない場合は MockBrokerClient を使用してください（KABUSYS_ENV=paper_trading / development）。
- データベースパスの親ディレクトリが存在しない場合、起動時に自動作成されることもありますが、事前に data/ を用意しておくことを推奨します。

トラブルシューティング
- validate_config の実行で PyYAML 未インストール警告が出たら、config/*.yaml のパース検証はスキップされます。YAML 構成を使用している場合は PyYAML をインストールしてください。
- Execution 起動時に kill.flag が存在している場合、KILL_FLAG_CLEAR_ON_START=1 でない限り起動を拒否します。意図しない起動を防ぐためのセーフガードです。

---

以上がこのコードベースの概要と基本的な使い方です。詳細は各モジュール（特に execution パッケージ内の各クラス）を参照してください。追加で README に含めたいサンプル .env のテンプレートや、CI / デプロイ手順、テストの実行方法などがあればお知らせください。