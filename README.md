# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買のための内部ライブラリ・実行スクリプト群です。シグナルの発行 → 発注 → 約定リコンシリエーション → 監視までの主要フローを含むモジュール群を提供します。テスト・開発用にブローカーのモック実装（MockBrokerClient）を備えており、paper_trading / development 環境で実行できます。

主な特徴
- シグナル駆動の ExecutionEngine（シグナル処理 + WebSocket push ドレイン）
- 注文状態管理（OrderRecord）と永続化（SQLite）
- ブローカー API 抽象化（BrokerAPIProtocol）と Mock クライアント
- 起動時リコンシリエーション（Reconciler）でクラッシュ後の整合性回復
- 3段階のリスクガード（Gate1/2/3）：余力、レート制限、ドローダウン等
- 環境設定ウィザード（.env 生成）と設定検証 CLI
- 市場カレンダー管理、ニュース収集モジュール（Data 側のユーティリティ）
- 監視ループ（SystemMonitor）用の起動スクリプト

必須 / 推奨機能一覧（抜粋）
- 環境設定の自動読み込み（.env / .env.local）と Settings ラッパー
- validate_config: .env と config/*.yaml の存在・妥当性チェック
- config_setup: 対話式で .env を作成・更新
- run_execution: ExecutionEngine を起動（paper_trading では MockBrokerClient を使用）
- run_monitoring: SystemMonitor ポーリングループを起動

セットアップ手順（ローカル開発想定）
1. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   プロジェクトに requirements.txt があればそれを使ってください。無ければ最低限必要そうなパッケージは次の通りです:
   - duckdb
   - httpx
   - websocket-client
   - PyYAML
   - defusedxml

   例:
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   SQLite と sqlite3 モジュールは標準ライブラリのため別途不要です。

3. プロジェクトルートに移動（README が存在するディレクトリ）
   このパッケージは src/ 配下にパッケージとして配置されています。pip インストール（開発モード）が必要な場合:
   - pip install -e .

使い方（基本コマンド）
- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスに保存可能
  - ウィザード終了後は .env に保存されます（.env を Git にコミットしないでください）

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict
  - チェック対象:
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
    - 任意環境変数や LOG_LEVEL / KABUSYS_ENV の妥当性
    - config/*.yaml の存在と（PyYAML がある場合は）パースチェック

- 実行エンジン起動（注文処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて動作:
    - development / paper_trading: MockBrokerClient を使用（paper_trading では paper_trading 用 SQLite を使用）
    - live: 現状 NotImplemented（BrokerClientFactory が NotImplementedError を投げます）
  - 停止: プロセス外で data/stop_requested.flag を作成すると安全停止処理が動作します
  - PID ファイル: data/execution.pid（デフォルト）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境にかかわらず本番 sqlite_path を使用して監視 DB に接続します
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で調整可能
  - 停止: data/stop_requested.flag を作成

主要な環境変数（重要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨
  - KABUSYS_ENV — 開発環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
  - KABU_API_BASE_URL — kabu station のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0 / 1）

注意点 / 運用に関するメモ
- .env はプロジェクトルートに置き、絶対にリポジトリにコミットしないでください。
- validate_config を CI / デプロイ前チェックに組み込むと安全です（--strict オプション推奨）。
- run_execution は実行前に kill.flag（data/kill.flag）を確認し、クリア方針に応じて起動を拒否できます（KILL_FLAG_CLEAR_ON_START）。
- paper_trading 環境では MockBrokerClient を使用し、発注はローカル DB に記録されます（本番ブローカーに影響しません）。
- live ブローカー実装は現状未実装で、BrokerClientFactory.create() は NotImplementedError を投げます。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py  — パッケージ定義（__version__ = "0.1.0"）
    - config.py  — 環境変数の自動読み込み・Settings ラッパー
    - config_setup.py  — .env 対話式ウィザード
    - validate_config.py  — 起動前設定検証 CLI
    - run_execution.py  — ExecutionEngine 起動スクリプト（セッション制御）
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
    - execution/
      - broker_api.py  — BrokerAPI のデータモデル・Protocol・例外・ファクトリ
      - kabu_client.py — kabu station REST クライアント（httpx）
      - mock_client.py — MockBrokerClient（テスト用）
      - broker_factory.py — Settings に応じたクライアント生成
      - order_record.py — 注文状態モデルと状態遷移検査
      - order_repository.py — SQLite 永続化層（orders テーブル）
      - order_manager.py — 発注フロー（作成・送信・同期・キャンセル）
      - execution_engine.py — セッション実行ロジック（signal/drain）
      - reconciler.py — リコンシリエーション（再起動時復旧）
      - risk_manager.py — Gate1/2/3 のリスク統制
    - data/
      - calendar_management.py — マーケットカレンダー管理
      - news_collector.py — RSS ニュース収集（前処理＋保存）
      - (jquants_client など参照されるモジュール)
    - monitoring/
      - monitoring_db.py  — 監視 DB 初期化・ログ（参照）
      - system_monitor.py  — SystemMonitor 実装（参照）
    - utils/
      - logging_setup.py — ログ設定ユーティリティ（参照）
      - process_priority.py — プロセス優先度設定ユーティリティ（参照）

（注）上記の "参照" と付いているモジュールは本 README に含められた抜粋の中で利用されています。実際のリポジトリでは対応するファイルが存在するはずです。

テスト・開発向けヒント
- 自動で .env を読み込みたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利）。
- MockBrokerClient は fill_mode により振る舞いを変えられます（instant / partial / never / reject）。paper_trading 環境の動作確認に便利です。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書きできます。値が不正な場合はデフォルト 60 秒にフォールバックします。

トラブルシューティング（よくあるケース）
- validate_config がエラーを出す:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）が未設定になっている可能性があります。
  - KABUSYS_ENV が "development" / "paper_trading" / "live" 以外になっていないか確認してください。
  - PyYAML がないと YAML のパース検査はスキップされます（警告）。
- run_execution で PID / kill.flag による起動拒否:
  - data/kill.flag が残っている場合、KILL_FLAG_CLEAR_ON_START が 0 のとき起動を拒否します。

ライセンス / コントリビューション
- この README にはライセンス情報は含まれていません。リポジトリに LICENSE ファイルがある場合はそちらを参照してください。

以上が KabuSys の概要・セットアップ・主要コマンド・ディレクトリ構成のまとめです。追加で README に入れたいチュートリアルや実行例（環境変数のサンプル .env テンプレート等）があれば作成します。