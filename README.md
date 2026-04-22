# KabuSys

日本株自動売買システムのサンプル実装（README）

この README はこのコードベースの概要、主要機能、セットアップ手順、および実行方法を日本語でまとめたものです。

注意: このリポジトリはサンプル実装です。実際の資金を使った運用・本番接続（kabuステーション等）は十分な理解と安全対策の上で行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買エンジンの構成例です。以下の主要コンポーネントを備えています：

- 環境変数 / .env ベースの設定管理（自動ロード、対話式ウィザード）
- 設定検証 CLI（起動前に.env と config/*.yaml の問題を検出）
- ExecutionEngine：シグナルを読み取り発注・状態管理を行うエンジン
- ブローカークライアント群：
  - MockBrokerClient（paper_trading / development 用テストモック）
  - KabuStationClient（kabuステーション REST API クライアント、実装済み）
- 注文の状態遷移モデル（OrderRecord）と永続化（SQLite）
- リスク管理（3段階ガード：Gate1/Gate2/Gate3）、サーキットブレーカー、レート制御
- リコンシリエーション（クラッシュ復旧）：OrderSent の突合やポジション差分検出
- 監視プロセス（SystemMonitor をポーリングして監視DBへ記録）
- データモジュール（マーケットカレンダー管理、RSSニュース収集など）
- ユーティリティ（ログ設定、プロセス優先度設定等）

設計方針として、ビジネスロジックと I/O（DB/API/ファイル）を分離し、クラッシュ時の安全性（永続化順序や再同期機構）に配慮しています。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）で必須環境変数・YAML ファイル等を検査

- 発注 / 実行
  - ExecutionEngine によるシグナル取得 → Gate1/Gate2 チェック → 発注フロー
  - OrderManager による二相永続化（OrderSent 前後の安全な DB 更新）
  - MockBrokerClient によるペーパートレード・テスト（fill_mode オプション）
  - KabuStationClient による実ブローカー API 実装（httpx, websocket 使用）
  - Reconciler による起動時の自動復旧（OrderSent の突合、ポジション差分検出）

- リスク管理
  - Gate1: 余力・重複・銘柄・全体上限チェック
  - Gate2: レート制限（トークンバケツ）・サーキットブレーカー
  - Gate3: ドローダウン監視（kill_switch 発動）

- 永続化 / 監視
  - orders テーブル（SQLite）で注文履歴を永続化
  - DuckDB を分析用 DB として使用（signals / position_entries など）
  - 監視プロセス（run_monitoring）で定期ログ収集（SQLite + DuckDB）

- データ取得
  - マーケットカレンダー（J-Quants 経由）管理（DuckDB）
  - RSS ニュース収集（前処理、SSRF 対策、DefusedXML 使用）

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の型記法などを使用）
- pip（パッケージ管理）
- SQLite（標準ライブラリに同梱）
- 推奨パッケージ（実行に必要になる機能に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (config YAML の検証に必要、無くても起動可だが警告)
  - defusedxml
  - その他（必要に応じて）: requests 等

（requirements.txt がない場合は上記を個別に pip install してください）

例:
pip install duckdb httpx websocket-client pyyaml defusedxml

---

## セットアップ手順

1. リポジトリをクローンして、Python 仮想環境を作成・有効化します。
   - git clone <repo-url>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（上の「必要条件」を参照）。
   例:
   - pip install duckdb httpx websocket-client pyyaml defusedxml

3. .env の作成
   - 対話式ウィザードを使って初期 .env を生成します（.env の作成を推奨）:
     - python -m kabusys.config_setup
     - デフォルトはプロジェクトルートの .env に保存されます。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他オプションやデフォルトはウィザードで確認できます。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

5. DB 初期化（実行前に必要なら）
   - Execution / Monitoring は起動時に必要テーブルを作成する初期化関数を呼ぶ設計です。
   - ただし、orders テーブルを用いる場合は init_orders_db を呼ぶなど、スクリプトや起動時に処理されます。

6. 実行用ディレクトリの作成
   - data/ フォルダ（デフォルト DB 保存先等）を作成してください（多くのコードは起動時に自動作成もしますが確認推奨）。
   - stop flag / kill flag のパスは .env で設定できます（デフォルトは data/ 内）。

---

## 使い方（コマンド・実行）

- 設定ウィザード（.env を作る）
  - python -m kabusys.config_setup
  - 対話式に各キーを入力し、.env を生成します。

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱いになります。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV に応じて挙動が変わります（development / paper_trading / live）。
    - paper_trading では MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）にログを残します。
    - 起動時に data/execution.pid（デフォルト）に PID を書きます。
    - 停止するにはプロジェクトルート data/stop_requested.flag を作成するか、kill.flag を設定して kill_switch を発動できます。

- 監視プロセス起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更できます（デフォルト: 60）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する設計です。

- 環境変数の自動読み込み制御
  - デフォルトではプロジェクトルートの .env を自動読み込みします。
  - 自動ロードを無効化するには環境変数を設定:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 停止・Kill Switch
  - 停止フラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring が検出して終了します。
  - kill.flag: 実行時に存在すると ExecutionEngine が起動を拒否する場合があります（KILL_FLAG_CLEAR_ON_START により動作を制御）。

---

## 重要な環境変数（主な一覧）

- 必須
  - JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）

- 推奨/オプション
  - KABUSYS_ENV            — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            — SQLite（監視DB）パス（デフォルト: data/monitoring.db）
  - LOG_LEVEL              — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - KABU_API_BASE_URL      — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知トークン（本番時のアラート用）
  - LINE_USER_ID              — LINE 通知先ユーザーID
  - PAPER_FILL_MODE           — paper_trading 実行時のモック約定挙動（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
  - MONITOR_POLL_INTERVAL     — 監視ポーリング間隔（run_monitoring）
  - KILL_FLAG_CLEAR_ON_START  — kill.flag があっても起動時にクリアするか（0|1）

validate_config や Settings クラス内で有効な値チェックが実装されています。

---

## 実行フロー（概略）

1. ExecutionEngine の起動:
   - PID ファイル書き込み
   - Reconciler（存在する場合）で OrderSent の突合・ポジション差分チェック
   - シグナル処理フェーズ（指定時刻内）: DuckDB から signals を読み、Gate1/Gate2 を経て発注
   - push ドレインフェーズ（WebSocket を利用して broker からの push を処理）
   - 終了時に PID ファイル削除

2. Order のライフサイクル:
   - OrderCreated（DB に保存）
   - OrderSent（送信前に状態を永続化）
   - broker の応答に応じて Accepted/Partial/Filled/Rejected/Cancelled 等に遷移
   - Reconciliation によりクラッシュ復旧を行えるような永続化順序が設計されています

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を要約）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py          — .env を対話式に作るウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine を起動するスクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - execution/
    - broker_api.py          — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py      — Settings に応じたクライアントを生成するファクトリ
    - kabu_client.py         — kabuステーション REST/WebSocket クライアント
    - mock_client.py         — テスト用モック実装（fill_mode 等）
    - order_record.py        — 注文状態モデル（状態遷移の検証）
    - order_repository.py    — SQLite 永続化（orders テーブル）
    - order_manager.py       — 発注フローの外向き API（create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine（シグナル処理 / push ドレイン / kill_switch）
    - reconciler.py          — 起動時の自動復旧・突合処理
    - risk_manager.py        — Gate1/Gate2/Gate3 のリスクガード
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite スキーマ・ロガー（参照）
    - system_monitor.py      — システム監視ロジック（参照）
  - data/
    - calendar_management.py — 市場カレンダー管理（DuckDB・J-Quants 連携）
    - news_collector.py      — RSS ニュース収集・前処理
    - jquants_client.py      — J-Quants API クライアント（参照）
  - utils/
    - logging_setup.py       — ログ初期化ヘルパー
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - scripts/
    - generate_config.py     — config/*.yaml の雛形生成（validate_config のメッセージ参照）

（上記は主要ファイルのみ抜粋。詳細はソースコードを参照してください）

---

## 運用上の注意

- 本番モード（KABUSYS_ENV=live）は慎重に扱ってください。validate_config では live の場合に追加の警告が出ます（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注記あり）。
- 発注フローはクラッシュに対する復旧を考慮して設計されていますが、実際の証券会社接続・本番運用には更なるテストと安全策（手動監査、段階的ロールアウト等）が必要です。
- KabuStationClient は PC 上で kabuステーション® が起動していることを前提としています。接続 URL とパスワード設定を確認してください。
- DuckDB / SQLite のパスはデフォルトで data/ 以下に配置されます。適切なバックアップとファイルパーミッションを設定してください。

---

## よく使うコマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 実行:
  - python -m kabusys.run_execution
- Monitoring 実行:
  - python -m kabusys.run_monitoring

---

README はここまでです。より詳細な API や内部設計（Order の永続化順序、Reconciler の動作、RiskManager のパラメータ調整など）については各モジュールの docstring を参照してください。必要であれば各モジュールごとの詳しいドキュメントや例を追加で作成します。