# KabuSys

日本株自動売買システムのコア部分（簡易実装）。  
このリポジトリは発注フロー、リスクガード、リコンシリエーション、監視、データ収集（カレンダー / ニュース）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys はローカル環境やペーパートレード環境で動作する日本株自動売買システムの骨格です。  
設計は次の関心ごとを分離しています：

- 設定管理 (.env / YAML)
- ブローカー API 抽象（実ブローカー / Mock）
- 発注エンジン（ExecutionEngine）
- 注文永続化（SQLite）
- 起動時リコンシリエーション（Reconciler）
- リスクガード（Gate1〜3）
- 監視ループ（SystemMonitor を想定、監視 DB を記録）
- データ系ユーティリティ（市場カレンダー、ニュース収集）

本実装は開発／ペーパー／本番のモードを想定しており、KABUSYS_ENV によって挙動が切り替わります（development / paper_trading / live）。

---

## 主な機能一覧

- .env / .env.local 自動読み込み（プロジェクトルート検出）
- 対話式環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数の未設定検出、YAML の存在・パースチェック、live 環境特有のガード等
- ExecutionEngine（signal queue を元にした発注ループ）
  - 発注：OrderManager → BrokerAPI（Mock/KabuStation）
  - 2相永続化パターン（OrderSent 前後のクラッシュ耐性）
  - WebSocket push ドレイン（kabu push を受けて同期）
  - リスクゲート（Gate1: シグナル／資金／ポジション、Gate2: レート制限／CB、Gate3: ドローダウン）
- Reconciler（OrderSent の復旧・ブローカー照合・ポジション差分検出）
- Mock ブローカークライアント（fill_mode：instant/partial/never/reject）
- OrderRecord（状態遷移を検証する純粋ドメインモデル）
- OrderRepository（SQLite ベースの永続化、スキーマ初期化関数）
- データユーティリティ
  - マーケットカレンダー管理（DuckDB を利用）
  - ニュース収集（RSS パーサ・URL 正規化・SSRF対策ほか）

---

## 前提 / 必要環境

- Python 3.10+
- SQLite（OS付属の sqlite3 が使用されます）
- 推奨インストールパッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（YAML 検証を有効にする場合）

例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb httpx websocket-client defusedxml pyyaml
```

- OS 権限やポート（kabu station を使う場合、kabu station がローカルで稼働していること）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化
2. 依存ライブラリをインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. DB 用ディレクトリの確認
   - デフォルトで data/ 配下にファイルを作成します。親ディレクトリが存在しない場合は警告が出ますが、起動中に自動作成されることが多いです。
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を変更してください。

---

## 使い方

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- 監視プロセス起動（SystemMonitor のポーリング）
  - デフォルトでは MONITOR_POLL_INTERVAL 環境変数（秒）で間隔を指定可能（デフォルト 60 秒）。
  ```bash
  python -m kabusys.run_monitoring
  ```

- 発注 / 実行エンジン起動
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用します（実ブローカー未実装）。
  ```bash
  python -m kabusys.run_execution
  ```

- 開発・テストでの Mock ブローカー利用
  - BrokerClientFactory を通して create_broker_api(mock=True, fill_mode="instant"|...) が利用されます。
  - fill_mode の選択により発注の挙動（即時約定 / 部分 / 保留 / 拒否）を変更できます。

注意:
- .env は機密情報（API トークン・パスワード）を含むため、絶対に Git にコミットしないでください。
- run_execution/run_monitoring は内部で PID ファイル / kill.flag を用います（data/ 配下）。停止制御には stop_requested.flag や kill.flag を使用します。

---

## 主要環境変数（抜粋）

重要なキーと簡単な説明：

- JQUANTS_REFRESH_TOKEN （必須） - J-Quants API 用トークン
- KABU_API_PASSWORD （必須） - kabuステーション API パスワード
- KABUSYS_ENV - 実行環境（development / paper_trading / live）
- DUCKDB_PATH - DuckDB ファイルパス（analytics）
- SQLITE_PATH - 監視/注文履歴用 SQLite パス
- LOG_LEVEL - ログレベル（DEBUG/INFO/...）
- KABU_API_BASE_URL - kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID - LINE 通知（本番向け）
- KILL_FLAG_CLEAR_ON_START - 起動時に kill.flag を自動クリア（1=有効、0=無効、本番は 0 推奨）
- MONITOR_POLL_INTERVAL - run_monitoring のポーリング間隔（秒）

詳細は対話式ウィザードやコード内 docstring を参照してください。

---

## ディレクトリ構成

以下は src/kabusys の主要ファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - execution/
    - __init__.py — execution パッケージの主要エクスポート
    - broker_api.py — Broker API のデータモデル・Protocol・例外・ファクトリ
    - kabu_client.py — kabu station REST API クライアント（httpx）
    - mock_client.py — Mock ブローカークライアント（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — 注文状態マシン（ドメインモデル）
    - order_repository.py — SQLite ベースの永続化層（init_orders_db を含む）
    - order_manager.py — 注文フロー（作成・送信・同期・キャンセル）
    - reconciler.py — 起動時リコンシリエーション
    - execution_engine.py — 発注エンジン（シグナル処理・WebSocket ドレイン）
    - risk_manager.py — 3 段階リスクガード

  - monitoring/
    - monitoring_db.py — 監視 DB 初期化 / ログ関数（コード内参照）
    - system_monitor.py — システム監視ロジック（コード内参照）

  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（SSRF 対策等）

  - utils/
    - logging_setup.py — ロギングセットアップ（コード内参照）
    - process_priority.py — プロセス優先度設定（コード内参照）

- config/
  - *.yaml — 各種 YAML 設定ファイル（system_config.yaml 等。validate_config でチェック対象）

- data/
  - （実行時に生成される DB・PID・フラグファイル等）

---

## 開発メモ / 設計上の注意点

- ExecutionEngine は signal_send_start/ end / market_close を持ち、シグナル処理と push ドレインを分けて実行します。
- OrderManager はクラッシュ耐性のため 2 段階の永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted に遷移）を採用しています。
- Reconciler は起動時に OrderSent 状態の注文を broker と照合し、ポジション差分を検出します（手動確認が必要なケースをログに残す）。
- mock クライアントはテストしやすいように fill_mode を持ち、さまざまなシナリオを再現できます。
- カレンダーとニュースは DuckDB を利用する前提の実装です（analytics 用）。

---

## よくある操作

- .env を作成したらまず設定検証を実行する：
  ```bash
  python -m kabusys.validate_config
  ```

- 本番モード（live）での注意点：
  - validate_config は live での不足設定（LINE トークン等）を警告します。
  - KILL_FLAG_CLEAR_ON_START=1 は本番では危険（自動で kill flag をクリアして起動してしまうため）。

---

## 参考・次のステップ

- 本番実装では KabuStationClient（kabu_client.py）を使えるよう環境整備が必要（kabuステーションのインストール・起動）。
- モニタリングやアラート連携（LINE）を有効化する場合は LINE の設定値を .env に入れてください。
- DuckDB にシグナルや portfolio_targets のテーブルを用意し、ExecutionEngine が読むシグナルを投入してください。

---

この README はコードベースの主要箇所を元に作成しています。より詳細な API 仕様や実行フローの理解は各モジュールの docstring を参照してください。必要があれば追加で開発者向けドキュメント（アーキテクチャ図、シーケンス図、API 仕様）を作成します。