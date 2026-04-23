# KabuSys

日本株自動売買システムのコアライブラリ（プロトタイプ）。  
このリポジトリは発注エンジン、リスクガード、監視、設定管理、データ収集などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は kabuステーション 等のブローカー API を利用して日本株の自動売買を行うための内部コンポーネント群です。設計上は以下の責務を明確に分離しています。

- 環境変数 / .env 管理とウィザード（config_setup）
- 起動前設定検証ツール（validate_config）
- 実行エンジン（ExecutionEngine）によるシグナル駆動の発注フロー
- ブローカー API 抽象化（実装: MockBrokerClient / KabuStationClient）
- 注文の永続化 (SQLite) と状態遷移ロジック
- リコンシリエーション（起動時の自動復旧）
- 監視ループ（SystemMonitor 用スクリプト）
- データユーティリティ（マーケットカレンダー、RSS ニュース収集 等）

本リポジトリはテスト・開発用途を念頭に置いた設計（paper_trading / development 環境での MockBroker 使用）になっています。`KABUSYS_ENV=live` の場合は本番運用を意識した追加チェックがありますが、Live ブローカークライアントは一部実装未完です。

---

## 主な機能一覧

- .env ウィザード（対話式）による初期設定生成: python -m kabusys.config_setup
- .env / config/*.yaml の起動前検証ツール: python -m kabusys.validate_config [--strict]
- 実行エンジン起動スクリプト（発注処理）: python -m kabusys.run_execution
  - Signal Pull 型の発注ループ（シグナル処理 + push ドレイン）
  - RiskManager による Gate1/2/3 の三段階リスクチェック
  - OrderManager / OrderRepository による堅牢な注文送信フロー（クラッシュ安全性）
- 監視スクリプト（system monitoring）: python -m kabusys.run_monitoring
- ブローカークライアント抽象化:
  - MockBrokerClient（テスト用、fill_mode サポート）
  - KabuStationClient（kabuステーション REST API 実装）
- データユーティリティ:
  - マーケットカレンダー（DuckDB 連携）: kabusys.data.calendar_management
  - RSS ニュース収集（XML パースに defusedxml を利用）: kabusys.data.news_collector

---

## セットアップ手順（開発環境向け）

1. Python 環境を用意する（推奨: 3.9+）
   - 仮想環境の作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする
   - 必要なパッケージ例（実際の requirements ファイルはリポジトリに含まれていないため参考）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (任意だが config/*.yaml の検証に使用)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成して必要な環境変数を設定する。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も致命扱いにしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルトで data/ 以下に DB や PID / フラグファイルが作られます。必要に応じて .env でパスを上書きしてください。

注意:
- 自動で .env を読み込む仕組みがあり、OS 環境変数 > .env.local > .env の優先度で読み込みます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数

必須 (起動前に設定すること)
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

オプション（主なもの）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用（任意）
- PAPER_FILL_MODE — paper_trading 時の MockBroker の fill 動作（instant/partial/never/reject）

詳細は config_setup のウィザードと kabusys.config.Settings のプロパティを参照してください。

---

## 使い方

1. .env を作る（ウィザード推奨）
   - python -m kabusys.config_setup

2. 設定チェック
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って修正します。

3. 監視ループを起動（ローカル監視、環境に依らず本番 sqlite_path を使用）
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60秒）。
   - 停止は data/stop_requested.flag を作成すると検知して終了します。

4. 実行エンジンを起動（発注）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite に記録します。
   - KABUSYS_ENV=live の場合は本番を想定します（注意: Live クライアントは制約あり）。

5. 開発時のモック使用
   - create_broker_api(mock=True, fill_mode="instant") などでテスト可能。
   - ExecutionEngine / OrderManager は BrokerAPIProtocol に依存しているため簡単に差し替え可能です。

運用に関する注意点:
- 起動時に data/kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合のみ自動クリアして起動）。
- stop フラグは data/stop_requested.flag（監視・実行スクリプト）で検知します。
- 本番環境（KABUSYS_ENV=live）の設定は慎重に扱ってください。validate_config は live の場合に追加の警告を出します。

---

## ディレクトリ構成（主要ファイル）

リポジトリは Python パッケージ `kabusys` を src 以下に持ちます。主要なファイルを抜粋します。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン等
  - config.py — 環境変数/.env 読み込み、Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — 監視（SystemMonitor）起動スクリプト
  - execution/
    - broker_api.py — ブローカー API の Protocol / データモデル / ファクトリ
    - kabu_client.py — kabuステーション REST クライアント実装
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py — SQLite を使った永続化層
    - order_manager.py — 外向けの注文 API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（セッション管理、signal/drain 等）
    - reconciler.py — 再起動時のリコンシリエーション（OrderSent の照合等）
    - risk_manager.py — Gate1/2/3 によるリスク統制
    - ...（その他関連モジュール）
  - data/
    - calendar_management.py — マーケットカレンダーユーティリティ（DuckDB）
    - news_collector.py — RSS ニュース収集（defusedxml 等安全対策実装）
    - jquants_client.py — J-Quants API 連携（参照あり）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite の初期化・ログ機能（参照される）
    - system_monitor.py — システム監視実装（参照される）
  - utils/
    - logging_setup.py — ロギング初期化
    - process_priority.py — プロセス優先度調整ユーティリティ

（注）一部ファイル・機能の実装はここでは抜粋・省略されています。詳細は各モジュールの docstring を参照してください。

---

## 開発者向けメモ

- 設計指針:
  - ビジネスロジック（OrderRecord 等）は DB に依存しない純粋関数/クラスとして実装。
  - 永続化は OrderRepository に集約し、SQL スキーマは init_orders_db() で冪等に初期化。
  - 発注フローはクラッシュ安全性を考慮（OrderSent の二相永続化、broker_order_id の先コミット等）。
  - リスクガードは複数段階（Signal / Execution / Metrics）で実装。
- テスト:
  - MockBrokerClient を利用すれば外部 API を必要とせずユニットテスト可能。
  - .env 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` はテストで便利。

---

## ライセンス / 注意事項

この README はコードベースの説明を目的とします。実際の稼働・金銭を伴う取引に使用する場合は十分なレビュー・監査を行ってください。特に本番環境での設定 (KABUSYS_ENV=live) は細心の注意が必要です。

---

何か追加したい内容（例: インストール用 requirements.txt の推奨内容、個別モジュールの詳細ドキュメントなど）があれば教えてください。README をそれに合わせて拡張します。