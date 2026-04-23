# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
この README はコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。  
主な責務は以下のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 発注・注文状態の永続化（SQLite）
- ブローカー API 抽象化（実運用向けの KabuStationClient、テスト用の MockBrokerClient）
- リスク管理（3段階ガード: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- マーケットカレンダー管理・ニュース収集などのデータ処理（DuckDB）
- 監視ループ（SystemMonitor）
- 環境設定ウィザード（.env 作成支援）および設定検証 CLI

設計上、DB 操作・ビジネスロジック・外部 API 呼び出しは役割分離されています。ペーパートレード用に本番 DB と完全分離される仕組み（PAPER_TRADING）を持ちます。

---

## 主な機能一覧

- .env 自動読み込み（OSC 環境 > .env.local > .env、必要に応じて自動ロードを無効化可能）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 起動前構成検証 CLI（python -m kabusys.validate_config、--strict オプションあり）
- ExecutionEngine（シグナル処理と WebSocket push ドレイン）
- Broker API 抽象化（Protocol）とファクトリ（mock / live 切替）
- MockBrokerClient（テスト用、fill_mode 等で挙動を制御）
- Order 管理（OrderRecord / OrderRepository / OrderManager）
- RiskManager（Gate1: シグナルレベル、Gate2: レート制限/CB、Gate3: ドローダウン）
- Reconciler（再起動時の OrderSent 照合とポジション差分チェック）
- Data モジュール（マーケットカレンダー管理、ニュース収集など）
- Monitoring（監視用ループ、監視 DB へのログ記録）

---

## 必要な環境変数

validate_config と Settings に基づく主要な環境変数は次の通りです。

必須（少なくとも設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（運用に応じて設定）:
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL（kabu station API のベース URL）
- LINE_CHANNEL_ACCESS_TOKEN（アラート通知用）
- LINE_USER_ID（アラート通知先）

その他運用関連:
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアするか: 0/1）
- PAPER_FILL_MODE（paper_trading 用の fill モード: instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite DB）
- PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など（監視・実行に用いる）

.env の生成は対話式スクリプト（config_setup）を使うのが推奨です。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
   - もしくは少なくとも以下をインストールしてください:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML（YAML 検証を有効にする場合）
     - defusedxml
   - 例:
     - pip install duckdb httpx websocket-client PyYAML defusedxml

4. .env の作成
   - 推奨: 対話式ウィザードで作成
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成し、上記の必須変数を設定してください。
   - .env は Git にコミットしないでください（スクリプトも同様に注意喚起を出します）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

---

## 使い方（起動コマンド）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- 実行エンジン起動（本番/ペーパートレード）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV により動作が変わります。development / paper_trading では MockBrokerClient が使われます。
    - 本番（live）は未実装（BrokerClientFactory は NotImplementedError を投げます）。
    - 停止制御: リポジトリルートの data/stop_requested.flag を作成すると起動中のループが停止します。
    - kill.flag により起動拒否や kill_switch をトリガできる点に注意（KILL_FLAG_CLEAR_ON_START に依存）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に留意してください。

- テスト・開発用のモッククライアント
  - create_broker_api(mock=True, fill_mode=...)
  - fill_mode: instant / partial / never / reject（MockBrokerClient の挙動に影響）

---

## 実行時の挙動・運用ノート

- ExecutionEngine
  - 1日セッション単位で動作（デフォルトのタイムレンジや target_date は EngineConfig で制御）
  - 起動時に Reconciler による同期（OrderSent の照合、ポジション差分検出）を行う（reconciler が渡されている場合）
  - シグナル処理（指定時間帯） → push drain（WebSocket） → セッション終了
  - kill_switch() は全 active 注文をキャンセルしループを停止する

- Order 管理
  - OrderRecord は状態遷移の検証を行い、InvalidStateTransitionError を投げる
  - OrderRepository は SQLite を用いた永続化層（テーブル作成関数 init_orders_db あり）
  - OrderManager は二相永続化を意識した設計（OrderSent の永続化 → ブローカー呼び出し → broker_order_id の永続化 → OrderAccepted 更新）

- RiskManager
  - Gate1: シグナル単位の余力・重複・ポジション上限検査
  - Gate2: トークンバケツによるレート制限 + サーキットブレーカー
  - Gate3: ドローダウンによる kill 判定（initial_portfolio_value を基準）

- DB
  - DuckDB: 信号・市場データ・analytics 用（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視・orders DB 等（デフォルト: data/monitoring.db / data/paper_trading.db）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数の読み込み/管理（自動 .env ロード、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（メインエントリ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — execution 関連の公開 API
    - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
    - broker_factory.py — Settings に応じたブローカー生成ファクトリ
    - kabu_client.py — KabuStationClient（実ブローカー API、httpx/websocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — Order の外向き API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン・セッション管理）
    - reconciler.py — Reconciliation（再起動時の自動復旧）
    - risk_manager.py — リスクガード実装
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集
    - jquants_client.py (参照あり) — J-Quants API ラッパ（別ファイル想定）
  - monitoring/
    - monitoring_db.py (参照あり) — 監視用 DB 初期化・ロギング（別ファイル想定）
    - system_monitor.py (参照あり) — システム監視ロジック（別ファイル想定）
  - utils/
    - logging_setup.py (参照あり) — ログ初期化
    - process_priority.py (参照あり) — プロセス優先度設定

（注）README に列挙されている一部ファイルはこの抜粋に含まれていないため、プロジェクト内で実装されているものとして参照しています。

---

## よくある操作例

- .env を作って検証 → 実行エンジンを起動する一連の流れ:
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config
  3. python -m kabusys.run_execution

- 監視プロセス単独起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- テストでモックを利用してエンジンを起動する場合:
  - 環境変数を KABUSYS_ENV=development または paper_trading に設定（.env で指定）
  - MockBrokerClient が使用され、実ブローカーを必要としない

---

## 注意事項 / 運用上のヒント

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV=live のときは本番リスクがあるため、LINE 通知や KILL フラグなどの設定を慎重に行ってください（validate_config で live 時の追加チェックあり）。
- 本番ブローカークライアント（KabuStationClient）は API トークン管理や WebSocket の再接続ロジックを含みます。テスト・開発は MockBrokerClient を使うと安全です。
- DB のパス（DUCKDB_PATH / SQLITE_PATH）はデフォルトで `data/` 配下を使います。プロダクションではディレクトリ権限・バックアップを検討してください。

---

必要であれば、README に動作フロー図、API 仕様、テストの実行方法、デプロイ手順（systemd / コンテナ化）などの追加ドキュメントを追記できます。どの情報を優先して追加しますか？