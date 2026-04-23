KabuSys
======

日本株向けの自動売買システム（プロジェクト骨組み）。  
本リポジトリは発注エンジン、リスクガード、モニタリング、設定管理などを含むモジュール群を提供します。テストやローカル開発向けのモックブローカー（MockBrokerClient）を備え、本番（kabuステーション）連携を想定した設計になっています。

主な目的
- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の永続化・状態遷移管理（OrderRecord / OrderRepository）
- 再起動時のリコンシリエーション（Reconciler）
- 3段階リスクガード（RiskManager）
- モニタリング用ポーリングプロセス（SystemMonitor）
- .env 対話式ウィザードと起動前設定検証ツール

機能一覧
- 環境設定ウィザード: python -m kabusys.config_setup により .env を対話的に生成/更新
- 設定検証 CLI: python -m kabusys.validate_config で .env / config/*.yaml の不足や不正を検出
- ExecutionEngine: シグナルの読み取り → Gate1/2 のリスクチェック → 発注送信 → push ドレイン
- Broker クライアント群:
  - MockBrokerClient（paper_trading / development 用のモック）
  - KabuStationClient（kabuステーション REST API 実装）
  - create_broker_api によるファクトリ
- 注文管理:
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite による永続化）
  - OrderManager（作成・送信・同期・キャンセル）
- 再起動時自動復旧（Reconciler）: OrderSent 状態の注文を照合して復旧
- リスク管理（RiskManager）: Gate1（余力/重複/ポジション上限）/ Gate2（レート制限・サーキットブレーカー）/ Gate3（ドローダウン）
- データ処理:
  - マーケットカレンダー管理（DuckDB）
  - ニュース収集プレースホルダ（RSS 収集・正規化等）
- モニタリングプロセス（run_monitoring）: 定期ポーリングでシステム状況を記録

前提・依存（代表的なもの）
- Python 3.9+
- duckdb
- httpx
- websocket-client
- PyYAML（config/*.yaml 内容検証に必須ではあるが無くても起動可）
- defusedxml（ニュース収集で利用）
- （SQLite は Python 標準の sqlite3 を利用）
※ 実際の requirements.txt がある場合はそちらを利用してください。

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（例）
   - pip install duckdb httpx websocket-client pyyaml defusedxml
   - 必要に応じて追加パッケージをインストール
4. 環境設定ファイルの作成
   - python -m kabusys.config_setup
     - 対話ウィザードで .env を生成します（.env の既存値は再利用）
   - .env は絶対に Git にコミットしないでください
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を FAIL として扱う場合:
     - python -m kabusys.validate_config --strict

主要環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（よく使うもの）:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
  - KABU_API_BASE_URL: kabuステーション API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知用（任意）
  - KILL_FLAG_CLEAR_ON_START: 本番起動時に既存の kill.flag を自動クリアするか（0/1、デフォルト 0）
- 自動 .env ロード:
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします
  - .env.local が存在すれば .env を上書きして読み込みます
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

使い方（主要スクリプト）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 起動前検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（本日のセッションを実行）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録
    - KABUSYS_ENV=development でも Mock が使われます
    - KABUSYS_ENV=live は未実装の箇所があるため注意（現状 NotImplementedError を出す）
  - 停止:
    - 実行プロセスはプロジェクトルート/data/stop_requested.flag の検出で安全に停止します
    - kill.flag（デフォルト data/kill.flag）を使用して即時 kill_switch を発動可能（設定により起動時に既存 kill.flag を拒否する）
- モニタリング（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します
- 実装のポイント
  - ExecutionEngine.run_session はシグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）を想定
  - OrderManager はクラッシュ安全性（OrderSent の永続化等）を考慮した2相的な永続化設計
  - Reconciler は起動時の OrderSent レコードをブローカーと照合して整合性を回復

停止・制御ファイル
- data/stop_requested.flag: 存在するとループ系プロセス（monitoring, execution）が検出して穏やかに終了します
- kill.flag（デフォルト KILL_FLAG_PATH）：エンジン内で即座に全 active 注文をキャンセルする kill_switch のトリガー
- PID ファイル: settings.pid_file_path（デフォルト data/execution.pid）に PID を書きます

開発メモ
- DB 初期化:
  - run_execution/run_monitoring は起動時に必要なテーブルの冪等初期化（init_orders_db / init_monitoring_db 等）を呼びます
- テスト用モック:
  - MockBrokerClient は paper_trading やユニットテスト向け。PAPER_FILL_MODE（instant/partial/never/reject）で挙動を指定可能
- 設定ファイル:
  - config/*.yaml（system_config.yaml など）を用いる設計。PyYAML がない場合は内容検証をスキップしますがファイル存在は警告されます

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数と .env の自動読み込みロジック、Settings クラス
  - config_setup.py         — .env 生成/更新ウィザード（CLI）
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — モニタリングポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py         — BrokerAPIProtocol / データモデル / 例外 / factory
    - broker_factory.py     — Settings に応じたブローカー選択ファクトリ
    - kabu_client.py        — kabuステーション REST API 実装
    - mock_client.py        — テスト用モックブローカー
    - order_record.py       — 注文状態・状態遷移ロジック
    - order_repository.py   — SQLite による永続化層
    - order_manager.py      — 発注フローの外向け API（作成・送信・同期・取消）
    - execution_engine.py   — 発注エンジン本体（シグナル処理 + push ドレイン）
    - reconciler.py         — 再起動時のリコンシリエーション
    - risk_manager.py       — 3段階リスクガード
    - ...（その他関連モジュール）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集ロジック（プレースホルダ）
    - jquants_client.py      — J-Quants API クライアント等（参照）
  - monitoring/
    - monitoring_db.py      — 監視用 DB 初期化とログ書き込み
    - system_monitor.py     — システム資源監視ロジック
  - utils/
    - logging_setup.py      — ロギング設定
    - process_priority.py   — プロセス優先度設定ユーティリティ
  - scripts/
    - generate_config.py    — config/*.yaml を生成するスクリプト（参照）

最後に
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- 本番（live）運用時は設定・通知先（LINE 等）や Kill Switch の扱いを十分に確認してください。
- 本 README はコードの現状に基づく概要です。詳細実装や追加のユーティリティはソースコード内の docstring を参照してください。

必要であれば、README にインストール用の requirements.txt の候補や具体的な systemd / supervisor 用のサービス定義テンプレート、より詳しい運用手順（デプロイ手順・バックアップ・監視）を追記します。どの情報が必要か教えてください。