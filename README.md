# KabuSys

日本株向け自動売買システムのコアライブラリ（KabuSys）。  
このリポジトリは発注エンジン、リスク管理、監視、データ収集用のユーティリティ群を含みます。  
（本 README はコードベースの主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです）

---

## プロジェクト概要

KabuSys は以下の機能を備えた自動売買の基盤ライブラリです。

- Signal ベースの注文エンジン（ExecutionEngine）
- ブローカークライアント抽象（kabuステーション向け実装 + モック）
- 3 段階のリスクガード（Gate1/Gate2/Gate3）
- 注文状態管理（OrderRecord）と SQLite 永続化（OrderRepository）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor 起動スクリプト）
- データ関連：マーケットカレンダー管理、ニュース収集など
- 環境設定ウィザード（.env 作成）と起動前設定検証 CLI

設計上、DB（SQLite / DuckDB）や外部 API（kabu station / J-Quants）とのインタフェースは明確に分離されています。テスト用に MockBrokerClient が提供され、本番接続は将来的に KabuStationClient を利用します。

---

## 主な機能一覧

- config (.env) ウィザード: 対話式で .env を生成 / 更新（kabusys.config_setup）
- 設定検証 CLI: .env と config/*.yaml の存在/基本妥当性チェック（kabusys.validate_config）
- ExecutionEngine: シグナル読み取り→リスクチェック→発注→push ドレインまでのワークフロー（run_execution）
- Monitoring loop: SystemMonitor の定期ポーリング（run_monitoring）
- Broker API 層: Protocol とファクトリ、KabuStationClient（実装）と MockBrokerClient（テスト用）
- Order 管理: OrderRecord（状態遷移ロジック）、OrderRepository（SQLite 永続化）、OrderManager（外向け API）
- RiskManager: レート制限、サーキットブレーカー、ポジション上限、ドローダウン監視
- Data utilities: カレンダー管理、ニュース収集（RSS）

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール（例）
   - 実際の requirements.txt がない場合は、機能に応じて以下をインストールしてください。
   ```bash
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```
   - 注意: PyYAML を入れると config/*.yaml のパース検証が有効になります。

4. 初期設定（.env）の作成
   - 対話式ウィザードを利用して .env を生成できます：
   ```bash
   python -m kabusys.config_setup
   ```
   - 生成後、内容を確認して必要な秘密情報（J-Quants トークンや Kabu API パスワード等）を設定してください。

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主なコマンド）

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（Execution）
  - 本番 / テストの実行エントリポイント（settings による挙動分岐）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、発注履歴は data/paper_trading.db に分離されます。

- 監視プロセス（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

---

## 主要環境変数

必須
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）

任意 / 推奨（主なもの）
- KABUSYS_ENV : 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL : kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN : 本番アラート用 LINE トークン（任意）
- LINE_USER_ID : LINE の通知先ユーザー ID（任意）
- KILL_FLAG_CLEAR_ON_START : 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE : paper_trading 用 Mock の fill 動作（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒）

自動ロード
- プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込みします。
- OS 環境変数優先。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

設定ファイル
- config/*.yaml（例: system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）  
  validate_config は PyYAML がインストールされている場合にパース検証を行います。欠けているファイルは警告が出ます。

ファイル / フラグ
- data/kill.flag : エンジン運転中の「kill switch」フラグ
- data/stop_requested.flag : 監視ループ停止用フラグ
- data/execution.pid : Execution の PID ファイル（デフォルト）

---

## 動作モードについて

- development: ローカル開発用（MockBrokerClient を使うのが想定）
- paper_trading: ペーパートレード（MockBrokerClient を使用、DBは data/paper_trading.db に分離）
- live: 本番（本番ブローカークライアント / 実際の発注を行う設計。現状 KabuStationClient は実装され一部は利用可能だが、本番運用時は慎重に設定を確認してください）

注意: KABUSYS_ENV=live 設定時は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値等の追加チェックが走ります（validate_config、Settings）。

---

## 開発者向けメモ

- ブローカークライアントは create_broker_api(factory) を通じて取得します。モード切替は BrokerClientFactory で行われます。
- Order の状態遷移ロジックは OrderRecord に集中しており、OrderManager が永続化／API 呼び出しの順序（2相永続化など）を管理します。
- リコンシリエーション（Reconciler）は起動時に OrderSent 状態の注文を突合して自動回復します。
- RiskManager はトークンバケツ方式のレート制限とサーキットブレーカーを備えています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — .env の読み込み、Settings クラス（環境変数アクセス）
  - config_setup.py — .env 対話式ウィザード（生成 / 更新）
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - __init__.py — execution 層のエクスポート
    - broker_api.py — BrokerAPIProtocol, データモデル, 例外, ファクトリ
    - broker_factory.py — Settings に基づくクライアント生成
    - kabu_client.py — kabu station 実装（HTTP + websocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — 注文状態モデル・状態遷移判定
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — 発注 API（create/send/sync/cancel）
    - execution_engine.py — セッション実行ロジック（signal 処理 + push ドレイン）
    - reconciler.py — リコンシリエーション（起動時自動復旧）
    - risk_manager.py — Gate1/2/3 リスクガード

  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB + J-Quants）
    - news_collector.py — RSS ニュース収集（セキュリティ考慮あり）
    - (その他データ関連モジュール)

  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル初期化等
    - system_monitor.py — SystemMonitor（run_monitoring から使用）

  - utils/
    - logging_setup.py — ロギング初期化
    - process_priority.py — プロセス優先度設定ユーティリティ
    - (その他ユーティリティ)

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （validate_config で存在チェック・パースチェックされます。generate スクリプト等で生成可能。）

---

## よくある操作例

- .env を生成して検証 → 実行（ペーパートレード）
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視プロセスをデバッグ的に短い間隔で動かす
  ```bash
  export MONITOR_POLL_INTERVAL=10
  python -m kabusys.run_monitoring
  ```

---

## 注意事項 / セキュリティ

- .env ファイルには機密情報（API トークン / パスワード）が含まれます。絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）での実行はリスクが高いため、validate_config の警告を確認し、LINE 通知や kill flag の設定を必ず整えてください。
- news_collector 等は外部 HTTP を取り扱うため SSRF / XML 脆弱性対策（defusedxml、URL フィルタ等）を行っていますが、運用上の注意を配慮してください。

---

この README はコードベース（src/kabusys/*）の現在の構成に基づく概要ドキュメントです。さらに詳細な API 仕様や運用手順は個別モジュールの docstring / ソースを参照してください。