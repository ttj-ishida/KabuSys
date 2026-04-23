# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
このリポジトリは発注エンジン、リスク管理、モニタリング、カレンダー・データ処理、ニュース収集などのコンポーネントを含みます。設計は実運用を想定しており、クラッシュ耐性（2相永続化、起動時リコンシリエーション）や複数段階のリスクガードを備えています。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定ウィザード（.env の対話式生成／更新）
- 起動前設定検証ツール（.env と config/*.yaml の存在・妥当性確認）
- ExecutionEngine（シグナルに基づく発注処理）
  - 発注の状態管理（OrderRecord）と SQLite 永続化（OrderRepository）
  - 3段階リスクガード（Gate1: シグナル／余力等、Gate2: レート制限／CB、Gate3: ドローダウン）
  - Reconciler によるクラッシュ後の自動復旧（OrderSent の同期、ポジション差分検出）
  - WebSocket push ドレイン / push ハンドリング（kabu station 用）
- Broker クライアント群
  - KabuStationClient（kabu station REST+WebSocket 実装）
  - MockBrokerClient（paper_trading / development 用のモック）
  - create_broker_api ファクトリ
- 監視プロセス（SystemMonitor のポーリングループ）
- データ関連ユーティリティ
  - DuckDB を用いたマーケットカレンダー管理（J-Quants 連携想定）
  - ニュース収集（RSS 取得・前処理・保存）
- ロギング／プロセス優先度等のユーティリティ

---

## 必要環境 / 依存

- Python 3.10 以上（型記法で `X | Y` を使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など
- 推奨インストール例（必須・任意を含む）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml（config/*.yaml 内容の検証に必要。インストールされていない場合は検証をスキップ）
  - その他（プロジェクトで使用するユーティリティに応じて追加）

例:
pip install duckdb httpx websocket-client defusedxml pyyaml

---

## 主な環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意／設定系（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- PAPER_FILL_MODE: paper_trading 用の fill モード（instant, partial, never, reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・制御用）

自動 .env ロード:
- プロジェクトルートの `.env` と `.env.local` を起動時に自動読み込みします（OS 環境変数より低優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がある場合）
   - あるいは必要なパッケージを個別に:
     pip install duckdb httpx websocket-client defusedxml pyyaml

4. .env を作成（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
     - 対話形式で .env を作成・更新します。
     - ウィザード終了後、.env に保存されます。

5. 設定検証
   - python -m kabusys.validate_config
     - --strict をつけると警告もエラー扱いになります（exit code=1）。

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data

7. （オプション）DuckDB/SQLite の初期化は実行時に自動で行われる箇所があります（例: monitoring/start では init_monitoring_db が呼ばれる）。

---

## 使い方（実行コマンド例）

- .env 作成（対話ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、DB は data/paper_trading.db（分離）になります。
  - KABUSYS_ENV=live は現時点では live broker client 実装が未提供（NotImplementedError）。

- ログは環境変数 LOG_LEVEL で制御（例: LOG_LEVEL=DEBUG）

停止制御:
- stop フラグ / kill フラグ
  - 停止指示用のフラグファイル（デフォルト: data/stop_requested.flag, data/kill.flag 等）を使用して外部から停止／キルを制御します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag が自動でクリアされます（本番では推奨しません）。

---

## 注意点 / 運用メモ

- 本番環境（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は live 設定時に追加の警告を出します（LINE 通知設定の確認など）。
- config/*.yaml ファイル検証には PyYAML が必要です。未インストールの場合は警告になり検証がスキップされます。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにもその旨が書かれています）。
- paper_trading モードは MockBrokerClient を使い、本番 DB と分離された SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。
- ExecutionEngine の PID / kill flag ファイルはデフォルトで data/ 配下に作成されます。適切なディレクトリ権限を確保してください。
- Live broker 実装（KabuStationClient）は存在しますが、BrokerClientFactory.create は live を NotImplementedError にしています。実運用での live 対応は実装と検証が必要です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env の自動読み込みと Settings
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

src/kabusys/execution/
- broker_api.py            — Broker API のデータモデル / Protocol / ファクトリ
- kabu_client.py           — KabuStation の REST/WebSocket クライアント
- mock_client.py           — MockBrokerClient（テスト・開発用）
- broker_factory.py        — Settings に応じたブローカーファクトリ
- order_record.py          — 注文状態モデルと遷移ロジック
- order_repository.py      — SQLite を用いた永続化層
- order_manager.py         — OrderRecord と Repository / Broker の統合 API
- execution_engine.py      — ExecutionEngine（シグナル処理 + push ドレイン）
- reconciler.py            — 起動時の注文同期・ポジション照合
- risk_manager.py          — 3段階リスクガード、サーキットブレーカー等

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理（DuckDB, J-Quants 統合）
- news_collector.py        — RSS ニュース収集・前処理

src/kabusys/monitoring/
- monitoring_db.py         — 監視用 SQLite テーブル初期化 / ロギング（参照: run_monitoring）

その他:
- config/                  — YAML 設定ファイル置き場（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）
- data/                    — デフォルトの DB / PID / フラグファイル置き場（例: data/kabusys.duckdb, data/monitoring.db）

---

## 開発 / 貢献

- コードは型注釈・ドキュメント文字列が充実しています。ユニットテストを追加して各コンポーネント（OrderManager, RiskManager, Reconciler 等）を検証することを推奨します。
- .env の自動ロードや .env.local の扱いはテスト環境で影響するため、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って手動で設定を注入してください。

---

問題や実装上の不明点があれば、どの機能について知りたいか教えてください。README の補足やコマンド例、運用チェックリストなども用意できます。