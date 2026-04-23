README
======

概要
----
KabuSys は日本株自動売買向けの軽量フレームワーク（ライブラリ兼実行コンポーネント）です。  
主に以下を提供します。

- 発注エンジン（ExecutionEngine） — シグナルに基づく Pull 型発注と WebSocket push ドレイン
- ブローカー抽象（BrokerAPIProtocol） — 実ブローカー（kabu station）とモックの切替が可能
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時リコンシリエーション（Reconciler）
- リスクガード（RiskManager） — Gate1/2/3 による安全制御
- 監視ループ（SystemMonitor を使う run_monitoring スクリプト）
- 設定ウィザード (.env 生成) と設定検証ツール

特徴
----
- 明確に分離された層設計（API クライアント層 / 永続化層 / ビジネスロジック層）
- ペーパートレード向け MockBrokerClient を用意し、本番 DB と分離可能
- 発注フローのクラッシュ耐性（OrderSent の二相永続化等）
- 起動時自動リコンシリエーション機構でクラッシュ後の整合性回復を支援
- 設定用 CLI（config_setup）と起動前検証 CLI（validate_config）で安全な運用を支援

セットアップ手順
--------------
1. リポジトリをクローンしてプロジェクトルートへ移動します（.git または pyproject.toml があるパスが自動検出ルートになります）。

