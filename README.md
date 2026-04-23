# KabuSys

KabuSys は日本株の自動売買を想定したシステムのコアコンポーネント群です。  
このリポジトリには、設定管理・検証、発注エンジン、ブローカー抽象、リスク制御、マーケットカレンダー、ニュース収集、監視ループなどの主要ロジックが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- 目的: kabuステーションや外部 API（J-Quants）と連携して自動売買を行うための基盤ライブラリ。
- 設計方針:
  - ビジネスロジックと永続化を分離（OrderRecord は DB を触らず、OrderRepository が SQLite を扱う等）。
  - 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境切替で扱う。
  - 安全機能（kill switch、3段階のリスクガード、リコンシリエーション）を提供。

---

## 主な機能一覧

- 環境設定ウィザード（.env を対話的に作成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine（シグナルに基づく発注エンジン）
  - 発注フロー、リスクチェック（Gate1/2/3）、WebSocket push ドレイン、kill switch
- Broker クライアント層
  - MockBrokerClient（テスト／ペーパートレード用）
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
  - 共通 Protocol とファクトリ create_broker_api()
- 注文永続化（SQLite）
  - OrderRepository, init_orders_db
- リコンシリエーション（再起動時の自動復旧）
  - Reconciler
- リスク管理（Rate-limit / Circuit-breaker / ドローダウン / ポジション上限 等）
  - RiskManager, RiskConfig
- Data モジュール
  - カレンダー管理（JPX カレンダーの取得・営業日判定）
  - ニュース収集（RSS の収集・前処理・保存ロジック）
- 監視ループ（SystemMonitor のポーリング: run_monitoring）
- ユーティリティ（ログ設定、プロセス優先度等 — utils 以下に配置）

注: KABUSYS_ENV=live の Live broker クライアント（本番用 KabuStation を直接使う完全実装）は限定的/未実装箇所があります。ペーパートレードや開発モードでの検証を推奨します。

---

## セットアップ手順

1. Python 仮想環境を作成して有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール  
   - プロジェクトに requirements.txt が無い場合は以下パッケージが主に必要になります:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config YAML の内容検証を行う場合）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

3. プロジェクトルートで .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env は決して Git にコミットしないこと）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

注意:
- 自動で .env をプロジェクトルートから読み込みます（OS 環境変数 > .env.local > .env の順）。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主要なもの）

主に config_setup や validate_config で扱う項目の抜粋:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり／用途別）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — kabu station ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

実行時に使うフラグ・ファイル:
- data/stop_requested.flag — このファイルが存在すると run_execution/run_monitoring が終了します
- PID ファイル: デフォルト data/execution.pid（設定で変更可能）
- KILL_FLAG_PATH（デフォルト data/kill.flag） — kill switch の判定用

---

## 使い方（主要な実行コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit code 1

- 実行（ExecutionEngine） — 発注エンジンを起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します
  - KABUSYS_ENV=live は一部未実装の箇所があります（注意）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60）

- 開発向け: Mock broker を使った単体テスト / 対話的確認
  - ExecutionEngine は Settings を読み、development / paper_trading では MockBrokerClient が生成されます

ログ:
- LOG_LEVEL でログの出力レベルを制御（例: export LOG_LEVEL=DEBUG）

停止・安全:
- kill.flag（デフォルト data/kill.flag）を用いた kill switch があり、発注停止やキャンセルを行います。起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 を設定していない限り起動を拒否します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なモジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API の Protocol / 型 / ファクトリ
    - broker_factory.py      — Settings に基づく Broker クライアント生成
    - kabu_client.py         — kabuステーション 実装（HTTP + WebSocket）
    - mock_client.py         — モックブローカー（テスト用）
    - order_record.py        — 注文状態モデル（状態遷移の純粋ロジック）
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 発注ワークフロー管理（OrderRecord + Repository）
    - execution_engine.py    — ExecutionEngine（シグナル処理 / push ドレイン）
    - reconciler.py          — リコンシリエーション（起動時復旧）
    - risk_manager.py        — RiskManager（3段階ガード）
  - data/
    - calendar_management.py — マーケットカレンダー管理（J-Quants との同期）
    - news_collector.py      — ニュース収集（RSS）
    - (jquants_client.py 等 想定)
  - monitoring/
    - monitoring_db.py       — 監視用 DB 初期化 / ログ記録（参照元あり）
    - system_monitor.py      — システム監視ロジック（参照）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

※ 上記以外にも補助モジュールや追加実装ファイルが含まれる想定です。プロジェクトルートに pyproject.toml や requirements.txt がある場合はそちらを参照ください。

---

## 注意事項 / 運用メモ

- .env は絶対に VCS（Git 等）にコミットしないでください（機密情報を含むため）。
- デフォルト DB ファイルは data/ 下に作成されます。実運用では永続ストレージやバックアップの検討をしてください。
- 本番環境で KABUSYS_ENV=live を使う際は十分な検証と監査ログ、通知経路（LINE など）の設定を必ず行ってください。
- run_execution / run_monitoring は stop flag を監視します。安全に停止するには data/stop_requested.flag を作成するか、プロセスに対して通常の停止処理を行ってください。
- Reconciler はクラッシュ後の一貫性回復を試みますが、手動確認が必要なケースもあります（validate_config やログ出力でアラートを確認してください）。

---

## 貢献 / 開発

- 変更を加える場合はローカルで unit テストや手動検証を十分に行ってください。
- 新しい依存を追加したら requirements または pyproject.toml を更新してください。
- 本番接続（kabu station）を行うコードは入念にレビューを行い、Mock を使った回帰テストを用意することを推奨します。

---

もし README に追記してほしい情報（例: 詳しい環境変数一覧、サンプル .env.example、データベーススキーマの説明、運用フローなど）があれば教えてください。必要に応じて追加で記載します。