# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、発注エンジン、リスクガード、ブローカークライアント（モック含む）、監視・リコンシリエーション機能、マーケットカレンダー管理やニュース収集などを含む自動売買プラットフォームの主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- シグナルに基づく発注エンジン（ExecutionEngine）
  - シグナル取得 → Gate1/2 のリスクチェック → 発注 → push ドレイン
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
  - SQLite に永続化し、状態遷移を厳格に管理
- ブローカークライアント層
  - KabuStationClient（kabuステーション REST 実装）
  - MockBrokerClient（paper_trading / 開発用）
  - create_broker_api ファクトリで切り替え
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視 → kill_switch）
- 起動時リコンシリエーション（Reconciler）
  - OrderSent 状態の注文をブローカーと突合し状態回復
- 監視プロセス（run_monitoring）
  - 定期的に SystemMonitor を実行しメトリクスを保存
- 設定管理 / ウィザード / 検証ツール
  - .env をウィザードで生成（config_setup）
  - 起動前に .env や config/*.yaml を検証（validate_config）
- データ処理モジュール
  - マーケットカレンダー管理（calendar_management）
  - RSS ニュース収集（news_collector）

---

## 主な機能一覧

- ExecutionEngine: シグナルプル＆push ドレインによる発注セッション管理
- OrderManager / OrderRepository: 注文生成・送信・同期・取消
- Reconciler: 再起動後の自動同期とポジション差分検出
- RiskManager: 3段階のリスクガード（Gate1/2/3）
- Broker クライアント: 実クライアント（KabuStationClient）と Mock 実装
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視ループ: python -m kabusys.run_monitoring
- 実行ループ: python -m kabusys.run_execution

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈に `|` 形式のユニオンを使用）
- 推奨パッケージ（実行に応じて必要なものをインストール）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証を行う場合）
- 組み込み DB: sqlite3 は標準ライブラリ
- ネットワーク接続（kabuステーション と連携する場合）

requirements.txt の例:
```
duckdb
httpx
websocket-client
defusedxml
PyYAML  # オプション（YAML 検証用）
```

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトを取得）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール
   ```
   pip install -r requirements.txt
   ```

4. 初期設定ファイル `.env` を生成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 既存の `.env` があれば読み込まれ、Enter で既存値を再利用できます。
   - ウィザード実行後、`.env` に保存します。

5. 設定検証（起動前の確認）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱いにする
   ```

---

## 環境変数（.env）

自動ロード順序: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

必須（validate_config でチェックされる）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション（例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
- KILL_FLAG_CLEAR_ON_START: 0 | 1（本番で 1 は危険）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, run_monitoring で使用）

簡単な .env 例（ウィザードで生成されます）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意:
- `.env` は絶対にリポジトリにコミットしないでください（秘匿情報が含まれるため）。

---

## 使い方（コマンド）

- 設定ウィザード（.env の作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env / config/*.yaml のチェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（発注セッション）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用（paper_trading 用 SQLite に記録）
  - 停止フラグ: リポジトリルートの data/stop_requested.flag を作成すると停止検知します
  - PID ファイル: data/execution.pid（設定で変更可）

- 監視ループ（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視 DB は設定に従い sqlite_path を使用

- 直接ライブラリを使った組み合わせ
  - create_broker_api(mock=True, fill_mode=...)
  - ExecutionEngine のテストでは _process_signals() / _drain_push_queue() を直接呼べます

---

## 主要コンポーネント（簡単な説明）

- config.Settings
  - 環境変数からアプリ設定を取得。必須値未設定時は例外を投げる。
  - 自動でプロジェクトルートの `.env` / `.env.local` をロード（無効化可能）

- ExecutionEngine
  - シグナル読み込み → Gate1/2 を経て発注 → WebSocket push を drain
  - セッション管理（開始・終了）、kill_switch の実装

- OrderRecord / OrderRepository / OrderManager
  - OrderRecord: 状態遷移ロジック（検証付き）
  - OrderRepository: SQLite に対する永続化層（init_orders_db でテーブル作成）
  - OrderManager: 作成・送信・同期・キャンセルの高レベル API

- RiskManager
  - Gate1: シグナル単位のチェック（余力・重複・ポジション上限）
  - Gate2: レート制限 & サーキットブレーカー
  - Gate3: ドローダウン監視（kill_switch 発動）

- Reconciler
  - 起動時に OrderSent の注文を照合して DB とブローカーの状態を整合させる
  - ポジション差分検出をログ出力

- Broker クライアント
  - KabuStationClient: kabuステーション REST API／WebSocket 実装（httpx / websocket-client）
  - MockBrokerClient: テスト用。fill_mode による挙動を再現

- data.calendar_management
  - DuckDB を使った市場カレンダー管理（J-Quants から差分取得する想定）

- data.news_collector
  - RSS からニュース収集 → 前処理 → DuckDB へ冪等保存（SSRF / XML 攻撃対策あり）

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み取り・Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - execution/
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - execution_engine.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - reconciler.py
      - risk_manager.py
      - ...（他）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照される想定)
    - utils/
      - logging_setup.py
      - process_priority.py
    - config/                   — YAML 設定ファイル群（system_config.yaml 等）
- pyproject.toml (プロジェクトルート検出用)
- .env.example (存在する場合)

config/*.yaml のファイル名（validate_config で確認）
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では LINE 通知などアラート設定を必ず確認してください。validate_config は live 環境での注意点を警告します。
- KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（起動時に kill.flag を自動クリアしてしまう）。
- .env は機密情報を含むため決して Git にコミットしないでください。
- Paper trading（paper_trading）モードでは MockBrokerClient を使用し、本番 DB と分離した paper_trading 用 SQLite に記録します。
- Python のバージョン制約に注意（3.10 以上推奨）。

---

## 開発者向けメモ

- 自動ロードを無効化したいテストでは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップしますが、ファイル存在は警告します。
- ExecutionEngine や Reconciler のテストは MockBrokerClient を使うとネットワーク不要で再現可能です。

---

ご不明点や追加したいドキュメント（API仕様、データベーススキーマ、運用手順など）があれば教えてください。README に追記します。