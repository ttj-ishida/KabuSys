# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群です。  
このリポジトリは発注フロー（ExecutionEngine）、モニタリング、設定管理、データ処理ユーティリティなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした軽量な自動売買フレームワークです。

- kabuステーション（ローカル REST / WebSocket）またはモックブローカーを用いた発注処理
- 発注の状態管理（OrderRecord / OrderRepository / OrderManager）
- 起動時のリコンシリエーション（Reconciler）
- 3 段階のリスクガード（Gate 1〜3）を備えた RiskManager
- 監視（SystemMonitor）を行う別プロセススクリプト
- .env を使った設定ウィザードと起動前検証ツール

設計方針として、ビジネスロジックと永続化・API 呼び出しを明確に分離しています（例: OrderRecord は DB を参照しない純粋ロジック）。

---

## 主な機能一覧

- 設定管理
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 発注エンジン
  - Signal Queue ベースの ExecutionEngine（シグナル処理 / push-drain）
  - Order の状態遷移管理（OrderRecord）
  - 永続化: SQLite を利用する OrderRepository
  - ブローカーファクトリ: 実ブローカー（KabuStationClient）または MockBrokerClient を切替
  - Reconciler による起動時の自動同期
- リスク管理
  - Gate1: シグナル単位の余力・重複・ポジション上限チェック
  - Gate2: レート制限（トークンバケツ）とサーキットブレーカー
  - Gate3: ドローダウン監視（kill switch 発動）
- モニタリング
  - run_monitoring.py による定期ポーリングと監視 DB への記録
- データユーティリティ
  - DuckDB を用いたマーケットカレンダー管理（next_trading_day 等）
  - RSS ニュース収集（defusedxml を使った安全なパース処理）

---

## 必要な環境・依存

- Python 3.10+
- 標準ライブラリ: sqlite3, threading, logging, datetime, pathlib, etc.
- 推奨 / オプションの外部パッケージ:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml の検証に任意）
  - defusedxml（ニュース収集）
- OS 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

インストール例（最小）:
pip install duckdb httpx websocket-client defusedxml pyyaml

requirements.txt がある場合はそちらを利用してください（本サンプルには同梱されていません）。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトルートは .git または pyproject.toml により自動検出されます。

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml

4. .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（プロジェクトルートに配置）
     - 必須キー（例）
       - JQUANTS_REFRESH_TOKEN=your_token_here
       - KABU_API_PASSWORD=your_password_here
     - 参考テンプレートは config_setup が生成します（ウィザード実行後に .env が作成されます）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

6. DB 初期化
   - run_execution や run_monitoring の起動時に必要なテーブルを作成する処理が組み込まれています（例: init_monitoring_db, init_orders_db）。ただし初回に手動でスクリプトを用意する場合は該当関数を呼んでください。

注意:
- 自動で .env を読み込む場合、OS 環境変数 > .env.local > .env の優先順で適用されます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

基本的なコマンドはモジュールとして実行します。

- 環境設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して出力先を変更可能

- 起動前設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告もエラー扱いで exit(1)

- 実行エンジン起動（発注プロセス）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid、停止フラグ file により制御（data/stop_requested.flag）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）

動作モード（KABUSYS_ENV）:
- development: ローカル開発用（MockBrokerClient を利用、発注は発生しない想定）
- paper_trading: ペーパートレード（MockBrokerClient）。paper_trading 用の SQLite DB に記録され、本番 DB と分離される。
- live: 本番（注意: 本サンプルでは Live broker client は未実装の箇所あり）

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) - デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 時の代替 SQLite)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用、任意）
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時の kill.flag 自動クリア（開発用）

kill.flag の取り扱い:
- 実行エンジンは settings.kill_flag_path（デフォルト data/kill.flag）を見て起動中に安全停止や起動拒否を行います。
- KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に既存の kill.flag を自動で削除します（本番では 0 を推奨）。

---

## ディレクトリ構成

以下は主要ファイルと簡単な説明です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - .env の自動ロード、Settings クラス（環境変数の取得／検証）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI（env / config/*.yaml / パス存在チェック等）
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（実行プロセス）
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト（監視プロセス）
  - execution/
    - __init__.py
    - broker_api.py
      - BrokerAPIProtocol、データモデル、例外、ファクトリ（create_broker_api）
    - broker_factory.py
      - Settings に基づく Broker クライアント生成
    - kabu_client.py
      - kabu station REST / WebSocket クライアント実装（httpx, websocket-client）
    - mock_client.py
      - MockBrokerClient（テスト / paper_trading 用）
    - order_record.py
      - 注文状態モデルと状態遷移ロジック
    - order_repository.py
      - SQLite を使った永続化レイヤ（orders テーブル定義・CRUD）
    - order_manager.py
      - 発注ワークフロー（create/send/sync/cancel）の高レベル API
    - execution_engine.py
      - セッション制御（シグナル処理、push ドレイン、WS スレッド等）
    - reconciler.py
      - 再起動時のリコンシリエーション（OrderSent 照合、ポジション差分）
    - risk_manager.py
      - Gate1〜3 を実現するリスク統制
  - data/
    - calendar_management.py
      - JPX 営業日ロジック（is_trading_day / next_trading_day / calendar_update_job）
    - news_collector.py
      - RSS 収集・前処理ロジック（defusedxml を使用）
    - (jquants_client など外部 API 連携用モジュールが想定される)
  - monitoring/
    - monitoring_db.py (使用されているが今回の抜粋では省略)
    - system_monitor.py (使用されているが今回の抜粋では省略)
  - utils/
    - logging_setup.py (ロギング設定)
    - process_priority.py (プロセス優先度制御)

補足:
- 一部のファイル（monitoring_db, system_monitor, logging_setup など）は run_monitoring/run_execution からインポートされ、起動フロー内で DB 初期化やログ設定に使われます。
- config/*.yaml（system_config.yaml など）が存在する場合は validate_config によりパース検証されます。PyYAML がインストールされていない場合は検証がスキップされ、警告が出ます。

---

## よくある操作例

- .env を作って起動前検証する:
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config

- 開発用に ExecutionEngine をローカルで動かす（Mock ブローカー利用）:
  - KABUSYS_ENV=development python -m kabusys.run_execution

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

---

## 注意事項 / 運用メモ

- .env は機密情報を含むため絶対に Git リポジトリにコミットしないでください。
- 本番動作（KABUSYS_ENV=live）は慎重に設定を確認してください。validate_config は live 時に追加のチェック（LINE 通知設定など）を行います。
- データベースファイル（DuckDB / SQLite）のパスは環境変数で変更できます。親ディレクトリが存在しない場合は起動時に自動作成される場合がありますが、ディレクトリ権限などを事前に確認してください。
- Reconciler は起動時に OrderSent 状態の不確定な注文をブローカーと照合して自動修復を試みます。再起動やクラッシュ後はリコンシリエーションが重要です。

---

## 連絡先 / さらに読む

- 各モジュールの詳細は src/kabusys 以下のドキュメント文字列（docstring）を参照してください。  
- config_setup.py と validate_config.py は起動前の設定整備に便利です。まずはこれらを実行してセットアップ状態を確認してください。

もしこの README に追加してほしい項目（例: Dockerfile、CI 設定、より詳しい schema / SQL 初期化手順など）があれば教えてください。