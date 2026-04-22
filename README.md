# KabuSys

日本株自動売買システム（ミニマム実装）  
このリポジトリは、発注エンジン・リスクガード・監視・データ収集などを統合した自動売買フレームワークのコア部分です。モジュールはできるだけ単純な責務分離で設計されており、ローカル開発・ペーパートレードでの検証が容易です。

バージョン: 0.1.0

---

## 概要

主なコンポーネント:

- 環境設定管理（`.env` 読み込み・ウィザード）
- 設定検証 CLI（起動前に環境変数や config YAML をチェック）
- ExecutionEngine（シグナルに基づく発注エンジン）
- Broker クライアント層（実運用は kabuステーション、テスト用に Mock）
- Order の状態遷移ロジック / 永続化（SQLite）
- リコンシリエーション（クラッシュ復旧）
- RiskManager（Gate1/2/3 による多段階リスク制御）
- 監視ループ（SystemMonitor をポーリングして監視 DB にログ）

本リポジトリは、KABUSYS_ENV によって挙動を切り替えられます：
- `development` : 開発（kabuステーション不要、Mock を使用）
- `paper_trading` : ペーパートレード（MockBrokerClient、paper 用 DB に記録）
- `live` : 本番（実際のブローカークライアント想定）

---

## 機能一覧

- .env ウィザード（`kabusys.config_setup`）で初期設定を対話的に作成
- 設定検証ツール（`kabusys.validate_config`）で起動前チェック（必須環境変数・YAML 構文・パス等）
- ExecutionEngine（信号読み取り → Gate1/2 判定 → 発注 → push drain）
- Order state machine（OrderRecord）と SQLite 永続化（OrderRepository）
- MockBrokerClient による発注シミュレーション（fill モード制御: instant/partial/never/reject）
- Reconciler によるクラッシュ後の自動同期処理
- RiskManager（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視）
- 監視プロセス（run_monitoring）で定期的にシステム状態を監視・記録
- DuckDB を用いたデータ分析用テーブル（signals / portfolio_targets / position_entries 等の利用想定）
- News collector / market calendar utilities（データ収集・営業日判定ロジック）

---

## 必要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（有用）:
- KABUSYS_ENV (development|paper_trading|live) — デフォルト `development`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- LOG_LEVEL — `DEBUG|INFO|WARNING|ERROR|CRITICAL`（デフォルト `INFO`）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト `http://localhost:18080/kabusapi`）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番時のアラート通知用

その他、PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH、PID / KILL フラグ関連など多数の設定が `kabusys.config.Settings` で参照されます。詳細は `src/kabusys/config.py` を参照してください。

---

## セットアップ手順

1. Python 環境を準備（推奨: venv）
   - python 3.9+（コードは 3.10+ の構文を使用している可能性があります）
   - 仮想環境を作成・有効化:
     - unix/macOS:
       - python -m venv .venv
       - source .venv/bin/activate
     - Windows:
       - python -m venv .venv
       - .venv\Scripts\activate

2. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb httpx websocket-client PyYAML defusedxml
   - 追加で必要なライブラリがあれば README を更新してください。

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

3. リポジトリルートで data ディレクトリを作成（必要に応じて）
   - mkdir -p data

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（`.env.example` があれば参照）。`.env` は Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗とみなす場合:
     - python -m kabusys.validate_config --strict

---

## 使い方

主要な実行スクリプト:

- 環境設定ウィザード（.env を作成 / 更新）
  - python -m kabusys.config_setup
  - 対話的に値を入力し `.env` を保存します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit code 1 にする

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され、paper_trading 用 SQLite に記録されます。
  - 停止はルートの `data/stop_requested.flag` を作成することで行います（起動中のプロセスは検知して終了します）。
  - PID ファイルは `data/execution.pid`（設定で変更可能）に書き出されます。
  - 起動時に `kill.flag` が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動可）。

- 監視ループ（System Monitor）
  - python -m kabusys.run_monitoring
  - 簡易ポーリングループでシステムメトリクスを監視します。`MONITOR_POLL_INTERVAL` 環境変数で秒数を上書き可（デフォルト 60 秒）。
  - 監視は本番 DB（settings.sqlite_path）を使用します（環境にかかわらず）。

- その他（モジュールとして利用）
  - from kabusys.config import settings
  - settings を使って設定を参照できます（例: settings.duckdb_path）

注意点:
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると `.env` の自動ロードを無効化できます（テスト時など）。
- `.env` はプロジェクトルート（.git または pyproject.toml が見つかる場所）から自動検索されます。

---

## 簡単な実行例

1. .env を作成（ウィザード）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 実行（ペーパートレード）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

4. 監視（別プロセス）
   - python -m kabusys.run_monitoring

---

## 主要なディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数の読み込み / Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_api.py — Broker API のデータモデル、Protocol、ファクトリ
    - kabu_client.py — kabuステーション REST API 実装
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — 設定に応じて BrokerClient を生成
    - order_record.py — Order の状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py — SQLite による永続化
    - order_manager.py — Order の外向き API（作成・送信・同期・キャンセル）
    - execution_engine.py — ExecutionEngine（発注ループ / push drain / session 管理）
    - reconciler.py — 起動時のリコンシリエーション
    - risk_manager.py — Gate1/2/3 の実装（各種リスク判定）
  - data/
    - calendar_management.py — 市場カレンダー管理（J-Quants を利用する想定）
    - news_collector.py — RSS ニュース収集（前処理・正規化・SSRF 対策含む）
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化・ログインターフェース（参照される）
    - system_monitor.py — 実システムモニタリング（参照される）
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上は抜粋です。詳細は各モジュール内の docstring を参照してください。）

---

## 開発・運用上の注意

- .env は絶対にバージョン管理にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE 通知トークン等を必ず設定し、KILL フラグ等の運用手順を明確にしてください。
- ExecutionEngine は PID / kill.flag を使ってプロセス管理を行います。オーケストレーション（systemd / supervisor / Kubernetes 等）に組み込む場合はこれらのファイルの場所と挙動を反映してください。
- DB パス（DuckDB / SQLite）は `Settings` で定義されているデフォルトを使用しますが、運用環境に合わせて変更してください。
- Reconciler はクラッシュ後の回復を支援しますが、すべての障害ケースをカバーするわけではありません。手動オペレーション手順（運用者向けの runbook）を用意してください。

---

## 貢献

バグ報告やプルリクエスト歓迎です。機能追加は以下を意識してください:
- 単一責務（モジュールごとの分離）
- DB とビジネスロジックの分離（OrderRecord は DB に依存しない）
- テストの追加（特に状態遷移 / Reconciler / RiskManager）

---

必要であれば、README にサンプル .env.example、より詳細な依存関係一覧（requirements.txt）やデプロイ手順（systemd ユニット例等）を追加できます。どの情報を優先して追記しますか？