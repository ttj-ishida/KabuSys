# KabuSys

日本株向けの自動売買システム（プロトタイプ）です。  
このリポジトリは、環境設定管理、発注フロー（ExecutionEngine）、注文永続化、ブローカー抽象化（Mock / KabuStation）、リスクガード、監視ループ、データ系ユーティリティ（カレンダー・ニュース収集）などを含みます。

バージョン: 0.1.0

注意: .env 等の機密情報は絶対にコミットしないでください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は kabuステーション / J-Quants 等を利用した日本株自動売買のためのモジュール群です。
- 発注フローは Signal Queue を読み取り ExecutionEngine が OrderManager 経由で発注し、SQLite に注文履歴を保持します。
- paper_trading / development では MockBrokerClient を使って実行可能で、本番相当の動作検証が行えます。
- 起動時に設定検証や対話式 .env 生成ウィザードを提供します。

機能一覧
- 環境設定読み込み・管理（Settings）
  - .env / .env.local を自動ロード（必要に応じて無効化可能）
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数の存在チェック、YAML ファイルのパース確認、パスの存在確認など
  - --strict オプションで警告も失敗扱いに可能
- 発注エンジン（ExecutionEngine）
  - シグナル読み込み（DuckDB）→ Gate1/2 のリスクチェック → 発注 → push ドレイン
  - PID / kill flag 管理、kill_switch による全注文キャンセル
- 注文管理（OrderManager / OrderRecord / OrderRepository）
  - 注文状態遷移の検証、SQLite 永続化（orders テーブル）
  - Reconciliation（再起動時の OrderSent 照合）
- ブローカー抽象化（broker_api.create_broker_api）
  - MockBrokerClient（テスト用）実装あり
  - KabuStationClient（kabuステーション REST API 実装）
- リスク管理（RiskManager）
  - Gate1: シグナルレベルの余力／重複／ポジション上限チェック
  - Gate2: レート制限（トークンバケツ）・サーキットブレーカー
  - Gate3: ドローダウン監視（発注後）
- 監視ループ（run_monitoring）
  - SystemMonitor を定期ポーリングし SQLite / DuckDB にログを残す
- データユーティリティ
  - マーケットカレンダー管理（calendar_management）
  - ニュース収集（news_collector） — RSS 収集、URL 正規化、SSRF 対策等

セットアップ手順（開発環境向け）
1. Python 環境（3.10+ 推奨）を準備
   - 仮想環境を作成することを推奨します:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt は含まれていませんが、以下を少なくともインストールしてください:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (任意: config/*.yaml の内容検証に使用)
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

3. プロジェクトルートに data ディレクトリを作成（必要に応じて）
   - デフォルトで使用される DB 等のパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要なら手動でディレクトリを作成:
     - mkdir -p data

4. .env を準備
   - 対話式ウィザードで作成するのが簡単です（下の「使い方」参照）。
   - 自動ロード:
     - Settings はプロジェクトルートに .env / .env.local があれば自動で読み込みます。
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 (Settings.paper_sqlite_path)
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station のベース URL（デフォルト local）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知設定
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1）
  - PAPER_FILL_MODE — paper_trading 時のモック挙動（instant|partial|never|reject）
- 監視周り:
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（主要 CLI）
- 環境設定ウィザード（.env を対話式に生成）
  - python -m kabusys.config_setup
  - デフォルトでプロジェクトルート/.env を編集します。--env-file で別パス指定可能。

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする（CI 等で）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって:
    - development / paper_trading: MockBrokerClient を使用
      - paper_trading は data/paper_trading.db を使い本番 DB と分離
    - live: 現状 NotImplementedError（本番ブローカーは未実装）
  - 起動時に PID ファイルを書き、stop_requested.flag があれば起動をスキップ

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存せず）

- 注意点
  - .env は絶対に Git にコミットしないでください（README のテンプレートにも警告あり）。
  - validate_config は PyYAML が無い場合 YAML 内容チェックをスキップしますが、インストール推奨です。

簡単な .env の例
（実際には秘密値は適切に設定してください）
  JQUANTS_REFRESH_TOKEN=your_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  KABU_API_BASE_URL=http://localhost:18080/kabusapi
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0
  PAPER_FILL_MODE=instant

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数・.env 読み込み・Settings
    - config_setup.py                 — 対話式 .env ウィザード CLI
    - validate_config.py              — 設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — 監視ループ起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py                 — Broker API データモデル・Protocol・ファクトリ
      - broker_factory.py             — Settings を参照するクライアントファクトリ
      - kabu_client.py                — kabuステーション REST クライアント
      - mock_client.py                — MockBrokerClient（テスト用）
      - execution_engine.py           — 実行エンジン（シグナル処理・push ドレイン）
      - order_record.py               — 注文状態モデルと遷移ロジック（純粋ロジック）
      - order_repository.py           — SQLite 永続化レイヤ
      - order_manager.py              — 外向き注文 API（create/send/sync/cancel）
      - reconciler.py                 — 起動時リコンシリエーション
      - risk_manager.py               — Gate1/2/3 リスクガード
    - monitoring/
      - monitoring_db.py              — 監視DBの初期化・ロギング（参照される）
      - system_monitor.py             — SystemMonitor（ポーリング対象の実装）
    - data/
      - calendar_management.py        — マーケットカレンダー管理（DuckDB 用）
      - news_collector.py             — RSS ニュース収集
    - utils/
      - logging_setup.py              — ロギング初期化ユーティリティ
      - process_priority.py           — プロセス優先度設定ユーティリティ
- config/
  - system_config.yaml, data_config.yaml, ...（各種設定 YAML、存在チェックあり）

補足（運用・開発上のポイント）
- 起動前に python -m kabusys.validate_config で設定チェックを行ってください。CI では --strict を付けると警告も失敗扱いにできます。
- paper_trading は実際の発注を行わず、MockBrokerClient が発注・約定・残高をシミュレーションします。テスト時は paper_trading を使うのが安全です。
- ExecutionEngine はセッション（通常 8:50-15:30 など）に沿った処理を行う設計です。テストでは内部メソッド（_process_signals / _drain_push_queue）を直接呼ぶこともできます。
- Reconciler は再起動時に OrderSent の状態をブローカーと照合し、注文状態やポジション差分を検出します。運用時の自動復旧に重要です。
- news_collector や calendar_update_job 等の夜間バッチは DataPlatform.md の設計に従って動作します（外部 API の呼び出しや DB 保存を行います）。

ライセンス / コントリビュート
- この README 内にライセンスは明記していません。リポジトリに LICENSE がある場合はそちらを参照してください。  
- 機密情報 (.env) を誤ってコミットしないよう注意してください。

---

問題・バグ報告、機能リクエストはリポジトリの Issue にお願いします。