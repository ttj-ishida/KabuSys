# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリは、シグナルに基づく発注エンジン（ExecutionEngine）、リスクガード、リコンシリエーション、監視ループ、データ収集ユーティリティなどを含みます。

---

## プロジェクト概要

KabuSys は次の責務を持つコンポーネント群で構成されています。

- 発注フロー（ExecutionEngine）: シグナル取得 → Gate1/2（リスクチェック） → 発注 → push/drain で状態同期
- ブローカークライアント層: 実ブローカー（kabu station）とモック（MockBrokerClient）を切り替え可能
- 注文永続化（SQLite）: 注文の保存・更新・照合を安全に行う
- リコンシリエーション: 再起動・クラッシュ時に未確定注文をブローカーと突合して復旧
- 監視（SystemMonitor）: システムリソースや監視イベントの記録（sqlite / duckdb）
- データユーティリティ: マーケットカレンダー管理、RSS ニュース収集など
- 環境設定ウィザード / 設定検証ツール: .env 作成補助および起動前の検証

設計上、DB（SQLite / DuckDB）や broker API 呼び出しは明確に分離され、テスト・開発時はモッククライアントを使って本番環境と分離できます。

---

## 主な機能一覧

- 環境設定ウィザード (.env の対話式作成) — `kabusys.config_setup`
- 起動前設定検証（必須環境変数、config/*.yaml、パス等） — `kabusys.validate_config`
- ExecutionEngine（シグナルプル型、WebSocket push ドレイン） — `kabusys.run_execution`
- Monitoring ループ（定期的に SystemMonitor を実行） — `kabusys.run_monitoring`
- Broker クライアントファクトリ（Mock / 実クライアント切替）
- Order state machine（OrderRecord）と永続化（OrderRepository）
- RiskManager（Gate1/2/3：余力・重複・ポジション上限・レート制限・ドローダウン）
- Reconciler（OrderSent レコードの突合・ポジション差分検出）
- Data utilities（market calendar 管理、RSS ニュース収集）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンしてワークディレクトリに入る
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate.bat   # Windows (PowerShell など)
   ```

3. 依存パッケージをインストール  
   （ここでは主要な依存項目を例示します。実プロジェクトでは requirements.txt / pyproject.toml を参照してください）
   ```bash
   pip install duckdb httpx websocket-client defusedxml
   # validate_config が YAML の構文検査を行うには PyYAML が必要
   pip install pyyaml
   ```

4. .env を作成（対話式推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードで入力するとプロジェクトルートに `.env` が作成されます。
   - `.env` はリポジトリにコミットしてはいけません（機密情報が含まれるため）。

5. 必須環境変数を確認
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

※ Settings モジュールは自動で `.env` / `.env.local` を読み込みます（OS の環境変数が優先）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 主要な環境変数（代表例）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト `data/paper_trading.db`）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABU_API_BASE_URL — kabu station API の base URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアする（0/1）

例（.env の一部）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=paper_trading
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（起動フローの一例）

1. .env 作成・更新
   ```
   python -m kabusys.config_setup
   ```

2. 設定検証
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も exit code 1 として扱う
   python -m kabusys.validate_config --strict
   ```

3. 監視ループを起動（バックグラウンド監視）
   ```
   # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
   python -m kabusys.run_monitoring
   ```

   注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

4. 発注エンジンを起動
   ```
   # paper_trading モードで実行する場合（.env で KABUSYS_ENV を設定しておく）
   python -m kabusys.run_execution
   ```

   実行時の挙動:
   - KABUSYS_ENV が `paper_trading` または `development` のときは MockBrokerClient を使用（実ブローカー呼出しは行わない）
   - `live` は現在 NotImplemented（使用不可）。本番は慎重に実装・確認してください。
   - 起動時に kill.flag（デフォルト: data/kill.flag）が存在する場合、`KILL_FLAG_CLEAR_ON_START=1` であれば自動クリア、デフォルト（0）の場合は起動を拒否します。
   - PID ファイル（デフォルト: data/execution.pid）を作成します。停止時に削除されます。

---

## CLI / スクリプト一覧（エントリポイント）

- python -m kabusys.config_setup
  - .env を対話式に作成・更新するウィザード
- python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml の検査。警告・エラーを出力。--strict で警告を FAIL 扱いにする
- python -m kabusys.run_execution
  - ExecutionEngine を起動するメインスクリプト
- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを起動する

---

## ディレクトリ構成（抜粋）

プロジェクトルートの `src/kabusys` 内の主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数の読み込み・Settings
  - config_setup.py            — .env 作成ウィザード（CLI）
  - validate_config.py         — 起動前設定検証（CLI）
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py            — BrokerAPI のデータモデル / Protocol / factory
    - broker_factory.py        — Settings に基づく broker クライアント生成
    - kabu_client.py           — kabu station REST client (httpx)
    - mock_client.py           — MockBrokerClient（テスト用）
    - order_record.py          — Order 状態モデルと遷移ロジック
    - order_repository.py      — SQLite 永続化層
    - order_manager.py         — 発注フロー（OrderManager）
    - execution_engine.py      — ExecutionEngine（シグナル処理 / push drain）
    - reconciler.py            — リコンシリエーション
    - risk_manager.py          — Gate1/2/3 のリスク制御
    - ...（他、order_manager 等）
  - data/
    - calendar_management.py   — マーケットカレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集
    - ...（jquants_client など）
  - monitoring/
    - monitoring_db.py         — 監視 DB 初期化 / ログ用 API
    - system_monitor.py        — SystemMonitor（ポーリング実装）
  - utils/
    - logging_setup.py         — ロギング初期化
    - process_priority.py      — プロセス優先度設定
  - config/                    — YAML 設定ファイル群（system_config.yaml 等）

※ 上は主要ファイルを抜粋したものです。詳細はソースコードを参照してください。

---

## 運用上の注意 / トラブルシューティング

- .env は機密情報を含むため、決して Git にコミットしないでください。
- 起動前に `python -m kabusys.validate_config` を実行して設定の不備を検出してください。
  - PyYAML がインストールされていない場合、config/*.yaml の内容検証はスキップされます（警告が出ます）。
- Monitoring は本番 sqlite path を使う点に注意（環境にかかわらず共有される設計）。
- KABUSYS_ENV=live を設定した場合は、本番向けの警告が出ます。LINE の通知設定などを必ず確認してください。
- ExecutionEngine は kill.flag による安全停止、PID ファイル管理、リコンシリエーションを備えています。運用時はこれらのファイルパスや初期化を正しく設定してください。
- MockBrokerClient には複数の fill_mode（instant / partial / never / reject）があり、テスト用途で挙動を切り替えられます。

---

## 開発のヒント

- Settings はプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` を自動読み込みします。テストで自動読み込みを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ExecutionEngine のシグナル処理 / push ドレインは個別に呼び出せるため、ユニットテストでは直接 `_process_signals()` / `_drain_push_queue()` を呼んで挙動検証ができます。
- broker_api.create_broker_api(mock=True, ...) でモックを得られるため、統合テスト時は実ブローカーに依存せずにシミュレーションできます。

---

必要に応じて README に追記します。以下が欲しい場合は教えてください：
- インストール用 requirements の具体的な候補（requirements.txt 生成）
- .env.example のサンプル全文
- 実行時のログ出力例 / validate_config のサンプル出力
- 各モジュール（ExecutionEngine / RiskManager / Reconciler 等）の詳細設計ドキュメント