# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ/実行スクリプト群）

このリポジトリは、kabuステーション等のブローカー API と連携する日本株自動売買システムの主要コンポーネントを含みます。実行環境（development / paper_trading / live）に応じてモッククライアントや実クライアントを切り替え、発注エンジン、リスクガード、リコンシリエーション、監視ループ、カレンダー管理、ニュース収集などの機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- 環境変数 / .env 管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（必要に応じて自動ロード無効化可）
  - Settings クラスを通じた型付きアクセス

- 環境設定ウィザード
  - `kabusys.config_setup` による対話式 `.env` 生成・更新

- 設定検証 CLI
  - `.env` と `config/*.yaml` を起動前にチェック（`kabusys.validate_config`）
  - `--strict` オプションで警告も FAIL 扱いに

- 実行エンジン（Execution）
  - シグナルに基づく発注フロー（ExecutionEngine）
  - OrderRecord による状態遷移管理
  - OrderRepository（SQLite）による永続化
  - OrderManager による発注・同期・キャンセル処理
  - RiskManager による 3 段階リスクガード（Gate1/2/3）
  - Reconciler による再起動時の復旧（OrderSent の同期、ポジション照合）
  - Broker クライアント:
    - MockBrokerClient（paper_trading / development 向け）
    - KabuStationClient（kabuステーション REST API 実装）

- 監視ループ（Monitoring）
  - SystemMonitor をポーリング実行（SQLite / DuckDB へログ保存）

- データ関連
  - カレンダー管理（JPX カレンダー用ロジック、next_trading_day など）
  - ニュース収集（RSS 取得・正規化・保存ロジック）

---

## 必要条件（環境）

- Python 3.10 以上（型注釈や union 型記法に依存）
- pip でインストール可能な以下ライブラリ（最低限の例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML のパース検証に使用、任意）
- SQLite（標準ライブラリの sqlite3 を使用）

インストール例（仮の requirements）:
```
python -m pip install duckdb httpx websocket-client defusedxml PyYAML
```

※ 実運用では依存関係を requirements.txt / pyproject.toml にまとめてインストールしてください。

---

## セットアップ手順（ローカルでの初回セットアップ）

1. リポジトリをクローンし、Python 環境を用意する
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install duckdb httpx websocket-client defusedxml PyYAML
   ```

2. .env を生成（対話式ウィザード）
   ```
   PYTHONPATH=src python -m kabusys.config_setup
   ```
   - あるいは Python パスを通して `python -m kabusys.config_setup --env-file /path/to/.env` で任意の場所に保存可能

3. 設定の検証
   ```
   PYTHONPATH=src python -m kabusys.validate_config
   # 警告を FAIL にしたい場合
   PYTHONPATH=src python -m kabusys.validate_config --strict
   ```
   必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   その他利用可能な環境変数（例）
   - KABUSYS_ENV (development | paper_trading | live)
   - DUCKDB_PATH (例: data/kabusys.duckdb)
   - SQLITE_PATH (例: data/monitoring.db)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - KABU_API_BASE_URL
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID

4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（実行例）

- 監視ループを起動する
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 停止するにはプロセス終了、またはリポジトリルートの `data/stop_requested.flag` を作成すると検知して終了します

- 発注エンジンを起動する（Execution）
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、paper trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離します
  - 起動時に `data/stop_requested.flag` が存在する場合は起動を行わず終了します
  - `kill.flag`（設定で指定されたパス）による起動制御や、`KILL_FLAG_CLEAR_ON_START` による自動クリア設定があります

- 設定ウィザード（再掲）
  ```
  PYTHONPATH=src python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```
  PYTHONPATH=src python -m kabusys.validate_config [--strict]
  ```

注意: 上記コマンドはリポジトリルートから `PYTHONPATH=src` を付けて実行するか、`pip install -e .` 等でパッケージをインストールした後に実行してください。

---

## 重要な運用上の注意

- 本番モード（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は `live` モードを設定すると警告を出します（LINE 通知設定や kill flag の自動クリアに関するチェックなど）。
- `.env` ファイルは絶対にリポジトリにコミットしないでください（config_setup にもその旨の注意文を出力しています）。
- ExecutionEngine の PID / kill flag / stop flag の運用方法に従い、プロセス管理を行ってください。
- ブローカークライアント（KabuStationClient）はローカルで kabuステーションアプリが稼働していることが前提です。テスト時は paper_trading / development を使用して MockBrokerClient を利用してください。

---

## ディレクトリ構成（主なファイルと役割）

（src/kabusys 以下を想定）

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数 / .env 自動読み込み、Settings クラス（型付きアクセス、バリデーション）

- config_setup.py
  - .env 対話式ウィザード（生成/更新スクリプト）

- validate_config.py
  - 起動前の設定検証 CLI（必須/任意環境変数、config/*.yaml の存在・パース検証）

- run_execution.py
  - ExecutionEngine を起動するスクリプト（プロセス優先度設定、DB 初期化、スレッド管理）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - broker_api.py
    - BrokerAPIProtocol（Protocol）、データモデル（OrderRequest 等）、例外、ファクトリ
  - kabu_client.py
    - KabuStationClient（kabuステーション REST 実装）
  - mock_client.py
    - MockBrokerClient（テスト用）
  - broker_factory.py
    - Settings に応じたブローカークライアント生成
  - order_record.py
    - OrderRecord データモデルと状態遷移ロジック（純粋ビジネスロジック）
  - order_repository.py
    - SQLite を用いた永続化層（orders テーブル、インデックス、CRUD）
  - order_manager.py
    - OrderRecord と OrderRepository を利用した外向き API（作成・送信・同期・キャンセル）
  - execution_engine.py
    - ExecutionEngine（シグナル処理、WebSocket push ドレイン、kill switch 等）
  - reconciler.py
    - 起動時リコンシリエーション（OrderSent の同期、ポジション差分検知）
  - risk_manager.py
    - 3 段階（Gate1/2/3）のリスクガードとサーキットブレーカー、レート制御

- data/
  - calendar_management.py
    - JPX カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - news_collector.py
    - RSS 収集・前処理・保存ロジック（SSRF/サイズ制限対策など）
  - jquants_client.py (参照あり)
    - J-Quants API クライアント（カレンダー取得等に使用）

- monitoring/
  - monitoring_db.py (参照あり)
  - system_monitor.py (参照あり)
  - など監視関連の実装

- utils/
  - logging_setup.py（ログ設定）
  - process_priority.py（プロセス優先度設定）

---

## 開発者向けメモ

- テスト実行や CI では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動 .env 読み込みを無効化できます。
- MockBrokerClient は fill_mode オプション（instant / partial / never / reject）を持ち、テストの挙動を細かく制御できます。
- OrderManager の send_order はクラッシュ安全性を考慮した 2 相永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted）を設計しています。Reconciler はクラッシュ後の回復に対応します。

---

README の内容や補足ドキュメント（API 仕様書、DataPlatform.md 等）は随時追加してください。必要であれば各モジュールの詳細なドキュメント（関数・クラスの使い方、サンプルコード）も作成できます。