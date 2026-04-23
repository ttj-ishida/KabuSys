KabuSys — 日本株自動売買システム
================================

このドキュメントはリポジトリの簡易 README です。プロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
--------------
KabuSys は日本株を対象とした自動売買システムの骨組み（コアロジック）です。  
主に以下を提供します。

- 環境設定の対話式ウィザード（.env の生成／更新）
- 起動前の設定検証 CLI（環境変数や config/*.yaml の基本チェック）
- 発注エンジン（ExecutionEngine） — シグナルに基づく発注フロー、WebSocket ドレイン、kill-switch 等
- ブローカークライアント抽象化（Mock / 将来的に KabuStation 実装）
- 注文状態管理（OrderRecord）・永続化（SQLite）・リコンシリエーション
- リスク管理（3段階の Gate）
- 監視プロセス（SystemMonitor 用のポーリングループ）
- データ系ユーティリティ（市場カレンダー管理、ニュース収集など）

主な機能一覧
-------------
- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env を対話式に作成・更新。秘密情報はマスク表示。
- 設定検証（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの存在確認、
    config/*.yaml の存在と（PyYAML があれば）パースチェック、本番環境用ガードなど。
  - --strict を付けると警告も失敗扱い（exit 1）。
- 発注（ExecutionEngine）
  - Signal Queue に基づく発注ループ（8:50〜9:10）と WebSocket push ドレイン（9:10〜15:30）。
  - OrderManager / OrderRepository / Reconciler による状態管理とクラッシュ耐性。
  - 環境による Broker 選択：development / paper_trading → MockBrokerClient、live →（将来的に）実ブローカ。
- MockBrokerClient
  - テスト用に発注挙動を模擬（instant / partial / never / reject の fill_mode）。
- RiskManager（3段階）
  - Gate1: シグナル単位（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: 約定後メトリクス（ドローダウン監視）
- 監視プロセス
  - run_monitoring.py で SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔変更可。
- データユーティリティ
  - マーケットカレンダー管理（DuckDB を利用）
  - RSS ニュース収集（安全対策: defusedxml, SSRF チェック, URL 正規化等）

セットアップ手順
----------------
以下はローカルで動かすための一般的な手順例です。requirements.txt がある場合はそちらを使用してください。

1. Python 環境を用意
   - Python 3.9+ を推奨
   - 仮想環境を作る: python -m venv .venv && source .venv/bin/activate

2. 必要なパッケージをインストール
   - 最低限推奨パッケージ（例）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（任意：validate_config が YAML を検証する場合に使用）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - ウィザードは .env（デフォルト）を生成・上書きします。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 任意（代表例）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - KABU_API_BASE_URL（kabuステーション 接続先）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知用）

4. 起動前に設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
   - 注意: PyYAML 未導入の場合、config/*.yaml の内容検証はスキップされます（警告出力）。

5. 実行（監視 / 実行エンジン）
   - 実行エンジン（ExecutionEngine）を起動:
     - python -m kabusys.run_execution
     - KABUSYS_ENV が paper_trading の場合は MockBrokerClient が使われ、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録されます。
   - 監視ループを起動:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可（デフォルト 60 秒）。

注意事項・運用メモ
-----------------
- 自動 .env 読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env → .env.local の順で（OS 環境変数を保護しつつ）読み込みます。
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
  - .env のパースは export プレフィックス、引用符、行内コメント、エスケープをサポートします。
- データベース
  - デフォルトのパス: data/kabusys.duckdb（DuckDB）、data/monitoring.db（SQLite）。
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（設計上の注意）。
- 本番（live）注意
  - KABUSYS_ENV=live を設定すると validate_config で警告が出ます。LINE 通知設定や Kill Switch 設定など本番用ガードを必ず確認してください。
  - BrokerFactory は現在 live の実ブローカークライアント実装を投げる（NotImplementedError）ため、本番運用は未実装箇所に注意してください。
- kill.flag / stop_requested.flag / PID
  - 起動時や運用上、停止フラグ（data/kill.flag など）を用いた安全停止や起動拒否の仕組みがあります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動クリアします（本番では推奨されません）。
- YAML 設定ファイル（config/*.yaml）
  - validate_config は config ディレクトリ内の主要な YAML ファイルが存在し、PyYAML があればパース可能かをチェックします。
  - 指摘される場合は python scripts/generate_config.py（リポジトリ内にスクリプトがある想定）でテンプレートを生成してください。

使い方（主なコマンド）
---------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数で調整例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- パッケージ内部 API（ライブラリ利用例）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

主要ファイル・ディレクトリ構成
----------------------------
（リポジトリのルートを想定。ソースは src/kabusys 以下に配置されています。）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py                — .env 対話式ウィザード CLI
  - validate_config.py             — 起動前の設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py                — Broker 抽象（Protocol）・データモデル・例外・ファクトリ
    - broker_factory.py            — Settings に基づく Broker インスタンス生成
    - kabu_client.py               — kabu station 実装（httpx / websocket）
    - mock_client.py               — MockBrokerClient（テスト用）
    - order_record.py              — 注文状態と遷移ロジック（純粋モデル）
    - order_repository.py          — SQLite 永続化層（orders テーブル）
    - order_manager.py             — 外向きの発注 API（Send/Sync/Cancel）
    - execution_engine.py          — 発注セッション全体の制御
    - reconciler.py                — 起動時リコンシリエーション
    - risk_manager.py              — 3段階リスクガード
  - data/
    - calendar_management.py       — マーケットカレンダー管理（DuckDB）
    - news_collector.py            — RSS ニュース収集（安全対策付き）
    - jquants_client.py            — （参照される想定の J-Quants クライアント）
  - monitoring/
    - monitoring_db.py             — 監視用 DB 初期化・ログ機能（SQLite）
    - system_monitor.py            — 実際の監視ロジック（参照）
  - utils/
    - logging_setup.py             — ロギング設定ユーティリティ
    - process_priority.py          — プロセス優先度設定ユーティリティ
  - その他:
    - config/                      — YAML 設定ファイル（system_config.yaml 等）
    - data/                        — データ用ディレクトリ（SQLite/duckdb 等のデフォルトパス）
    - .env, .env.local             — 実行時の環境変数ファイル（プロジェクトルートに配置）

補足（設計上のポイント）
-----------------------
- クラッシュ安全性
  - OrderManager.send_order は「OrderSent を DB に永続化 → ブローカ呼び出し → broker_order_id を保存 → OrderAccepted 更新」という二相的永続化を設計しており、クラッシュ後に Reconciler が復旧できるようになっています。
- リスク設計
  - レート制限はトークンバケツ方式、サーキットブレーカーはエラー発生ウィンドウで OPEN/HALF_OPEN を管理、ドローダウンによる kill-switch など複数レイヤで安全を担保します。
- テスト容易性
  - MockBrokerClient により外部サービスなしで発注フローの単体・統合テストが可能です。
- セキュリティ
  - RSS 処理では defusedxml を使用し、URL 正規化と SSRF 対策を実装しています。

最後に
------
この README はコードベースから抽出した概要ドキュメントです。実運用に移す際は次を確認してください。

- 実ブローカ（kabu station）クライアントの検証と実装（live モード）
- 運用監視・ログの永続化・アラート経路（LINE など）
- データベースバックアップ・マイグレーション戦略
- セキュリティ（API トークンの保管、アクセス制御）

必要であれば README を拡張して「デプロイ手順」「運用手順」「API リファレンス」「設定例ファイル(.env.example)」等も作成します。どの情報を追加したいか教えてください。