2. Python 仮想環境を作成・有効化して依存パッケージをインストールします。
   依存関係は環境により異なりますが、本プロジェクトの機能を使うには少なくとも次が必要です:
   - duckdb
   - httpx
   - websocket-client
   - PyYAML（config/*.yaml の検証に必要）
   - defusedxml
   - （実行環境に応じて他ライブラリ）
   例:
   - pip install -r requirements.txt
   （requirements.txt が無い場合は上記パッケージを個別にインストールしてください）

3. .env の作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
     これによりプロジェクトルートの .env（デフォルト）を生成／更新できます。
   - 既存の .env がある場合はウィザードが読み込み、Enter で既存値を再利用できます。

4. 環境変数の自動ロード
   - Settings モジュールは自動的にプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数
--------------
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

（その他オプション）
- KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL（kabu station の base URL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START（起動時の kill.flag 自動クリア: 0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、デフォルト 60 秒）

使い方
------

1) 設定ウィザード
- 実行:
  - python -m kabusys.config_setup
- 概要:
  - .env を対話式に作成／更新します。
  - シークレット項目はマスク表示されます。
  - 保存確認後に .env を書き込みます。

2) 起動前設定検証
- 実行:
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict
- 概要:
  - 必須環境変数の存在、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パス親ディレクトリの有無、config/*.yaml の存在と YAML パースを検証します（PyYAML が無い場合は YAML 検証はスキップして警告）。
  - エラーがあれば exit code 1。

3) 実行（ExecutionEngine）
- 実行:
  - python -m kabusys.run_execution
- 概要:
  - Settings を読み、DB に接続（paper_trading の場合は paper_trading 専用 SQLite に接続して本番 DB と分離）。
  - BrokerClientFactory を通じてブローカークライアントを生成（開発 / ペーパー → MockBrokerClient）。
  - ExecutionEngine を起動しシグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を行います。
  - stop は data/stop_requested.flag を作成することで通知できます（同様に kill.flag による kill_switch 制御あり）。

4) 監視ループ起動
- 実行:
  - python -m kabusys.run_monitoring
- 概要:
  - SystemMonitor のポーリングループを起動します（デフォルト 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
  - 監視 DB（SQLite）と DuckDB に接続し、監視情報を記録します。
  - 停止は data/stop_requested.flag の作成で検知します。

運用に関する重要事項
--------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダーにもその旨を記載）。
- KABUSYS_ENV=live を設定する場合は LINE 通知や kill flag 周りなどの設定を慎重に確認してください（validate_config は live 環境でのいくつかの警告を通知します）。
- kill.flag の存在は起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 を設定した場合のみ起動時に自動クリアします（本番では 0 推奨）。
- paper_trading モードは MockBrokerClient を使用し、発注は実際のブローカーには到達しません（テスト・検証用途）。

主要コンポーネント（概要）
-----------------------
- kabusys.config
  - Settings クラス: 環境変数からの設定取得、.env 自動ロード機能、必須チェック等
  - 自動ロード順序: OS 環境 > .env.local > .env（プロジェクトルートが自動検出できる場合）

- kabusys.config_setup
  - .env の対話式生成ツール

- kabusys.validate_config
  - 起動前に環境設定の不備を検出する CLI

- kabusys.execution
  - broker_api: BrokerAPIProtocol、データモデル、ファクトリ（Mock / KabuStation）
  - kabu_client: kabu station REST + WebSocket クライアント（httpx / websocket-client）
  - mock_client: テスト用 MockBrokerClient（fill_mode により振る舞いを変更可能）
  - order_record / order_repository / order_manager: 注文状態と永続化、送信フロー管理
  - execution_engine: シグナル処理、push ドレイン、kill_switch、PID 管理、リコンシリエーション呼び出し
  - reconciler: 起動時に OrderSent の注文を突合して状態回復、ポジション差分検出
  - risk_manager: Gate1/2/3 の実装（余力・重複・ポジション上限 / レート制限・サーキット / ドローダウン）

- kabusys.data
  - calendar_management: JPX カレンダー管理（DuckDB ベース）と関連ユーティリティ
  - news_collector: RSS 収集・前処理機能（セキュリティ対策あり）

- kabusys.monitoring
  - 監視向け DB 初期化や SystemMonitor（run_monitoring から起動）

実行時ファイル・パス
-------------------
- デフォルト DB / ファイル場所（プロジェクトルート基準）
  - DuckDB: data/kabusys.duckdb（DUCKDB_PATH）
  - 監視 SQLite: data/monitoring.db（SQLITE_PATH）
  - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - PID ファイル: data/execution.pid（PID_FILE_PATH）
  - kill flag: data/kill.flag（KILL_FLAG_PATH）
  - stop フラグ: data/stop_requested.flag（run_* が監視）

ディレクトリ構成
----------------
（src/kabusys 以下の主なファイル/モジュール）
- src/kabusys/
  - __init__.py                  — パッケージ定義（バージョン等）
  - config.py                    — Settings（環境変数読み込み、.env パーサ）
  - config_setup.py              — .env 対話型ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine を起動するスクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py              — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - kabu_client.py             — kabu station REST / WebSocket 実装
    - mock_client.py             — MockBrokerClient（テスト用）
    - broker_factory.py          — Settings に基づくクライアント生成
    - order_record.py            — 注文状態モデルと遷移ロジック
    - order_repository.py        — SQLite 永続化
    - order_manager.py           — 発注フロー管理（create/send/sync/cancel）
    - execution_engine.py        — 発注エンジン本体（シグナル処理／push ドレイン）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — Gate1/2/3 リスクガード
    - ...（他の execution 関連）
  - data/
    - calendar_management.py     — マーケットカレンダー管理
    - news_collector.py          — RSS 収集
    - ...（他の data 関連）
  - monitoring/
    - monitoring_db.py           — 監視 DB 初期化 / ログ保存（run_monitoring から使用）
  - utils/
    - logging_setup.py           — ロギング設定ユーティリティ
    - process_priority.py        — プロセス優先度設定

補足 / 運用メモ
---------------
- config/*.yaml は一部コンポーネントで使用されます。validate_config はこれらの存在と YAML パースを確認します（PyYAML がインストールされている場合）。
- ExecutionEngine はセッション時間（デフォルト: 8:50-9:10 / 9:10-15:30）に従って動作します。テストでは内部メソッドを直接呼び出して制御可能です。
- OrderManager は二相永続化（OrderSent 前に DB 更新 → broker 呼び出し → broker_order_id 先に永続化 → OrderAccepted 更新）を行い、クラッシュ時の回復を考慮しています。
- Reconciler は起動時に OrderSent の注文をブローカーに照合し、必要なら状態同期やポジション差分ログを出力します。

ライセンス / コントリビュート
-----------------------------
この README はコードベースの説明を目的としています。リポジトリ内の LICENSE ファイルや CONTRIBUTING.md があればそちらを参照してください。

以上。セットアップや実行で不明点があれば、どの部分を詳しく知りたいか教えてください。