KabuSys
======

日本株自動売買システム（KabuSys）の軽量ドキュメントです。本 README はコードベース内の主要機能・セットアップ・運用方法・ディレクトリ構成をまとめたものです。

概要
----
KabuSys は日本株の自動売買向けに設計されたモジュール型のシステムです。  
主に以下を提供します。

- 環境設定の対話式ウィザード（.env の生成/更新）
- 起動前設定の検証ツール（.env と config/*.yaml のチェック）
- 発注エンジン（ExecutionEngine）と注文状態管理（OrderRecord / OrderManager）
- ブローカー API 抽象（実際の kabu station クライアント & モック実装）
- リスクガード（Gate1〜3）とサーキットブレーカー
- 起動時リコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor ベースのポーリング）
- データ系ユーティリティ（マーケットカレンダー、ニュース収集 等）

主な機能一覧
--------------
- 環境管理
  - Settings クラスにより .env / 環境変数から安全に設定を読み込む
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- 設定支援・検証
  - python -m kabusys.config_setup : 対話式ウィザードで .env を作成/更新
  - python -m kabusys.validate_config : 起動前に必須環境・設定ファイル等を検証
    - --strict オプションで警告も失敗扱い（exit 1）
- 実行（発注）関連
  - ExecutionEngine: シグナル読み取り→Gate1/2を通して発注、WebSocket push のドレイン
  - OrderRecord / OrderManager / OrderRepository: 注文状態管理と永続化（SQLite）
  - Broker API 層: 抽象 Protocol と実実装（KabuStationClient）および MockBrokerClient（テスト用）
  - RiskManager: Gate1（シグナル）/ Gate2（実行）/ Gate3（メトリクス）による安全制御
  - Reconciler: 再起動時の OrderSent 照合とポジション差分検出
- 監視関連
  - run_monitoring スクリプト: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可能）
  - 監視用 DB は monitoring 用の SQLite（settings.sqlite_path）
- データ系
  - calendar_management: J-Quants カレンダー取得・営業日判定ロジック
  - news_collector: RSS ベースのニュース収集（SSRF 対策・前処理・冪等性考慮）

セットアップ手順
----------------
前提: Python 3.10 以上を想定（typing の記法等に依存）。実際の production では仮想環境を推奨します。

1. リポジトリをクローン / ソースを入手

2. 依存パッケージをインストール（最低限）
   - 必須パッケージ（例）
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
   - 任意（設定検証で YAML をパースする場合）
     - PyYAML
   例:
     pip install duckdb httpx websocket-client defusedxml PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください）

3. .env の作成
   - 対話式ウィザードで作成するのが簡単:
     python -m kabusys.config_setup
     - オプション: --env-file を指定して別パスに保存可能
   - 手動で作る場合は .env.example を参考に .env を作成（リポジトリに例がある想定）

4. 設定検証
   - .env を作成したら起動前に検証:
     python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（CI 等で有効）

5. 実行用 DB / ファイルパス
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - PID / kill flag 等: data/ ディレクトリ配下
   - 設定は .env の DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等で変更可能
   - 起動時に親ディレクトリが存在しない場合は自動作成されることがあるが、事前に data/ を作成しておくと安心

使い方（主要スクリプト）
-----------------------
- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup
  オプション: --env-file <path>

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

  検出項目:
  - 必須環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD)
  - KABUSYS_ENV の値チェック（development / paper_trading / live）
  - LOG_LEVEL の妥当性
  - DB パスの親ディレクトリ存在チェック
  - config/*.yaml の存在と YAML パース検証（PyYAML がインストールされている場合）

- 実行エンジン（発注）
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient が使われます（fill_mode は PAPER_FILL_MODE）
  - live 用クライアントは Factory 側で未実装（BrokerClientFactory が NotImplementedError を投げます）
  - 停止フラグ: data/stop_requested.flag を作成すると安全に停止シーケンスが始まります
  - PID ファイル: data/execution.pid（デフォルト）に書き出されます

- 監視プロセス
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は KABUSYS_ENV に関係なく "本番" sqlite_path を使用します（監視 DB は分離）

- テスト用モック / API
  - MockBrokerClient により発注の即時約定 / 部分約定 / 保留 / 拒否 等をシミュレート可能
  - create_broker_api(mock=True, fill_mode=...) で生成

設定に関する重要な環境変数
--------------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（主要なもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL（kabu station 用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START（0/1、本番での kill.flag 自動クリア）
- MONITOR_POLL_INTERVAL（監視のポーリング間隔）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にするとライブラリ初期化時の自動 .env 読み込みを無効化

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールとその役割の簡易ツリーです（提供されたコードに基づく）:

- src/kabusys/
  - __init__.py                 (パッケージ情報)
  - config.py                   (Settings, .env 自動ロード, env パーサ)
  - config_setup.py             (.env 対話式ウィザード)
  - validate_config.py          (起動前設定検証 CLI)
  - run_execution.py            (ExecutionEngine 起動スクリプト)
  - run_monitoring.py           (SystemMonitor ポーリング起動スクリプト)
  - execution/                  (発注周りの実装)
    - broker_api.py             (API 抽象, データモデル, ファクトリ)
    - kabu_client.py            (kabu station REST クライアント)
    - mock_client.py            (テスト用モッククライアント)
    - broker_factory.py         (Settings に基づくクライアント生成)
    - order_record.py           (OrderState / OrderRecord の純粋ビジネスロジック)
    - order_repository.py       (SQLite 永続化)
    - order_manager.py          (発注ワークフロー: create/send/sync/cancel)
    - execution_engine.py       (ExecutionEngine: シグナル処理 + push ドレイン)
    - reconciler.py             (起動時リコンシリエーション)
    - risk_manager.py           (Gate1/2/3 リスクガード)
    - ... (他の関連モジュール)
  - data/
    - calendar_management.py    (マーケットカレンダー管理)
    - news_collector.py         (RSS ニュース収集)
    - jquants_client.py         (J-Quants API クライアント等) — 参照あり
  - monitoring/
    - monitoring_db.py          (監視 DB 初期化・書き込み)
    - system_monitor.py         (SystemMonitor 実体) — 参照あり
  - utils/
    - logging_setup.py          (ログ設定ユーティリティ)
    - process_priority.py       (プロセス優先度設定ユーティリティ)
  - その他の補助モジュール...

補足事項・運用上の注意
---------------------
- live モード（KABUSYS_ENV=live）は本番発注を行います。設定ミスやキーの漏洩による誤発注の危険があるため、validate_config の警告・エラーを十分確認してください。
- .env は機微なシークレット（API トークン・パスワード）を含みます。絶対にリポジトリへコミットしないでください。
- run_execution/run_monitoring は停止用フラグ（data/stop_requested.flag）や kill.flag（KILL_FLAG_PATH）を使ってプロセス制御を行います。運用手順に合わせて利用してください。
- DB スキーマの初期化は各コンポーネントの init_* 関数で行われることが想定されています（例: init_monitoring_db）。手動で初期化が必要な場合は該当モジュールの init 関数を呼び出してください。
- KabuStationClient を使用する場合、ローカル PC 上で kabuステーション® アプリが稼働している必要があります（本実装はその REST と WebSocket を利用）。

参考コマンドまとめ
-------------------
- 対話式 .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 発注エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 自動 .env ロードを無効化（テスト時など）:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ライセンス・貢献
----------------
本 README はコードからのリバースドキュメントです。実際のライセンス・コントリビューションの手順はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

---
不明点や README に追記してほしい箇所（example .env のテンプレート、より細かい DB 初期化手順、CI 用の validate 使い方 など）があれば教えてください。必要に応じて README を拡張します。