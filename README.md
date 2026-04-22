KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォーム（プロトタイプ）です。  
主な目的はシグナルに基づく注文発行・約定管理・再起動時のリコンシリエーション・監視を行うことです。  
設計上、実運用（live）と検証（paper_trading / development）を切り替えられ、paper_trading では実際のブローカー接続なしで動作します。

主な機能
--------
- 環境設定ウィザード（.env 作成支援）: kabusys.config_setup
- 起動前設定検証 CLI（.env と config/*.yaml を検査）: kabusys.validate_config
- ExecutionEngine: シグナル読み取り→Gate1/2 リスクチェック→発注→push ドレイン（発注フロー全体）
  - 注文状態管理（OrderRecord の状態遷移）
  - 永続化（SQLite に orders テーブル）
  - リスク管理（3段階: check_signal / check_execution / check_metrics）
  - Reconciler（再起動時の OrderSent 注文照合、ポジション差分検出）
- Broker クライアント層
  - 実装: KabuStationClient（kabuステーション用 REST/WebSocket クライアント）
  - モック: MockBrokerClient（paper_trading / development 用テスト実装）
- 監視ループ（SystemMonitor を定期ポーリング）: kabusys.run_monitoring
- データ関連ユーティリティ
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集（RSS 取得・正規化・保存ロジック）

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（型ヒント・構文での union 型等を使用）
- システムライブラリ: SQLite は標準、DuckDB は Python パッケージ（duckdb）を使用

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限推奨パッケージ:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - pyyaml (config/*.yaml の中身検証を有効にする場合)
   - 例:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

4. 初期設定ファイルの作成
   - 対話式ウィザードを使って .env を作成:
     - python -m kabusys.config_setup
   - ウィザードで入力した値はプロジェクトルートの .env に保存されます（デフォルト）。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
     - python -m kabusys.validate_config --strict

使い方
------
環境変数の扱い
- .env（および .env.local）がプロジェクトルートにあれば自動で読み込まれます。
- OS 環境変数が優先され、.env の値は未設定時に補完されます。
- 自動ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API パスワード（必須）

代表的な任意 / 推奨項目
- KABUSYS_ENV            — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 任意（本番でのアラートに使用）

実行例
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（ExecutionEngine）
  - 実行:
    - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading（デフォルト development でも Mock を使用）では MockBrokerClient が使われ、注文は data/paper_trading.db に記録され実際の発注は行われません。
    - 本番（live）向けの KabuStationClient は未実装/要注意箇所あり（コード内で NotImplementedError を投げる場合があります）。
  - 停止:
    - プロジェクトの data ディレクトリに stop_requested.flag を作成すると実行ループが終了します。
    - PID ファイルは settings.pid_file_path（デフォルト: data/execution.pid）に書き出されます。
- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を使います（環境にかかわらず）。

運用上の注意
- KABUSYS_ENV=live は本番扱いです。LINE 通知設定や Kill Switch 設定を必ず確認してください。
- 起動時の kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 により可能ですが、本番では 0 を推奨します。
- config/*.yaml が存在し内容を検証するには PyYAML が必要です。インストールされていない場合は検証がスキップされ、警告が出ます。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
  - パッケージ初期化、バージョン情報
- config.py
  - .env 自動読み込みロジック、Settings クラス（アプリ設定の取得）
- config_setup.py
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前チェック CLI（python -m kabusys.validate_config）
- run_execution.py
  - ExecutionEngine 起動スクリプト（注文フローのエントリポイント）
- run_monitoring.py
  - 監視ループ起動スクリプト
- execution/
  - broker_api.py
    - BrokerAPIProtocol、データモデル、例外クラス、create_broker_api()
  - kabu_client.py
    - KabuStationClient（REST/WebSocket 実装）
  - mock_client.py
    - MockBrokerClient（fill_mode を設定可能。テスト用）
  - broker_factory.py
    - Settings に基づき Broker を生成するファクトリ
  - order_record.py
    - Order の状態モデルと遷移ロジック（DB 非依存）
  - order_repository.py
    - SQLite を使った永続化層（orders テーブル）
  - order_manager.py
    - OrderRecord と OrderRepository / Broker を結びつける API（create/send/cancel/sync）
  - execution_engine.py
    - ExecutionEngine（シグナル処理 + push ドレイン）
  - reconciler.py
    - 再起動時のリコンシリエーション（OrderSent の突合、ポジション差分検出）
  - risk_manager.py
    - 3段階リスクガード（Gate1/2/3）
- data/
  - calendar_management.py
    - マーケットカレンダー管理（DuckDB ベース）
  - news_collector.py
    - RSS ニュース取得・正規化・DB 保存ロジック
- monitoring/
  - monitoring_db.py  (参照されるがここでは説明のみ)
  - system_monitor.py   (参照されるがここでは説明のみ)
- utils/
  - logging_setup.py
  - process_priority.py

サンプル .env（抜粋）
---------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=     # 任意
LINE_USER_ID=                  # 任意
KILL_FLAG_CLEAR_ON_START=0     # 本番は 0 推奨

補足
----
- DB ファイル（デフォルト data/ 配下）は必要に応じて自動作成されますが、parent ディレクトリが存在しない場合警告が出ます。事前に data/ を作成しておくとよいです。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）の存在を想定しています（存在しない場合は手動で用意してください）。
- 本リポジトリは実運用に用いる際は十分な検証と安全対策（秘密鍵の管理、ネットワーク周りの堅牢化等）が必要です。

ライセンス / 貢献
-----------------
（該当情報がないためここでは記載していません。必要に応じてプロジェクトの LICENSE を追加してください。）

以上。設定ウィザードと validate_config をまず実行し、development / paper_trading で動作を確認してから live 運用を検討してください。