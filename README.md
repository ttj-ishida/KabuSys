# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム（プロジェクト骨格）です。シグナル取得 → 発注 → 約定監視 → リコンシリエーション といった発注ワークフローを実装するためのモジュール群（Execution Engine、Broker クライアント、注文永続化、リスクガード、監視/モニタリング、データユーティリティ等）を含みます。開発・ペーパートレード・本番の実行モードに対応する設計です。

主な想定用途
- ローカル開発 / テスト（開発モード）
- ペーパートレード（Mock ブローカーでの動作検証）
- 本番運用の基礎構成（KabuStation 経由の実運用は将来的な実装が前提）

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルートを基準）
  - 対話式ウィザードで .env を生成・更新（python -m kabusys.config_setup）
  - 設定検証 CLI（環境変数 / config/*.yaml の存在 & YAML パース検証、python -m kabusys.validate_config）

- 実行系（Execution）
  - ExecutionEngine：シグナルの取得・Gate（3段階）でのリスク検査・発注フロー（send / sync / cancel）
  - OrderRecord：注文状態遷移（状態遷移検証）
  - OrderRepository：SQLite による注文永続化（orders テーブル、ユニークインデックス等）
  - OrderManager：OrderRecord と Broker API を組み合わせた外向き API
  - Reconciler：再起動時の OrderSent 照合とポジション差分チェック
  - RiskManager：Gate1/2/3（余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
  - Broker クライアント群：
    - MockBrokerClient（テスト/開発用）— fill_mode（instant/partial/never/reject）を指定可能
    - KabuStationClient（kabuステーション REST API 実装）
  - 実行起動スクリプト（run_execution）

- 監視（Monitoring）
  - SystemMonitor ポーリングループ起動スクリプト（run_monitoring）
  - 監視用 SQLite DB（monitoring DB）への記録（Execution 内からの監視ログ書き込みを参照）

- データユーティリティ
  - market calendar 管理（DuckDB を使った営業日判定 / next_trading_day 等）
  - RSS ニュース収集（XML の安全パース、URL 正規化、記事ID 生成、前処理など）

- ユーティリティ
  - ロギングセットアップ・プロセス優先度設定等（utils.*）

---

## セットアップ手順（開発環境）

前提
- Python 3.10 以上（コード上で | 型等が使われています）
- Git

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate.bat  # Windows

3. 必要パッケージをインストール
   - 主要な依存（最低限）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（任意、config YAML の検証に必要）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   ※ 実行環境や CI に合わせて requirements.txt を用意している場合はそれを使用してください。

4. .env の準備
   - 対話的に作成する（推奨）:
     - python -m kabusys.config_setup
     - ウィザードに従って .env を生成します。
   - もしくは手動でルートの .env を作成（下記の必須項目を参照）。

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - すべて OK にしたい場合は --strict を付けると警告を FAIL 扱いして終了コード 1 を返します:
     - python -m kabusys.validate_config --strict

---

## 環境変数（主な項目）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（重要）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - development: ローカル開発（発注は Mock）
  - paper_trading: ペーパートレード（Mock ブローカー、paper DB を使用）
  - live: 本番（注意喚起あり）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API の base URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag 自動クリア（0/1）

実行時に必要なファイル/フラグ
- data/stop_requested.flag — 存在すると監視/実行ループは終了します
- data/kill.flag — kill switch（存在時は起動拒否、KILL_FLAG_CLEAR_ON_START=1 でクリアして起動可能）
- pid ファイル（設定により data/execution.pid など）

例（.env での設定例）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告もエラー扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（1セッション実行）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使われます。
    - 本番連携（KabuStationClient）を使うには KABUSYS_ENV=live と実際の kabu ステーション環境が必要（未実装/要注意箇所あり）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。

- テスト用/デバッグ
  - MockBrokerClient は fill_mode（instant/partial/never/reject）を指定して挙動を変えられます（設定経由またはテストコードで利用）。

ログや DB の場所は .env の設定に依存します。運用時は data ディレクトリ配下のファイル群（PID / flag / DB）に注意してください。

---

## ディレクトリ構成

以下は主要なファイルとモジュール（src/kabusys）です。実プロジェクトではさらに tests、scripts、config/*.yaml、docs 等があることが想定されます。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に応じた Broker クライアント生成
    - kabu_client.py         — KabuStation REST API クライアント（httpx）
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderRecord と状態遷移
    - order_repository.py    — SQLite 保存ロジック（orders テーブル）
    - order_manager.py       — 注文処理の外向き API
    - execution_engine.py    — ExecutionEngine（シグナル処理・push ドレイン等）
    - reconciler.py          — 再起動時リコンシリエーション
    - risk_manager.py        — 3段階リスクガード
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・ログ（参照: run_monitoring）
    - system_monitor.py      — SystemMonitor（ポーリング処理）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants API クライアント（参照あり）
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

- config/
  - *.yaml                   — システム設定ファイル（存在しない場合は警告）

- data/
  - （データファイル群: DuckDB / SQLite / flag / pid など）

---

## 運用上の注意 / トラブルシュート

- PyYAML がインストールされていない場合、validate_config は YAML の内容検証をスキップします（警告）。YAML パース検証が必要なら PyYAML をインストールしてください。
- KabuStationClient を使うには実際に kabuステーション が起動し、API が応答することが必要です。テストや開発では MockBrokerClient を利用してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- run_execution/run_monitoring はデータベースファイル（DUCKDB_PATH, SQLITE_PATH）へ接続します。これらの親ディレクトリが存在しない場合は自動作成されないことがあるため、事前にディレクトリを作成するか validate_config の警告を確認してください。
- kill.flag（KILL_FLAG）や stop_requested.flag によりプロセスの起動/停止が制御されます。運用時は flag の状態に注意してください。
- ExecutionEngine は起動時に PID ファイルを作成します。複数プロセスの同時起動に注意してください。

---

## 今後の拡張ポイント（参考）

- 本番用 KabuStationClient のさらなる確認・実装・監査
- 詳細なメトリクス収集 / Prometheus Exporter の追加
- CI での自動化テスト（OrderRecord の状態遷移、RiskManager の挙動、Reconciler の統合テスト等）
- 監視アラート（LINE / Slack 等）送信ロジックの実装・強化

---

この README はリポジトリ内のコード（src/kabusys）をもとに作成しています。追加の情報（実行サンプル、requirements.txt、運用ドキュメント等）があれば README を追補してください。