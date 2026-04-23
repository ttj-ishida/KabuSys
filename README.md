# KabuSys

日本株自動売買システムの一部コンポーネント群（実行エンジン、モニタリング、環境設定ユーティリティ等）。

このリポジトリは、小規模〜中規模の自動売買プラットフォームを想定したモジュール群を含みます。
主にローカル／ペーパートレードでの試験に適した設計で、発注フロー、注文状態管理、リスクガード、リコンシリエーション、
マーケットカレンダー管理、ニュース収集、監視ループなどの機能を備えます。

バージョン: 0.1.0

---

## 主な機能

- 環境設定ウィザード（.env の対話的生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検査）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（ExecutionEngine）
  - シグナル取得 → Gate1/Gate2（リスク検査）→ ブローカー発注 → Gate3（ドローダウン監視）
  - python -m kabusys.run_execution
  - paper_trading（モックブローカー）と live の環境切替対応（現在 live は未実装の箇所あり）
- 監視ループ（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
- ブローカークライアント実装
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST API 実装）
- 注文状態管理
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite による永続化）
  - OrderManager（外向け API）
- リスク管理（3段階ガード）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン）
- リコンシリエーション（再起動時の注文・ポジション突合）
- データ周り
  - マーケットカレンダー管理（DuckDB / J-Quants 経由の差分更新）
  - ニュース収集（RSS → raw_news / 正規化・SSRF 防止・サイズ制限等）

---

## 必須 / 推奨環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意（よく使われるもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — データ分析用 DuckDB のパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — kabuステーション API のベース URL
- LOG_LEVEL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE — paper_trading の fill 動作（instant | partial | never | reject）

設定は .env / .env.local / OS 環境変数から読み込まれます（優先順: OS > .env.local > .env）。
自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。

---

## セットアップ手順

1. Python（推奨: 3.9+）をインストール。

2. 依存パッケージをインストール（代表例）:
   - httpx
   - websocket-client
   - duckdb
   - pyyaml（config/*.yaml のパース検証に使用、無くても動作する）
   - defusedxml

   例:
   pip install httpx websocket-client duckdb pyyaml defusedxml

   ※ 実際のプロジェクトに requirements.txt がある場合はそちらを使用してください。

3. プロジェクトルートに移動して .env を作成（推奨: ウィザード使用）:
   python -m kabusys.config_setup

   ウィザードは既存の .env を読み込み、対話的に入力して .env を生成します。
   重要: .env は決してリポジトリにコミットしないでください。

4. 設定検証:
   python -m kabusys.validate_config
   警告を FAIL 扱いにしたい場合は --strict を付ける:
   python -m kabusys.validate_config --strict

5. DB 初期化や各種設定（必要に応じて）:
   - 例: 実行前に data ディレクトリを作成しておくと良い（.env のパスに依存）。
   - monitoring の初回起動で monitoring DB の初期化は自動で行われます（init_monitoring_db）。

---

## 使い方（主要 CLI / 起動方法）

- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 専用 SQLite に記録（settings.paper_sqlite_path）。
    - PID ファイルと stop フラグを使用:
      - 停止: プロセスを終了するか、プロジェクトの data/stop_requested.flag を作成すると安全停止処理が走る。
      - 起動時 kill.flag が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合のみクリアして起動可能）。

- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60s）。
  - 監視は本番／検証にかかわらず本番 sqlite_path を使用する設計。

- テスト/開発支援
  - MockBrokerClient を使ってユニット/統合テストを行うことが想定されています。
  - create_broker_api(mock=True, fill_mode=...) でモックを取得可能。

---

## 実行時の停止 / 管理ファイル

- stop_requested.flag
  - run_execution / run_monitoring はループ毎に data/stop_requested.flag の存在を確認します。
  - 停止したい場合はこのファイルを作成してください（プロセスは安全に終了処理を行います）。

- kill.flag / KILL_FLAG_CLEAR_ON_START
  - kill.flag が存在すると ExecutionEngine の起動を拒否（誤起動防止）。
  - KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動でクリアします（本番では 0 を推奨）。

- PID ファイル
  - 実行時に PID ファイルを出力（デフォルト: data/execution.pid）。監視や外部管理に利用。

---

## 注意点 / 補足

- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを推奨。
  - "live" を設定すると警告が多数発生し、LINE 通知設定など本番向けの追加チェックが働きます。
  - 現状 live 用の実際のブローカークライアント実装は一部 NotImplementedError を投げる場所があります（README 作成時点の実装状況に依存します）。

- YAML 設定ファイル（config/*.yaml）は存在をチェックします。PyYAML がない場合、パース検証はスキップされます。
  - 生成スクリプトが用意されている場合: python scripts/generate_config.py（メッセージ参照）

- リコンシリエーション（Reconciler）は再起動時に OrderSent の不確定注文をブローカーと照合し、ポジション差分を検出・ログ出力します。

---

## ディレクトリ構成（抜粋）

リポジトリは src/kabusys 以下にパッケージ化されています。主なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API の Protocol・データモデル・ファクトリ
    - broker_factory.py      — Settings に応じた BrokerClient 生成
    - kabu_client.py         — kabuステーション API クライアント
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 外向け注文 API（OrderState 管理）
    - execution_engine.py    — セッション / 発注ループ 本体
    - reconciler.py          — リコンシリエーション（起動時の復旧）
    - risk_manager.py        — 3段階リスクガード
  - data/
    - calendar_management.py — 市場カレンダー管理（DuckDB / J-Quants）
    - news_collector.py      — RSS ニュース収集
    - (他のデータ関連モジュール)
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化とログ機能（参照コード上で使用）
    - system_monitor.py      — SystemMonitor（run_monitoring から使用）
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

（実際のリポジトリには他にもファイルが含まれることがあります。上は代表的な構成です。）

---

## 開発者向けメモ

- テストは MockBrokerClient を使って実装するとブローカー依存を排除できます。
- OrderRepository の DB スキーマは init_orders_db() によって冪等に作成されます。
- ExecutionEngine のタイミング（シグナル処理開始/終了・マーケットクローズ）は EngineConfig で設定できます（テスト時に短縮するなど）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。配布後でも CWD に依存せず動作するよう設計されています。

---

もし README の内容をプロジェクトの実際のリポジトリ構成や運用ポリシーに合わせて調整したければ、必要な追加情報（例: requirements.txt, サービス起動手順、systemd ユニット例、config/*.yaml のサンプル等）を教えてください。