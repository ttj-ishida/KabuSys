KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
----
KabuSys はローカル／ペーパートレード環境向けの日本株自動売買フレームワークです。
主要コンポーネントとしてシグナル読み取り→発注を行う ExecutionEngine、システム監視を行う SystemMonitor、設定ウィザード／検証 CLI、ブローカークライアント抽象層などを提供します。設計はクラッシュ耐性（永続化・リコンシリエーション）や安全（3段階のリスクガード、kill switch）を重視しています。

主な機能
--------
- 環境設定ウィザード（.env 作成／更新）: python -m kabusys.config_setup
- 設定検証ツール（.env と config/*.yaml の事前チェック）: python -m kabusys.validate_config
- ExecutionEngine（シグナル読み取り・発注・WebSocket ドレイン・kill switch）
  - 発注フローにおける二相永続化（OrderSent の DB 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）
  - リコンシリエーション：クラッシュ復旧時に OrderSent を突合して同期
  - RiskManager による 3 段階のガード（Gate1 シグナル検査、Gate2 レート制限/CB、Gate3 ドローダウン監視）
- Monitoring（SystemMonitor ポーリングループ）
- ブローカークライアント抽象化
  - MockBrokerClient（テスト/ペーパートレード用、fill_mode 制御）
  - KabuStationClient（kabuステーション REST/WebSocket 実装）
- データ層
  - DuckDB（分析・シグナル/カレンダー）
  - SQLite（監視・orders 永続化）
- ニュース収集、マーケットカレンダー管理などのデータ処理ユーティリティ

動作要件（概略）
----------------
- Python 3.10+（型注釈に Path | None などが使われています）
- ライブラリ（主なもの）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（任意、validate_config の YAML 検証に使用。未インストールでも警告だけ）
- 標準ライブラリ: sqlite3, pathlib, logging など

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動する。
2. 仮想環境を作成して有効化する（推奨）。
3. 依存パッケージをインストールする。最小例:
   - pip install duckdb httpx websocket-client defusedxml pyyaml
   - PyYAML は任意だが config/*.yaml を深く検査したい場合は入れてください。
4. 初期設定ファイル（.env）を作成する:
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 既存の .env を用意する場合はプロジェクトルートに配置（.env と .env.local をサポート）。
   - 自動ロードはデフォルトで有効（OS 環境変数 > .env.local > .env の優先順）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

重要な環境変数（必須／主要）
----------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 任意（よく使うもの／デフォルトあり）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — デフォルト: INFO
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート用（本番での通知に必要）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - PAPER_FILL_MODE — paper_trading 時の mock の fill 動作（instant|partial|never|reject、デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

設定の作成・検証
----------------
- 設定ウィザード（.env を対話式で作成／更新）
  - 実行: python -m kabusys.config_setup
  - 完了すると .env を保存するか確認されます。
- 設定検証
  - 実行: python -m kabusys.validate_config
  - 警告を失敗扱いにする: python -m kabusys.validate_config --strict
  - このツールは必須環境変数の未設定、プレースホルダの検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を行います。

実行方法
--------
- 実行エンジン（本番/ペーパートレード/開発）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。live 環境の live ブローカーは未実装。
    - 起動時に PID ファイルを書き、stop フラグや kill.flag を監視します。
- 監視ループ
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は共通）。
- 停止方法
  - プロセス停止は通常シグナル（Ctrl+C）や、プロジェクトルート/data/stop_requested.flag を作成することで安全に停止させる仕組みになっています（スクリプトはこのファイルの存在を検査してループを終了します）。
  - kill.switch は settings.kill_flag_path（デフォルト data/kill.flag）で管理します。起動時にこのファイルが存在すると起動を拒否するか、自動クリア設定によってはクリアして起動します（KILL_FLAG_CLEAR_ON_START）。

仕様のポイント（設計上の注意）
-----------------------------
- 永続化とリコンシリエーション
  - OrderSent の状態は broker 呼び出し前に DB にコミットされます（クラッシュ時の整合性を確保）。
  - Reconciler が OrderSent をブローカーと照合して状態を復元します。
- RiskManager（3 段階ガード）
  - Gate1: 発注前に余力、重複、ポジション上限などを検査。
  - Gate2: レート制限（トークンバケツ）、サーキットブレーカー。
  - Gate3: 約定後にドローダウン監視、閾値越えで kill_switch 発動。
- MockBrokerClient によりローカル開発・自動テストが容易。fill_mode で挙動（即時全量約定、部分約定、常に pending、常に拒否）を切替可能。
- .env 自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local をロード。
  - OS 環境変数を保護し、.env.local は上書き（override=True）可能。
  - テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

開発者向けメモ
--------------
- YAML 検証: validate_config は PyYAML がインストールされていれば config/*.yaml をパースして検査します。未インストール時は警告にとどまります。
- ブローカーの切り替え:
  - create_broker_api(mock=True, ...) で MockBrokerClient を取得できます。
  - BrokerAPIProtocol によってコードはブローカー実装に依存しないよう設計されています。
- DB 初期化:
  - OrderRepository.init_orders_db 相当の初期化関数（init_orders_db）で orders テーブルを作成できます。
  - Monitoring 用テーブル初期化関数も用意されています（monitoring_db.init_monitoring_db 等）。

ディレクトリ構成（主要ファイル）
------------------------------
ここでは実装済みファイルの主要構成を示します（src/kabusys 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込みと Settings クラス（.env 自動ロード含む）
    - config_setup.py          — .env 対話ウィザード CLI
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py          — BrokerAPIProtocol、データモデル、ファクトリ
      - kabu_client.py         — kabuステーション REST/WebSocket 実装
      - mock_client.py         — MockBrokerClient（テスト用）
      - broker_factory.py      — Settings に基づくブローカーファクトリ
      - order_record.py        — OrderRecord と状態遷移ロジック
      - order_repository.py    — SQLite 永続化層（orders テーブル）
      - order_manager.py       — 発注フロー制御（OrderManager）
      - execution_engine.py    — ExecutionEngine 本体（シグナル処理／push drain 等）
      - reconciler.py          — 起動時のリコンシリエーション
      - risk_manager.py        — 3 段階リスクガード
      - ...（その他補助モジュール）
    - data/
      - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
      - news_collector.py      — RSS ニュース収集
      - jquants_client.py      — （存在する場合）J-Quants API クライアント
    - monitoring/
      - monitoring_db.py      — 監視 DB 初期化 / ログ
      - system_monitor.py     — SystemMonitor 実装
    - utils/
      - logging_setup.py      — ロギング初期化
      - process_priority.py   — プロセス優先度設定
    - config/                  — YAML 設定ファイル置き場（system_config.yaml 等を想定）
    - data/                    — デフォルト DB / flag ファイル保存場所（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/stop_requested.flag, data/kill.flag, data/execution.pid など）

補足（運用・安全）
-----------------
- 本番（KABUSYS_ENV=live）では LINE トークンやユーザー ID を必ず設定しておくこと。validate_config は live 時に未設定だと警告を出します。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険（kill.flag を起動時に自動でクリアしてしまうため）。production では 0 を推奨。
- ExecutionEngine の発注時間帯（signal_send_start/end、market_close）はコード内デフォルトに従います。テスト時は直接メソッドを呼んで検証できます。

ライセンス・貢献
----------------
（ここにライセンスと貢献方法を追記してください。プロジェクトベースのポリシーに合わせて編集してください。）

以上。必要であれば、各 CLI やコンポーネントの詳細な引数説明や設定テンプレート（.env.example / config/*.yaml のサンプル）を追記します。どの部分を深掘りしますか？