# KabuSys

日本株向け自動売買プラットフォーム (プロトタイプ)

このリポジトリは、シグナルに基づく発注・監視・リコンシリエーション等を行う小規模な自動売買システムのコア実装を含みます。実装はモジュール化されており、実器環境（kabuステーション）／モック（ペーパートレード／開発）を切り替えて動作させられます。

Version: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要な依存パッケージ
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（主要スクリプト）
- 実行時の停止・監視フラグ
- ディレクトリ構成（主なファイル解説）
- トラブルシューティング / 補足

---

## プロジェクト概要

KabuSys は以下の要素を含む自動売買エンジンです。

- シグナル取得（DuckDB の signals テーブル想定） → 発注（ExecutionEngine）
- 発注の状態管理（OrderRecord / OrderRepository）
- ブローカークライアント抽象化（kabuステーション実装 / Mock 実装）
- リスク管理（3段階のゲート）
- 起動時リコンシリエーション（OrderSent 状態の突合）
- 監視ループ（SystemMonitor を用いたポーリング）
- 環境設定の対話ウィザードと設定検証ツール

設計方針として DB（SQLite / DuckDB）と API クライアント層を分離し、テストしやすいモックを用意している点が特徴です。

---

## 主な機能

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の作成・更新をインタラクティブに支援
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数・config/*.yaml・各種パスなど起動前チェック
  - --strict オプションで警告も失敗扱いにできる
- 発注エンジン（python -m kabusys.run_execution）
  - Signal Queue Pull 型の実行エンジン
  - Paper trading（モック）対応（設定により本番/ペーパーを切替）
- 監視プロセス（python -m kabusys.run_monitoring）
  - SystemMonitor を定期ポーリングして監視データを記録
- ブローカー抽象化
  - MockBrokerClient（テスト用） / KabuStationClient（kabuステーション用）
- リコンシリエーション（起動時に OrderSent を突合）
- カレンダー管理、ニュース収集などのデータ処理ユーティリティ

---

## 必要な依存パッケージ

（プロジェクトに requirements.txt がない場合は以下を目安にインストールしてください）

- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config YAML のパース検証を行う場合、インストールが推奨）
- （標準ライブラリ）sqlite3, logging, threading など

例:
```
pip install duckdb httpx websocket-client defusedxml pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要なパッケージをインストール
   ```
   pip install -r requirements.txt     # (ある場合)
   # または
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```
4. .env を作成
   - 対話ウィザードで作成する:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作成する（サンプルは次節参照）。

5. 設定を検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（.env）と設定

自動ロード:
- プロジェクトルート（.git または pyproject.toml がある階層）を自動検出し、`.env` を読み込みます。
- OS 環境変数 > .env.local > .env の順で優先度があります。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 推奨環境変数（抜粋）:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知設定（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" or "1"、デフォルト 0）

重要なパス（デフォルト）:
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid (PID ファイル)
- data/kill.flag, data/stop_requested.flag （停止制御に使用）

サンプル (.env) — config_setup により自動生成されますが、参考:
```
JQUANTS_REFRESH_TOKEN=your_value
KABU_API_PASSWORD=your_value
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
# LINE_CHANNEL_ACCESS_TOKEN=...
# LINE_USER_ID=...
```

---

## 使い方（主要スクリプト）

- 環境ウィザード（.env の作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # 警告を FAIL として扱う:
  python -m kabusys.validate_config --strict
  ```

- Execution Engine（発注処理）起動
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - KABUSYS_ENV により動作が変わる（paper_trading または development は MockBrokerClient を使用）
  - paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録し、本番 DB と分離
  - 起動時に PID ファイルを書き込み、`data/stop_requested.flag` を置くことで外部から停止を要求可能
  - kill.flag（`KILL_FLAG_PATH`, デフォルト data/kill.flag）による Kill Switch を実装

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - モニターは `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を設定（秒、デフォルト 60）
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）

- 設定ファイル（config/*.yaml）の生成
  - validate_config は config 配下の YAML 存在とパースをチェックします。ファイルがない場合は警告を出します。
  - 本プロジェクトでは `scripts/generate_config.py` で生成可能（リポジトリにスクリプトがある想定。存在しない場合は手動で配置してください）。

---

## 実行時の停止・監視フラグ

- 停止リクエスト: プロセスはプロジェクトルートの `data/stop_requested.flag` の存在を監視しています。ファイルを作成するとループは検知して安全に停止します。
- Kill Switch: `data/kill.flag`（デフォルトパスは設定で変えられます）を検出すると、ExecutionEngine は全 active 注文をキャンセルし稼働を終了します。`KILL_FLAG_CLEAR_ON_START=1` を .env に設定すると、起動時に既存の kill.flag を自動でクリアして起動します（本番では推奨されません）。
- PID ファイル: 実行時に PID を `data/execution.pid` 等に書き出します。終了時に削除されます。

---

## ディレクトリ構成（主なファイル・モジュール）

プロジェクトルート（src/kabusys）を中心に:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（設定アクセス）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine のエントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - execution/
    - broker_api.py
      - BrokerAPIProtocol, データモデル, factory
    - mock_client.py
      - テスト用 MockBrokerClient
    - kabu_client.py
      - kabuステーション向け HTTP / WebSocket 実装
    - broker_factory.py
      - Settings に基づくクライアント生成
    - order_record.py
      - Order の状態モデルと遷移ロジック
    - order_repository.py
      - SQLite を使った永続化層
    - order_manager.py
      - OrderRecord と OrderRepository をつなぐ発注 API
    - execution_engine.py
      - ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py
      - 起動時のリコンシリエーション
    - risk_manager.py
      - Gate 1/2/3 によるリスク統制
  - data/
    - calendar_management.py
    - news_collector.py
    - jquants_client.py (参照される想定)
  - monitoring/
    - monitoring_db.py (監視DB 初期化等を想定)
    - system_monitor.py (SystemMonitor 実装を想定)
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルのみ抜粋。リポジトリの実際のファイル構成に合わせて参照してください）

---

## トラブルシューティング / 補足

- validate_config が YAML のパース検証を行うには PyYAML が必要です。インストールしていない場合、YAML 検証はスキップされますが警告が表示されます。
- 実機 kubuステーション を使う場合は KABU_API_PASSWORD と（必要に応じて）KABU_API_BASE_URL を正しく設定してください。デフォルトではローカルの kabusapi を想定しています（ http://localhost:18080/kabusapi ）。
- ペーパートレード時は settings.paper_fill_mode（instant / partial / never / reject）で挙動を制御できます。
- DB 親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、validate_config は親ディレクトリの存在を警告します。
- 起動後に発生した不整合（OrderSent のまま等）は Reconciler が復旧できるように設計されていますが、環境によっては手動確認が必要になることがあります。

---

この README はコードベースの主要な使い方と設定を簡潔にまとめたものです。実際の運用・デプロイ前に必ず設定検証（python -m kabusys.validate_config）を実行し、KABUSYS_ENV=live を使用する際は特に注意して設定を確認してください。