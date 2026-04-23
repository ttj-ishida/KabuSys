# KabuSys

日本株自動売買システムの一部（設定管理・実行/監視ランナー・実行層のコアコンポーネント群）。

このリポジトリは、kabuステーション（またはモック）経由で発注を行う ExecutionEngine、起動時のリコンシリエーション、監視ジョブ、ニュース収集やマーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

- 環境変数／`.env` による設定管理（自動ロード機能あり）
- 対話式の `.env` 作成ウィザード（config_setup）
- 起動前設定検証 CLI（validate_config）
- 発注エンジン（ExecutionEngine）とその関連コンポーネント（OrderManager, RiskManager, Reconciler 等）
- モニタリング用ポーリングループ（run_monitoring）
- Paper trading 用の Mock ブローカークライアントを提供（開発/テスト向け）
- DuckDB / SQLite を用いたデータ保存・分析基盤との統合

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先）
  - `python -m kabusys.config_setup` による対話式 `.env` ウィザード
  - `python -m kabusys.validate_config` による設定事前チェック（--strict あり）
- 実行エンジン
  - Signal Queue からの発注ループ（シグナルフェーズ・WebSocket ドレインフェーズ）
  - Order 状態管理（OrderRecord の状態遷移検証）
  - 発注のクラッシュ安全性（2段階永続化など）
  - リスクガード（Gate1: シグナル/ポジション、Gate2: レート制限/CB、Gate3: ドローダウン）
  - リコンシリエーション（起動時に OrderSent をブローカと突合）
- ブローカークライアント
  - MockBrokerClient（fill_mode: instant/partial/never/reject）
  - KabuStationClient（kabuステーション REST API 実装、httpx + websocket）
- データ／ユーティリティ
  - DuckDB を用いたカレンダー/シグナル/ポートフォリオ連携
  - ニュース収集（RSS）モジュール（SSRF・XML攻撃対策を含む）
  - 監視ループ（SQLite を使用）

---

## 要件（推奨）

- Python 3.10 以上（`|` 型などの構文を使用）
- 推奨パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証に使用。未インストールでも実行は可能）
  - その他（標準ライブラリに含まれる sqlite3 等）

（実際の依存はプロジェクトの requirements.txt があればそちらを参照してください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（例）:
   ```
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```

3. `.env` を作成します（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは `.env`（デフォルト）に各種設定を書き込みます。作成後に必ず設定検証を行ってください。

4. 設定検証を行います:
   ```
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化（orders / monitoring 等のテーブルを作成）  
   例えば、orders テーブルと監視DBの初期化を手動で行う場合:
   ```
   python - <<'PY'
   import sqlite3, duckdb
   from kabusys.execution.order_repository import init_orders_db
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   # paths は .env の DUCKDB_PATH / SQLITE_PATH に合わせて変更
   sqlite_conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(sqlite_conn)
   duckdb_conn = duckdb.connect("data/kabusys.duckdb")
   # orders テーブルは Execution 側で使う SQLite（init_orders_db は SQLite 接続を受け取る）
   # 例: Execution が使用する SQLite（paper/trade によりパスが分かれる点に注意）
   sqlite_conn.close()
   duckdb_conn.close()
   PY
   ```
   （monitoring_db のモジュールは本リポジトリ内に存在します。スクリプトを適宜調整してください）

6. 実行:
   - ExecutionEngine（発注エンジン）を起動:
     ```
     python -m kabusys.run_execution
     ```
     - KABUSYS_ENV が `paper_trading` もしくは `development` であれば MockBrokerClient が使われます。
     - `paper_trading` の場合は Paper 用 SQLite（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
   - Monitoring（監視ループ）を起動:
     ```
     python -m kabusys.run_monitoring
     ```
     - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能。

---

## 環境変数（主要）

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルト値ありやオプション）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - live は本番モード（validate_config は警告などを追加）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB のパス、デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- PAPER_FILL_MODE — paper_trading の挙動（instant | partial | never | reject）

自動読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動読み込みします。
- OS 環境変数が優先されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表的なコマンド）

- 環境ウィザード（対話式）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 発注エンジン（Execution）起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を 30 秒にする例:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 開発用モッククライアントの利用:
  - `KABUSYS_ENV=paper_trading` または `development` で起動すれば、自動的に MockBrokerClient が使われます（`PAPER_FILL_MODE`で挙動を制御）。

---

## config/*.yaml

実行時に参照する設定ファイル（存在しない場合は警告）:
- config/system_config.yaml
- config/data_config.yaml
- config/strategy_config.yaml
- config/risk_config.yaml
- config/execution_config.yaml
- config/monitoring_config.yaml

validate_config は PyYAML があれば YAML のパース検証も行います。見つからないファイルは警告になります（生成スクリプトがある場合はそちらで生成可能）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリのルートに `src/kabusys` 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                    — Settings, .env 自動ロードロジック
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 起動前構成検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py              — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py          — Settings に応じたクライアント生成
    - kabu_client.py             — kabu station 実装（httpx + websocket）
    - mock_client.py             — テスト用モック実装
    - order_record.py            — Order 状態/遷移ロジック（ビジネスロジック）
    - order_repository.py        — SQLite を使った永続化層
    - order_manager.py           — 発注フローの上位 API（作成/送信/同期/取消）
    - execution_engine.py        — ExecutionEngine 本体（セッション管理）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — Gate1/2/3 リスクガード
    - ...（その他）
  - data/
    - calendar_management.py     — マーケットカレンダー管理（DuckDB）
    - news_collector.py          — RSS ニュース収集（defusedxml 等対策含む）
    - ...（その他）
  - monitoring/
    - monitoring_db.py           — 監視用 SQLite 初期化/API（参照用）
    - system_monitor.py          — 監視ループ用のロジック
  - utils/
    - logging_setup.py           — ログ初期化ユーティリティ
    - process_priority.py        — プロセス優先度設定ユーティリティ
  - scripts/
    - generate_config.py         — config/*.yaml のテンプレート生成スクリプト（ある場合）

---

## 運用上の注意

- KABUSYS_ENV=live の場合は本番扱いになります。validate_config は live のときに追加の警告を出します。LINE トークン未設定や KILL_FLAG_CLEAR_ON_START=1 など本番で危険な設定は確認してください。
- kill.flag / stop_requested.flag による外部停止を検知します。これらファイルは data/ 以下に配置されます（デフォルト）。
- Paper trading（`paper_trading`）は内部で MockBrokerClient を用いるため、本番ブローカにアクセスしません。Paper 用 DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に分離されます。
- .env は絶対に Git にコミットしないでください（config_setup でも同ドキュメントに注意書きあり）。
- 実際の本番ブローカ実装（KabuStationClient の live 使用）は未実装/注意事項あり。BrokerClientFactory は live で NotImplementedError を出す実装になっています。

---

## 参考（例 .env の最小例）

```
# 実行環境
KABUSYS_ENV=development

# API / 認証
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# ログ
LOG_LEVEL=INFO

# Paper trading
PAPER_FILL_MODE=instant
```

---

質問や追加ドキュメント（例: データベーススキーマ、config/*.yaml の中身、運用手順など）が必要であれば教えてください。必要に応じて README を拡張します。