KabuSys
======

概要
----
KabuSys は日本株向けの自動売買システムの骨組みを提供する Python コードベースです。  
主要な責務は以下の通りです。

- 環境設定の対話式ウィザード（.env の生成／更新）
- 起動前の設定検証（必須環境変数や設定ファイルの有無チェック）
- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の永続化と状態管理（SQLite）
- ブローカークライアント抽象化（実運用用の KabuStationClient / テスト用の MockBrokerClient）
- 監視ループ（SystemMonitor）によるプロセス監視とメトリクス収集
- データ関連ユーティリティ（マーケットカレンダー管理、ニュース収集など）

目標は「本番運用に耐える自動化ロジック」と「テストしやすい構成」を両立することです。

主な機能一覧
------------
- 環境設定ウィザード
  - python -m kabusys.config_setup で .env を対話的に生成／更新できます。
- 設定検証 CLI
  - python -m kabusys.validate_config で .env や config/*.yaml の存在／整合性をチェック。--strict を指定すると警告も失敗扱い。
- ExecutionEngine（発注エンジン）
  - シグナルを読み込み Gate1〜Gate3 のリスクガードを通して発注を行う。
  - WebSocket（kabu push）対応で push ドレイン処理を行う。
  - ペーパートレード（MockBrokerClient）/ 本番（KabuStationClient）に対応（現在本番クライアントは未実装箇所あり）。
- ブローカー抽象化
  - BrokerAPIProtocol により実装を差し替え可能（mock=true で MockBrokerClient を使用）。
- 発注永続化（SQLite）
  - orders テーブルへ注文を保存。コンカレンシー対策や再起動時のリコンサイル用 API を提供。
- リコンシリエーション（再起動時の注文同期）
  - OrderSent 状態の注文をブローカーと突合して回復処理を行う。
- 監視ループ（run_monitoring）
  - 別プロセスで稼働し監視用 DB にメトリクス等を書き込む。
- データユーティリティ
  - マーケットカレンダー管理（DuckDB を想定）
  - RSS ニュース収集（defusedxml、URL 正規化、SSRF 対策などを考慮）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo_root>

2. Python 仮想環境を作成・有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要ライブラリをインストール
   - 主要な依存（本プロジェクトのコードから想定）:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml  (validate_config の YAML 検証用; インストールされていないとスキップされます)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記の必須環境変数を参照）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）。

6. データディレクトリの用意
   - デフォルトの DB パスは data/ 以下を想定しています。必要に応じてディレクトリ作成:
     - mkdir -p data

7. 実行
   - 実行方法は次の「使い方」を参照してください。

必須／推奨環境変数
-----------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 任意（ただし多くは設定しておくことを推奨）
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（本番環境では必須推奨）
  - LINE_USER_ID — LINE 通知先ユーザー ID（本番環境では必須推奨）
  - その他（PAPER_FILL_MODE 等、Settings クラスに記載のプロパティ参照）

- 注意
  - KABUSYS_ENV=live を使う場合は設定内容（特に通知周りや kill flag の運用）を慎重に確認してください。

使い方（主要コマンド）
--------------------
- 環境設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
  - オプション: --env-file で保存先を指定可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意: 実行前に .env の設定・DB の場所・kill.flag の運用を確認してください
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient が使われ、paper_trading 用 SQLite（data/paper_trading.db）が使用されます。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）

停止・制御
---------
- 停止フラグ
  - data/stop_requested.flag ファイルが存在すると run_execution / run_monitoring のループが検出して終了します（プロセスを安全に停止するための外部制御）。
- Kill Switch / kill.flag
  - 実行中に settings.kill_flag_path（デフォルト: data/kill.flag）が存在すると ExecutionEngine は kill_switch を発動し全 active 注文をキャンセルします。
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に既存の kill.flag を自動でクリアして起動します（本番では 0 推奨）。

自動初期化
----------
- 起動時に必要な監視用テーブルなどは init_monitoring_db / init_orders_db といった関数で作成されるようになっています（起動スクリプトが適宜呼び出します）。通常は手動で DB スキーマを用意する必要はありませんが、権限やパスに注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下はプロジェクトの主要モジュールと役割です（src/kabusys 以下を抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py — 実行周りの公開 API
    - broker_api.py — BrokerAPIProtocol とデータモデル・例外・ファクトリ
    - kabu_client.py — kabu station REST API 実装（HTTP + WebSocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — 設定に応じた Broker クライアント生成
    - order_record.py — Order 状態遷移モデル（純粋ロジック）
    - order_repository.py — SQLite を使った永続化
    - order_manager.py — 発注フロー管理（create/send/sync/cancel）
    - execution_engine.py — セッション制御・シグナル処理・push ドレイン
    - reconciler.py — 再起動時のリコンシリエーション
    - risk_manager.py — Gate1/2/3 によるリスクガード
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ
    - system_monitor.py — システム監視ロジック（別プロセス）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（正規化、SSRF 対策等）
    - jquants_client.py — （J-Quants API クライアント、実装がある想定）
  - utils/
    - logging_setup.py — ログ初期化
    - process_priority.py — プロセス優先度操作ユーティリティ

補足（設計上のポイント）
---------------------
- 発注フローはクラッシュ安全性を意識して設計されています（OrderSent を永続化してから外部 API を呼ぶ、broker_order_id を先に書き込む等）。
- ExecutionEngine は時間帯（シグナル処理時間、マーケット時間）に基づくセッション制御を行います。
- RiskManager は 3 段階（signal / execution / metrics）でガードを実施し、サーキットブレーカーやレート制限を内包します。
- データ処理（calendar, news）は DuckDB を想定しており、DB 集計を高速に行える構成です。
- テスト容易性のため MockBrokerClient が用意され、本番ブローカーとの切り替えは create_broker_api() で行います。

よくある質問
------------
Q. .env をコミットしても良いですか？  
A. 絶対にコミットしないでください。.env 内には API トークンやパスワードが含まれます。config_setup でもヘッダに「.env を絶対に Git にコミットしないこと」と明記しています。

Q. KABUSYS_ENV を live にしても本番発注できますか？  
A. 現状、BrokerClientFactory は paper_trading / development での mock クライアントを返す設計で、live 用クライアントは部分的に未実装な箇所があります。live を使う際はコードの該当部分（broker_factory / kabu_client）を十分にレビューしてください。

Q. 監視や停止はどうすれば良いですか？  
A. data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して安全に終了します。kill.flag は発注側で kill_switch を発動させるためのフラグです（運用ルールを決めて運用してください）。

ライセンス / 貢献
----------------
- 本 README はコードのコメントと構造に基づいて作成しています。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

以上。必要であれば README にインストール用の requirements.txt の例や、より詳細な運用手順（systemd ユニット例、Dockerfile など）を追記できます。どの情報が必要か教えてください。