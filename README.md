KabuSys — 日本株自動売買システム (README)
=====================================

概要
----
KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。  
主に以下を提供します。

- シグナル駆動の発注エンジン（ExecutionEngine）
- ブローカー API 抽象層（実運用向けの KabuStationClient とテスト用 MockBrokerClient）
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
- 安全装置（3段階のリスクガード、リコンシリエーション、kill switch）
- 監視ループ（SystemMonitor）と監視用 DB
- データユーティリティ（マーケットカレンダー管理・ニュース収集など）
- 環境設定ウィザード（.env 作成支援）と起動前設定検証ツール

特徴
----
- 環境変数 / .env 経由で設定を管理。プロジェクトルートの .env/.env.local を自動読み込み（不要時は無効化可能）。
- 発注処理は DB に対して冪等・クラッシュ耐性を意識した実装（OrderSent の2相永続化等）。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を切替可能。paper_trading / development は MockBrokerClient を使用。
- リスク管理は Gate1/2/3 の 3 段構成（余力・重複・ポジション上限 / レート制限・サーキットブレーカー / ドローダウン監視）。
- 起動時に未確定注文(= OrderSent)をブローカーと突合するリコンシリエーション機能を持つ。
- DuckDB / SQLite を利用したデータ管理（デフォルトパスは data/ 以下）。

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（| 型アノテーション等を使用）
- システムに sqlite3 が利用可能
- DuckDB を使用するため pip で duckdb をインストールしてください

1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必要最低限のパッケージ（例）
     - pip install duckdb httpx websocket-client defusedxml
   - オプション: PyYAML を入れると config/*.yaml の検証が有効になります
     - pip install pyyaml
4. data ディレクトリを作成
   - mkdir -p data
   - （起動時に自動作成されることもありますが手動で作っておくと安心です）

環境変数 / .env
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意・その他:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)
  - KABU_API_BASE_URL (kabu station API のベース)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
  - PAPER_FILL_MODE（paper_trading 用: instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 sqlite path）
- .env の自動読み込み
  - 実行時、プロジェクトルート（.git または pyproject.toml を基準）にある .env を読み込みます。
  - .env.local が存在すればそれが .env の上書き（override）として読み込まれます。
  - 必要に応じて自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定ウィザード / 起動前検証
--------------------------
- .env を対話的に作成・更新する:
  - python -m kabusys.config_setup
  - ウィザードは既存の .env を読み込み、Enter で既存値を再利用できます。シークレット項目はマスク表示。
- 起動前に設定を検証する:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL として exit(1) になります
  - validate_config は必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在・YAML パース（PyYAML 必要）、本番向けの追加安全チェック（LINE通知設定・KILL_FLAG_CLEAR_ON_START）を行います

実行方法（主要スクリプト）
-------------------------
- Execution エンジンを起動（通常はデーモン等で管理）
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings を読み込み、適切な sqlite/duckdb に接続
    - BrokerClientFactory を用いてブローカークライアントを選択（development/paper_trading → Mock）
    - ExecutionEngine を構築してセッションを run_session() で実行
    - stop フラグ（data/stop_requested.flag）や kill.flag の監視と対応
- Monitoring（SystemMonitor）ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使います
- 設計上の注意
  - KABUSYS_ENV=live は BrokerClientFactory では未実装（NotImplementedError）です。live を使う場合は KabuStationClient の利用実装に注意してください（本コードは Mock を主に想定）。

主要モジュール説明（概要）
-------------------------
- kabusys.config
  - .env 読み込みロジック、自動ロード、Settings クラス（環境変数から設定を取得）
- kabusys.config_setup
  - .env を対話式に生成・更新する CLI ウィザード
- kabusys.validate_config
  - 起動前に環境設定の検証を行う CLI
- kabusys.run_execution / run_monitoring
  - 実運用想定の起動スクリプト
- kabusys.execution
  - broker_api: ブローカー用データモデル、Protocol、ファクトリ
  - kabu_client: KabuStation 用 HTTP/WebSocket クライアント実装（httpx, websocket-client）
  - mock_client: テスト用の MockBrokerClient（fill_mode サポート）
  - order_record / order_repository / order_manager: 注文の状態管理と永続化
  - execution_engine: シグナル読み取り → Gate チェック → 発注 → push ドレイン を行うエンジン
  - reconciler: 起動時の OrderSent 照合 / ポジション差分チェック
  - risk_manager: Gate1/2/3 のリスク評価（レート制限、サーキットブレーカー、ドローダウン等）
  - broker_factory: Settings に応じた BrokerClient の生成
- kabusys.data
  - calendar_management: JPX カレンダー管理（DuckDB を利用）
  - news_collector: RSS からニュース収集・前処理・保存（SSRF、XML 脆弱性対策あり）
  - jquants_client: J-Quants API 用クライアント（参照あり）
- kabusys.monitoring
  - monitoring_db, system_monitor 等（監視データの記録・チェック）
- kabusys.utils
  - logging_setup, process_priority などのユーティリティ

ファイル/ディレクトリ構成（抜粋）
--------------------------------
（パッケージ直下を src/kabusys とした構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
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
    - ...（その他 execution 周辺）
  - data/
    - calendar_management.py
    - news_collector.py
    - jquants_client.py (参照)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - config/                    — YAML 設定ファイル群（例: system_config.yaml 等）
  - data/                      — 実行時 DB やフラグファイルが置かれる（data/*.db, *.pid, kill.flag）

運用上の注意
------------
- .env は機密情報（パスワード・トークン）を含むため絶対に Git にコミットしないでください。
- validate_config をまず実行して、必須変数や致命的な設定ミスを事前検出してください。
- production（live）運用を行う場合は、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の取り扱い等、本番向けの安全設定を十分に確認してください。
- paper_trading（ペーパートレード）では専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使って本番 DB と分離します。デフォルトは data/paper_trading.db。

よくあるコマンドまとめ
--------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

ライセンス・貢献
----------------
（このリポジトリに LICENSE ファイルがある場合はそちらを参照してください）  
バグ報告・プルリクエスト歓迎。実運用前の安全性確認（レビュー・テスト）を推奨します。

補足
----
- 本 README はソースコード内の docstring と実装を基に簡潔にまとめたものです。内部の細かい挙動や API の詳細は各モジュールの docstring / ソースコードを参照してください。