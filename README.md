# KabuSys

日本株向け自動売買システム（開発中 / プロトタイプ）

このリポジトリは「KabuSys」と呼ばれる日本株自動売買フレームワークの実装です。発注エンジン、監視ループ、リスク管理、ブローカー API 抽象化、カレンダー管理、ニュース収集など、実運用を想定したコンポーネント群を含みます。

## 主な特徴
- 環境設定ウィザード（.env 作成支援）
- 設定検証 CLI（.env と config/*.yaml の存在／パースチェック）
- ExecutionEngine：シグナル駆動の発注エンジン（発注／WebSocket push 処理／kill switch）
- Broker API 抽象化（実ブローカー / Mock 両対応）
- Order の状態遷移を定義した OrderRecord（状態機械）と SQLite 永続化層
- RiskManager：Gate1〜3 の三段階リスクガード（重複・余力・ポジション上限、レート制限・CB、ドローダウン）
- Reconciler：OrderSent 状態の復旧とポジション差分照合（リコンシリエーション）
- Monitoring：監視ループ（SQLite + DuckDB を使用）
- Data コンポーネント：マーケットカレンダー管理（J-Quants ベース）、ニュース収集（RSS）
- 複数環境対応：development / paper_trading / live（paper_trading では MockBroker を使用し本番 DB と分離）

## 必須・推奨依存関係
（プロジェクト配布時に requirements.txt を用意する想定ですが、ここでは主要パッケージを列挙します）
- Python 3.10+
- duckdb
- httpx
- websocket-client
- defusedxml
- pyyaml（config/*.yaml のパース検証を有効にする場合）
- その他：標準ライブラリ（sqlite3, logging 等）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
```

## セットアップ手順

1. リポジトリをチェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは既存の .env を読み込み、各項目を順に確認・入力します。重要な項目（J-Quants トークン、kabu API パスワード等）を必ず設定してください。
   注意: .env は絶対に Git にコミットしないでください（ウィザードも注意喚起を出します）。

4. 設定検証
   - 通常モード（エラーがあれば exit 1）
     ```
     python -m kabusys.validate_config
     ```
   - 厳格モード（警告も失敗と扱う）
     ```
     python -m kabusys.validate_config --strict
     ```

5. DB 初期化（必要に応じて）
   - orders テーブル等は Execution 起動時やスクリプト内部で初期化される想定ですが、手動で初期化することもできます。例（監視 DB を初期化）:
     ```
     python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"
     ```
     orders テーブル初期化例:
     ```
     python -c "import sqlite3; from kabusys.execution.order_repository import init_orders_db; conn=sqlite3.connect('data/monitoring.db'); init_orders_db(conn); conn.close()"
     ```
   - 実行スクリプト（run_execution/run_monitoring）は必要に応じて DB テーブルを生成します。

## 使い方

- 環境ファイル作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（当日のセッションを実行）
  ```
  python -m kabusys.run_execution
  ```
  動作モード:
  - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient を使用します（paper_trading では paper_trading 用の SQLite を使用）。
  - KILL フラグや PID ファイル、停止フラグ（data/stop_requested.flag / kill.flag）に対応しています。

- 監視ループ
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書きできます。

- プログラムから利用する（例）
  ```python
  from kabusys.config import settings
  from kabusys.execution import create_broker_api, ExecutionEngine, EngineConfig

  broker = create_broker_api(mock=True, fill_mode=settings.paper_fill_mode)
  # ExecutionEngine の構築と run_session の呼び出しは実装に合わせて行います
  ```

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABU_API_BASE_URL — kabu station API ベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア (0/1)
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）

安全上の注意:
- .env を誤ってコミットしないこと
- KABUSYS_ENV=live 設定時は設定・通知先を慎重に確認してください（validate_config が警告を出します）

## 重要コンポーネント概要（主要ファイル）
- kabusys/config.py
  - .env 自動ロード、Settings クラス（環境変数アクセスラッパ）
- kabusys/config_setup.py
  - .env 作成対話ウィザード
- kabusys/validate_config.py
  - 起動前の設定検証 CLI
- kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（本番・ペーパー両対応）
- kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- kabusys/execution/*
  - broker_api.py: Broker API の Protocol / データモデル / 例外 / ファクトリ
  - kabu_client.py: kabuステーション用の実装（httpx + websocket）
  - mock_client.py: テスト用 MockBrokerClient
  - order_record.py: 注文状態遷移モデル
  - order_repository.py: SQLite 永続化（orders テーブル）
  - order_manager.py: 外向き API（作成・送信・同期・キャンセル）
  - execution_engine.py: セッション実行ロジック（シグナル処理 / push ドレイン）
  - reconciler.py: 再起動時のリコンシリエーション
  - risk_manager.py: Gate1〜3 リスクガード
  - broker_factory.py: 設定に応じたクライアント生成
- kabusys/data/*
  - calendar_management.py: マーケットカレンダー（J-Quants ベース）
  - news_collector.py: RSS ニュース収集（前処理/保存ロジック）
- kabusys/monitoring/*
  - 監視 DB 初期化や SystemMonitor 実装（run_monitoring で使用）
- utils（logging_setup, process_priority 等）
  - ロギング設定やプロセス優先度制御のユーティリティ

## ディレクトリ構成（抜粋）
プロジェクトルートの src/kabusys 配下を抜粋して示します。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - broker_api.py
      - kabu_client.py
      - mock_client.py
      - broker_factory.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - ...（その他実行関連）
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照実装)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - ...（その他）

## 運用上の注意
- 本システムは取引を行うため、本番環境（KABUSYS_ENV=live）での運用は十分なテストと運用準備が必要です。LINE 通知や kill flag の設定を必ず確認してください。
- .env にシークレット情報（API トークン・パスワード）を保存します。漏洩に注意し、リポジトリには絶対にコミットしないでください。
- paper_trading モードは実取引を行わないため開発／検証に利用してください。paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

---

この README はコードベースの主要点をまとめた概要です。より詳しい設計や API の使用方法は各モジュールの docstring・ソースコードをご参照ください。必要であれば README にセットアップ例（systemd ユニットや docker-compose）や開発フローを追記できます。希望があれば教えてください。