KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
主な機能はシグナルに基づく発注エンジン（ExecutionEngine）、発注の状態管理と再同期（Reconciler）、3段階のリスクガード（RiskManager）、監視ループ（SystemMonitor）、およびカレンダー／ニュース収集などのデータ処理ユーティリティを含みます。  
設計上、ブローカー接続は抽象化されており、開発／検証用に MockBrokerClient を用いた paper_trading（ペーパートレード）がサポートされています。kabuステーション実装（KabuStationClient）は既に用意されていますが、設定により本番接続を制御します（注意: Broker の live 実装はファクトリ側で制限があります）。

主な特徴
--------
- 環境設定ウィザード（.env の対話的作成）
- 起動前の設定検証ツール（.env と config/*.yaml のチェック）
- ExecutionEngine：シグナルプル型発注＋WebSocket push ドレイン
- Order 管理：状態遷移（OrderRecord）・永続化（SQLite）・送信フロー（OrderManager）
- リスク管理：Gate1〜3（余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
- Reconciler：クラッシュ後の OrderSent 照合とポジション差分検出
- Broker API 抽象化（Protocol）と Mock / KabuStation クライアント
- データユーティリティ：マーケットカレンダー（DuckDB）・ニュース収集（RSS）
- 監視プロセス用スクリプト（run_monitoring）と実行エンジン起動スクリプト（run_execution）

前提（推奨）
-----------
- Python 3.10 以上（型アノテーション等を利用）
- OS 標準の SQLite（標準ライブラリ）
- 追加パッケージ（最低限、実行に必要なもの）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML の検証を行いたい場合）
- ネットワーク接続（kabuステーション API や J-Quants などに接続する場合）

セットアップ手順
----------------
1. リポジトリをクローン／展開
   - プロジェクトルートに src/ と data/ 等が存在する想定です。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 明示的に必要なパッケージを入れる場合:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env 作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、kabu API パスワード等を入力します。
   - 生成された .env は絶対に Git にコミットしないでください（ウィザードも注意喚起します）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いで exit(1) になります:
     - python -m kabusys.validate_config --strict

6. DB 初期化（必要なら手動で）
   - 監視用 SQLite（デフォルト: data/monitoring.db）や DuckDB（data/kabusys.duckdb）は起動時に自動で作成・初期化される処理がありますが、必要に応じて事前にディレクトリを作成してください。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり／運用で設定推奨）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — デフォルト: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabuステーション API の base URL
- LINE_CHANNEL_ACCESS_TOKEN — 本番でのアラート用（任意）
- LINE_USER_ID — 本番でのアラート先（任意）
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリア（0/1、本番は 0 推奨）

.env 自動ロードの挙動
--------------------
- 起動時にプロジェクトルート（.git または pyproject.toml）を探索し、.env を自動ロードします。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方
------
主な CLI スクリプト（モジュールとして実行）:

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - オプション: --strict（警告を FAIL として扱う）

- 実行エンジンを起動（通常はサービスとして稼働）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録します。

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒、デフォルト 60）。

運用上の注意
-------------
- KABUSYS_ENV=live を設定する場合は設定内容を慎重に確認してください（validate_config は live で警告を出します）。Broker の live 動作（KabuStationClient）を用いる際は API 設定や取引パスワードの取り扱いに十分注意してください。
- 起動時に data/ 以下に PID ファイルや stop flag、kill flag を作成／検出するので、プロセス管理はこれらのファイルに依存する箇所があります（PID: data/execution.pid 等）。
- .env 内のシークレットは秘匿し、Git 管理下に置かないでください。

ディレクトリ構成（抜粋）
-----------------------
以下はソース配置の主要ファイルと役割の一覧（src/kabusys 以下）:

- __init__.py
  - パッケージ定義（バージョン等）

- config.py
  - 環境変数読み込み（.env 自動読み込み）と Settings クラス

- config_setup.py
  - .env の対話式作成ウィザード

- validate_config.py
  - .env と config/*.yaml の静的検証 CLI

- run_execution.py
  - ExecutionEngine を立ち上げるエントリポイントスクリプト

- run_monitoring.py
  - SystemMonitor を立ち上げるエントリポイントスクリプト

- execution/
  - broker_api.py           — Broker API のデータモデル・Protocol・ファクトリ
  - kabu_client.py          — kabuステーション REST クライアント（HTTP/WebSocket）
  - mock_client.py          — テスト用 MockBrokerClient
  - broker_factory.py       — Settings に基づく broker クライアント生成
  - execution_engine.py     — ExecutionEngine（メインの発注ロジック）
  - order_record.py         — Order の状態遷移ロジック（ビジネスロジック）
  - order_repository.py     — SQLite を用いた永続化層
  - order_manager.py        — OrderManager（外向き API、発注フロー）
  - reconciler.py           — 再起動時リコンシリエーション
  - risk_manager.py         — RiskManager（3段階リスクガード）

- data/
  - calendar_management.py  — マーケットカレンダー管理（DuckDB）
  - news_collector.py       — RSS ニュース収集と前処理
  - （jquants_client 等、外部データ連携モジュールを想定）

- monitoring/
  - monitoring_db.py        — 監視用 SQLite テーブル初期化・書き込み（参照あり）
  - system_monitor.py       — システム監視ロジック（参照あり）

- utils/
  - logging_setup.py        — ロギング初期化
  - process_priority.py     — プロセス優先度設定（高優先度など）

補足（設計メモ）
----------------
- 発注フローはクラッシュ安全性を考慮した 2 相永続化（OrderSent の前後や broker_order_id の先保存など）を採用しています。Reconciler により再起動後の状態復旧を行います。
- RiskManager はトークンバケツによるレート制限、サーキットブレーカー、ドローダウン監視を実装しています。
- DuckDB を使ってバックテストデータやシグナルをクエリし、ExecutionEngine がそれを読み込んで発注を行います。
- news_collector は SSRF 対策や XML の安全なパース（defusedxml）を取り入れています。

ライセンス・貢献
----------------
- ライセンス情報がプロジェクトに含まれている場合はそちらに従ってください。  
- バグ修正・機能追加などの貢献は Pull Request を歓迎します。特に live ブローカークライアント周りや追加のモニタリング機能は改善の余地があります。

お問い合わせ
------------
- ソースコードや設計に関する質問があれば、リポジトリの Issue に記載してください。

以上。必要であれば README に含める実行例（コマンド）や .env のテンプレート、よくあるトラブルシュートセクションを追加しますか？