# KabuSys

日本株自動売買システムのコアライブラリ（プロトタイプ実装）。

このリポジトリには、発注エンジン・モニタリング・リスク制御・ブローカークライアント等の主要コンポーネントが含まれています。実運用前に安全性チェックや設定ファイル整備を行うための CLI（ウィザード / 検証ツール）も用意されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした自動売買コンポーネント群です。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアント抽象化（実運用向けの KabuStationClient、テスト用の MockBrokerClient）
- 注文永続化（SQLite）、監視（monitoring DB）、分析（DuckDB）
- 起動時のリコンシリエーション（Reconciler）によるクラッシュ復旧
- 3段階のリスクガード（Gate1/2/3）
- 環境変数ウィザード（.env 作成支援）と起動前検証ツール

設計上、DB への書き込み責務・API 呼び出し責務・ビジネスロジックを分離しており、テストやモックによる検証が容易です。

---

## 主な機能一覧

- .env ウィザード（interactive）
  - `python -m kabusys.config_setup`
- 設定検証ツール（.env と config/*.yaml の事前チェック）
  - `python -m kabusys.validate_config [--strict]`
- 発注エンジン起動スクリプト
  - `python -m kabusys.run_execution`
  - Paper trading（モック）対応（KABUSYS_ENV=paper_trading）
- 監視ループ起動スクリプト
  - `python -m kabusys.run_monitoring`
- ブローカー API 層（Protocol + 実装）
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション API 実装）
- 注文の状態遷移・永続化（OrderRecord / OrderRepository）
- リスク管理（Gate1: Signal / Gate2: Execution / Gate3: Metrics）
- リコンシリエーション（起動時の OrderSent 照合・ポジション差分検出）
- データモジュール：マーケットカレンダー管理・ニュース収集など

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（必要なもの）
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config 検証時に利用）
   - その他：標準ライブラリのみで動く箇所も多いです

   例:
   ```
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. .env を作成
   - 対話式ウィザードを利用するのが簡単です（下の「使い方」参照）。

5. 起動前検証
   - `python -m kabusys.validate_config` を実行し、必須変数や Yaml のパース等をチェックします。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABU_API_BASE_URL — kabu station API base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動ロード挙動:
- プロジェクトルートにある `.env` と `.env.local` を自動でロードします（OS 環境変数優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

1. .env の作成（ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   対話式に主要な環境変数を設定できます。ウィザードは既存の `.env` を読み込み、Enter で既存値を保持できます。最後に `.env` を保存するか確認されます。

2. 設定の検証（起動前）
   ```
   python -m kabusys.validate_config
   ```
   - 警告も FAIL 扱いにする場合:
     ```
     python -m kabusys.validate_config --strict
     ```
   - このツールは必須環境変数の未設定、プレースホルダ値、KABUSYS_ENV / LOG_LEVEL の不正、DB パスの親ディレクトリの有無、config/*.yaml（存在・YAML パース）のチェックを行います。
   - PyYAML がない場合は YAML の中身チェックをスキップします（警告が出ます）。

3. 発注エンジンを起動（本番 / ペーパートレード）
   ```
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV が `paper_trading` または `development` の場合、MockBrokerClient が使用されます（本番の KabuStationClient は未実装の箇所があります）。
   - paper_trading 時は DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離されます。
   - 起動時に `kill.flag` が存在すると、`KILL_FLAG_CLEAR_ON_START=1` の場合のみ自動クリアして起動、そうでなければ起動を拒否します。
   - 停止はリクエストファイル（data/stop_requested.flag）を作成することで行えます。スクリプトは起動中にこのフラグを監視します。

4. 監視ループを起動
   ```
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）。
   - 監視 DB は KABUSYS_ENV に関係なく `SQLITE_PATH`（または指定されたファイル）を使用します。

5. 開発・テスト
   - MockBrokerClient を使えば外部依存なしで発注フローやリスクロジックのテストが可能です。
   - `ExecutionEngine` は単体テストで `_process_signals()` や `_drain_push_queue()` を直接呼んで検証できます。

---

## 運用上の注意点

- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup はその旨のヘッダを付加して保存します）。
- 本番（KABUSYS_ENV=live）では LINE トークンなど通知設定を整備し、KILL_FLAG_CLEAR_ON_START は 0 を推奨します。
- run_execution / run_monitoring のプロセス優先度は起動時に「high」に設定されます（OS に依存）。
- run_execution は起動時に PID ファイルを書き込みます（デフォルト: data/execution.pid）。異常終了時に残る場合は手動で削除してください。
- Reconciler（起動時の自動復旧）は OrderSent の未解決注文をブローカーと照合し、ボラティリティ発生後の一貫性を保ちます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込み・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - 発注エンジン起動スクリプト
- run_monitoring.py
  - 監視ループ起動スクリプト

src/kabusys/execution/
- broker_api.py
  - BrokerAPIProtocol、データモデル、例外、create_broker_api()
- kabu_client.py
  - KabuStationClient（kabuステーション REST + WebSocket）
- mock_client.py
  - MockBrokerClient（テスト用）
- broker_factory.py
  - Settings を使ったクライアント生成
- execution_engine.py
  - ExecutionEngine（シグナル処理・push ドレイン・セッション制御）
- order_record.py
  - Order 状態列挙、OrderRecord の状態遷移検証
- order_repository.py
  - SQLite に対する永続化層（orders テーブル）
- order_manager.py
  - OrderManager（OrderRecord + OrderRepository + Broker を組合せた API）
- reconciler.py
  - 起動時の OrderSent 照合とポジション差分検出
- risk_manager.py
  - 3段階リスクガード（Gate1/2/3）

src/kabusys/monitoring/
- monitoring_db.py
  - 監視 DB の初期化・ログ機能（run_monitoring で使用）
- system_monitor.py
  - SystemMonitor（CPU/MEM/DISK 監視等）

src/kabusys/data/
- calendar_management.py
  - JPX カレンダー管理（J-Quants 連携）
- news_collector.py
  - RSS ニュース収集（前処理・保存ロジック）

src/kabusys/utils/
- logging_setup.py
  - ロギング初期化
- process_priority.py
  - プロセス優先度の設定ユーティリティ

config/
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml
  （存在を期待する YAML 設定ファイル — validate_config で検証します）

data/
- (デフォルトの DB/フラグ/ pid ファイル等を配置するディレクトリ)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 追加情報 / FAQ

- YAML 検証について: PyYAML がないと validate_config は YAML の中身検証をスキップします（警告を出します）。`pip install pyyaml` を推奨します。
- Paper trading モード: KABUSYS_ENV=paper_trading にすると MockBrokerClient が使用され、本番 DB とは別の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して発注を記録します。
- stop / shutdown:
  - 実行中プロセスを優雅に止めるには `data/stop_requested.flag` を作成します（run_monitoring・run_execution が監視して終了します）。
  - kill.flag は緊急停止スイッチとして扱われ、存在すると起動拒否や即時 kill_switch の発動条件になります。

---

## 開発者向け

- コードは機能ごとにモジュール化されており、単体テストは OrderRecord や RiskManager、MockBrokerClient を使って行うのが容易です。
- ExecutionEngine は時間依存のループを含みますが、内部メソッド（_process_signals / _drain_push_queue / _handle_push）を直接呼ぶことで副作用を制御できます。
- DB 初期化関係（orders テーブル等）は `init_orders_db` / `init_monitoring_db` を経由して冪等に作成できます。

---

この README はソースコードの主要点を簡潔にまとめたもので、運用時は `python -m kabusys.validate_config` を必ず実行して設定を確認してください。必要があれば README の補足や、運用手順（デプロイ、監視運用 Runbook 等）を追加します。