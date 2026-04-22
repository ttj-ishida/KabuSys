KabuSys
=======

日本株自動売買システムのコア実装（サンプル/プロトタイプ）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視ループ（SystemMonitor）、ブローカークライアント（kabu station / Mock）、データユーティリティ（マーケットカレンダー、ニュース収集）などを含みます。設計は本番運用を意識した安全性（リコンシリエーション、Kill Switch、リスクガード、レート制限等）を備えています。

主な特徴
--------
- .env 対話式ウィザード（kabuys.config_setup）で初期設定を簡単に作成
- 起動前に .env と config/*.yaml を検証する CLI（kabusys.validate_config）
- 発注ロジックを持つ ExecutionEngine（Signal Pull 型）
  - Gate1/2/3 による 3 段階リスクガード（余力、重複、ポジション上限、レート制限、ドローダウン等）
  - MockBrokerClient によるペーパートレードサポート
  - リコンシリエーション（再起動後の注文同期とポジション照合）
- SystemMonitor（監視）と監視用 DB 初期化
- ブローカークライアント実装（KabuStationClient：httpx / websocket-client 使用）
- データユーティリティ：市場カレンダー管理、RSS ニュース収集（安全処理を考慮）
- DB 永続化：SQLite（監視・注文履歴）／DuckDB（分析・シグナル格納）

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈や union 型 `X | Y` を使用）
- git, pip 等

推奨パッケージ（最低限）
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config YAML のパース検証に使用、未インストールでも実行可）

例: 仮想環境作成と依存パッケージのインストール
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb httpx websocket-client defusedxml PyYAML
```

リポジトリのクローン
```
git clone <repo-url>
cd <repo-root>
```

初期設定 (.env) の作成
```
python -m kabusys.config_setup
```
対話形式で .env を生成します。生成後は必ず .env を Git にコミットしないでください。

設定の検証
```
python -m kabusys.validate_config
# 警告もエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

DB の初期化
- monitoring/run scripts や execution/run が起動時に必要なテーブルを作成します（init_monitoring_db、init_orders_db など）。
- data ディレクトリは書き込み可能にしてください（デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db）。

主要な実行コマンド
------------------

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution エンジン起動（本番/ペーパーの判定は KABUSYS_ENV）
  ```
  python -m kabusys.run_execution
  ```
  KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、ペーパートレード用の SQLite（デフォルト: data/paper_trading.db）に記録します。`development` でも mock を使用します。`live` は現在未実装（BrokerClientFactory で NotImplementedError）。

- Monitoring ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL （秒）で上書き可能（デフォルト 60）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

停止方法
- 実行中プロセスは data/stop_requested.flag ファイルの作成で安全に停止処理を促します（run_execution/run_monitoring はこのフラグを監視しています）。
- Kill Switch（緊急停止）は settings.kill_flag_path（デフォルト: data/kill.flag）で管理します。起動時に kill.flag が存在すると起動を拒否する構成です（KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリア可能だが本番では推奨しません）。

重要な環境変数
----------------
必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite パス（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。デフォルト 60）

.env の自動読み込み
- 起動時に .env（および .env.local）を自動で読み込みます。既存の OS 環境変数は上書きされません。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
------------------------------

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数読み込み・Settings（アプリ設定取得）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（セッション制御・PID 管理）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- broker_api.py — BrokerAPI のデータモデル / Protocol / 例外 / ファクトリ
- kabu_client.py — kabu station REST/WebSocket クライアント実装（httpx, websocket-client）
- mock_client.py — MockBrokerClient（ペーパートレード / テスト用）
- broker_factory.py — Settings に基づくブローカークライアント生成
- order_record.py — 注文状態と状態遷移ロジック（ビジネスロジック）
- order_repository.py — SQLite を使った永続化（orders テーブル初期化含む）
- order_manager.py — 発注ワークフロー（create/send/sync/cancel）
- execution_engine.py — ExecutionEngine（シグナル処理、push ドレイン、kill switch）
- reconciler.py — 起動時リコンシリエーション（OrderSent の突合、ポジション照合）
- risk_manager.py — Gate1/2/3 のリスク制御ロジック

src/kabusys/data/
- calendar_management.py — マーケットカレンダー管理（DuckDB + J-Quants 連携）
- news_collector.py — RSS ニュース収集（セキュアな前処理・保存ロジック）
- jquants_client.py — （データ取得用クライアントを想定）※実装はコードベースに依存

src/kabusys/monitoring/
- monitoring_db.py — 監視用 DB 初期化とログ関数（init_monitoring_db 等）
- system_monitor.py — システム監視のロジック（CPU/メモリ/ディスク閾値等）

src/kabusys/utils/
- logging_setup.py — ロギング初期化ユーティリティ
- process_priority.py — プロセス優先度設定ユーティリティ

その他
- config/*.yaml — システム設定用 YAML（存在しない場合は警告。validate_config で検出）
- .env, .env.local — 環境変数設定（Git にコミットしないこと）
- data/ — DB や PID / flag ファイル保存用（data/kabusys.duckdb, data/monitoring.db, data/execution.pid, data/kill.flag, data/stop_requested.flag など）

運用上の注意
------------
- .env は機密情報（API トークン・パスワード）を含むため絶対に VCS にコミットしないでください。
- 本番（KABUSYS_ENV=live）での運用時は LINE 通知（LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID）や Kill Switch の設定等を忘れずに確認してください。validate_config はこれらの不足を警告します。
- ExecutionEngine はデフォルトで通知・キャンセル・リコンシリエーション等の安全機構を備えていますが、外部ブローカーの API 挙動やネットワーク障害に応じた運用手順を整備してください。
- `BrokerClientFactory` は `live` を未実装にしているため、本番相当のブローカークライアントを導入する場合は実装を追加してください。

開発・テストのヒント
-------------------
- 単体テストやローカル開発では KABUSYS_ENV=paper_trading / development として MockBrokerClient を利用してください。
- MockBrokerClient は fill_mode（instant/partial/never/reject）を切り替えて各種ケース（即時約定・部分約定・保留・拒否）をテストできます。
- validate_config は PyYAML がないと YAML のパース検証をスキップします。YAML 検証を行う場合は PyYAML をインストールしてください。

ライセンス / 貢献
-----------------
（この README では省略。実際のリポジトリでは LICENSE ファイルや Contributing ガイドを含めてください）

以上がこのコードベースの概要と基本的な使い方です。README に記載されていないスクリプトや追加の設定ファイルがある場合は、プロジェクト内の該当ドキュメントやコメントを参照してください。質問や追加ドキュメントが必要であれば教えてください。