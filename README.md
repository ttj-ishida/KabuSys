# KabuSys

軽量な日本株自動売買基盤（KabuSys）のコードベース README（日本語）

概要
----
KabuSys は日本株自動売買のためのシンプルな実行基盤です。  
主な責務はシグナルから発注までの実行フロー、注文状態管理・リコンシリエーション、リスクガード、マーケットカレンダ／ニュース収集、監視（Monitoring）です。  
本リポジトリはモジュール化されており、開発・検証用にモックブローカー（MockBrokerClient）を使ってローカルで安全に動作させられます。

主な機能
--------
- 環境設定ウィザード（.env の対話式作成 / 更新）
- 設定検証 CLI（.env / config/*.yaml の存在や妥当性チェック）
- ExecutionEngine：シグナル読み込み → 発注 → WebSocket プッシュ処理（発注・再同期・kill switch）
- Order 管理：OrderRecord（状態遷移ルール）、OrderRepository（SQLite 永続化）、OrderManager（DB と Broker の橋渡し）
- RiskManager：3 段階（Gate1: シグナルレベル / Gate2: レート制限・CB / Gate3: ドローダウン監視）
- Reconciler：再起動時の OrderSent 照合・ポジション差分検出
- ブローカークライアント層：Mock と将来の KabuStationClient 実装（kabu station REST API）
- データ側ユーティリティ：マーケットカレンダー管理、ニュース収集（RSS）
- 監視ループ（SystemMonitor）と監視 DB（SQLite）

クイックセットアップ
-------------------
前提
- Python 3.8+（型アノテーションの利用から 3.8 以上を推奨）
- OS 標準の sqlite3 は利用可能

推奨パッケージ（プロジェクトにより差分あり）:
- duckdb
- httpx
- websocket-client
- pyyaml (YAML の検証に使用)
- defusedxml (RSS パースの安全対策)

例:
pip install duckdb httpx websocket-client pyyaml defusedxml

.env の用意（推奨手順）
1. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup

   ウィザードは既存の .env を読み込み、シークレットはマスク表示したうえで Enter で既存値を再利用できます。
2. 作成後、設定検証:
   python -m kabusys.validate_config
   警告を FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict

主要な環境変数（必須 / 任意）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（よく使うもの）:
  - KABUSYS_ENV            (development | paper_trading | live) デフォルト: development
  - DUCKDB_PATH            デフォルト: data/kabusys.duckdb
  - SQLITE_PATH            デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db
  - LOG_LEVEL              (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
  - KABU_API_BASE_URL      デフォルト: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
  - KILL_FLAG_CLEAR_ON_START (0|1) デフォルト: 0（本番で 1 は危険）

自動 .env 読み込み
- 起動時に OS 環境変数 > .env.local > .env の順でロードします（既存 OS 環境変数は保護されます）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（デフォルトのコマンド）
------------------------------
- 環境設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  --strict オプションで警告を FAIL として exit(1)

- ExecutionEngine を起動（本番相当のセッション実行）:
  python -m kabusys.run_execution

  挙動メモ:
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録する。
  - 起動時に data/execution.pid（デフォルト）へ PID を書き込み、停止フラグ（data/stop_requested.flag）を監視します。
  - settings.kill_flag_path（デフォルト data/kill.flag）が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 なら自動クリアして起動）。

- Monitoring を起動（監視ループ）:
  python -m kabusys.run_monitoring

  挙動メモ:
  - 環境に関わらず本番 sqlite_path を使用して監視データを記録します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - data/stop_requested.flag を検知するとループを終了します。

実行時の主要ファイル・挙動（概要）
- config.py
  - .env/.env.local を自動読み込み（デフォルト）。Settings クラス経由で設定へアクセス。
  - _require() により必須変数が未設定だと例外を投げるプロパティがある。
- config_setup.py
  - 対話式で .env を生成/更新するウィザード。
- validate_config.py
  - 起動前に必要な環境変数や config/*.yaml の有無・YAML パースをチェックする CLI。
- run_execution.py
  - ExecutionEngine の起動スクリプト。PID 書き込み、DB 初期化、Mock/実ブローカーの選択など。
- run_monitoring.py
  - 監視ループを起動するスクリプト。
- execution/
  - order_record.py: 状態遷移ロジック（OrderState、OrderRecord）
  - order_repository.py: SQLite による永続化（init_orders_db）
  - order_manager.py: 作成 → 送信 → 同期 → キャンセルのワークフロー
  - execution_engine.py: セッション駆動（シグナル処理、push ドレイン、kill switch）
  - broker_api.py: BrokerAPIProtocol、データモデル、例外、ファクトリ（Mock / KabuStation）
  - kabu_client.py: kabu station REST API クライアント（httpx）
  - mock_client.py: テスト用 MockBrokerClient（fill_mode を指定可能）
  - risk_manager.py: Gate1/2/3 の実装
  - reconciler.py: 再起動時の照合・ポジション差分チェック
  - broker_factory.py: Settings を解釈して適切なブローカークライアントを返す
- data/
  - calendar_management.py: 営業日ロジック & カレンダ更新ジョブ
  - news_collector.py: RSS ベースのニュース収集（URL 正規化、SSRF 対策等）
- monitoring/（監視用コード群）

注意事項 / 運用メモ
-----------------
- KABUSYS_ENV:
  - development: ローカル開発向け（Mock ブローカー）
  - paper_trading: ペーパートレード（Mock ブローカー、専用 SQLite に記録）
  - live: 本番（実ブローカー想定）。KABUSYS_ENV=live は注意喚起の警告が出ます。
- PAPER_FILL_MODE（paper_trading 向け）
  - instant / partial / never / reject をサポート。Mock の挙動を制御してテスト可能。
- Kill Switch:
  - 起動時・運用中に kill.flag が検出されると発注ループは停止し、全 active 注文をキャンセルする挙動があります。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（自動クリアされる）。
- データベース:
  - DuckDB は分析用（signals, portfolio_targets, position_entries など）。
  - SQLite は監視・注文永続化用（monitoring.db / paper_trading.db）。
- YAML 検証:
  - PyYAML がインストールされていない場合、validate_config は YAML 内容検証をスキップします（存在チェックは行われます）。

ディレクトリ構成（抜粋）
---------------------
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    data/
      calendar_management.py
      news_collector.py
      jquants_client.py (実装想定)
    execution/
      __init__.py
      broker_api.py
      broker_factory.py
      kabu_client.py
      mock_client.py
      order_record.py
      order_repository.py
      order_manager.py
      execution_engine.py
      reconciler.py
      risk_manager.py
      order_* (その他関連ファイル)
    monitoring/
      monitoring_db.py
      system_monitor.py
    utils/
      logging_setup.py
      process_priority.py
    strategy/ (戦略関連モジュール群、未表示)
    monitoring/ (監視関連モジュール群、未表示)
config/
  system_config.yaml
  data_config.yaml
  strategy_config.yaml
  risk_config.yaml
  execution_config.yaml
  monitoring_config.yaml

（注）上記は抜粋で、リポジトリによっては追加ファイルがあります。config/*.yaml は validate_config でチェック対象になります。

よくあるコマンドまとめ
---------------------
- .env を作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

開発・テスト向けメモ
--------------------
- MockBrokerClient を使えば kabu station を立ち上げずに発注フローの単体テストが可能です。
- settings は環境変数経由なのでユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用し、テスト用に os.environ を直接差し替えると良いです。
- データベース初期化関数（init_orders_db / init_monitoring_db 等）を使ってテスト時にインメモリ SQLite を用いると簡単です。

ライセンス / コントリビュート
----------------------------
（ここにはプロジェクトのライセンスやコントリビュート手順を記載してください）

以上。README に追加したい項目（例: 実行例、設計ドキュメントへのリンク、細かい設定項目一覧など）があれば教えてください。