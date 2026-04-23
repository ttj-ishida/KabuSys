README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下を含みます:

- 発注エンジン（ExecutionEngine）: シグナルに基づく発注処理、WebSocket プッシュ処理、リスクガード、リコンシリエーション等
- ブローカークライアント抽象層: 実ブローカー（kabu station）とモック実装を切り替え可能
- 注文永続化層（SQLite）
- 監視プロセス（SystemMonitor）用ループ
- 環境設定ウィザード（.env 作成）および設定検証ツール
- データ系ユーティリティ（マーケットカレンダー、ニュース収集など）

バージョン: 0.1.0

主な機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に生成/更新
- 設定検証 CLI（python -m kabusys.validate_config）で .env と config/*.yaml を起動前にチェック
- ExecutionEngine によるシグナルベースの発注フロー（Gate1/2/3 によるリスクガード）
- MockBrokerClient によるペーパートレード／ローカルテスト（KABUSYS_ENV=paper_trading / development）
- 起動時リコンシリエーション（OrderSent 状態の注文の突合）
- 監視ループ（run_monitoring）でシステムメトリクス記録・監視
- DuckDB を用いたシグナル/ポートフォリオ操作・カレンダー管理
- RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、正規化）

前提（推奨）
-----------
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨 Python パッケージ（実行に必要なものの一部）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config 検証時に YAML パースを有効化）
  - defusedxml
  - その他（requests 等は用途に応じて追加）

セットアップ手順
----------------
1. リポジトリをクローン（またはソースを入手）:
   - git clone <repo>

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表的な依存パッケージ）:
   - pip install duckdb httpx websocket-client PyYAML defusedxml

   （実運用で使う場合は requirements.txt / Poetry 等の管理を推奨）

4. .env の作成:
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 既存の .env を編集する場合はプロジェクトルートに .env を配置

5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする (--strict):
     - python -m kabusys.validate_config --strict

主要な環境変数（必須 / 任意）
--------------------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意 / 設定:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（本番では必須に近い）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
- PAPER_FILL_MODE — paper_trading 時のモック約定挙動 (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

.env 自動ロードについて:
- デフォルトでプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（コマンド）
-----------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話的に .env を作成・更新します（シークレット項目はマスク表示）

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict で警告があっても exit(1) にする

- 実行エンジン（本番/ペーパートレード起動）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid（デフォルト）に PID を書き、停止は data/stop_requested.flag を作成して通知します
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は常に本番 sqlite_path を使用します（監視は環境に依存しない）

プロセス管理・停止フラグ
-----------------------
- stop 指示: プロジェクトルートの data/stop_requested.flag を作成すると、run_execution/run_monitoring は次のループで検知して終了します
- kill スイッチ: ExecutionEngine は kill.flag を監視し、存在する場合は起動を拒否または全 active 注文のキャンセルを行います
- 起動時の kill.flag 自動クリア: KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を消去して続行します（本番では推奨しません）

重要な設計メモ
--------------
- ExecutionEngine はシグナル処理（指定時間帯）と WebSocket Push のドレインを組み合わせた動作をします。発注前に Gate1/2、約定後に Gate3 のリスクチェックを行います。
- BrokerAPI の実装は抽象化されており、MockBrokerClient と KabuStationClient を切り替えて使えます。mock モードはテスト・バックテスト用に設計されています。
- 注文状態管理は OrderRecord（状態機械）で行い、OrderRepository が SQLite に永続化します。クラッシュや中断に備えて 2 相永続化等の設計考慮があります。
- DuckDB は分析・シグナル問い合わせ・カレンダー管理に使います。market_calendar が存在しない場合は曜日ベースのフォールバックを行います。
- RSS ニュース収集はセキュリティ（SSRF、XML の脆弱性、追跡パラメータ除去）に配慮しています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数と Settings クラス（自動 .env ロード、必須チェック）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 起動前設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト（メインの発注プロセス）
- run_monitoring.py — 監視ループ起動スクリプト

- execution/
  - broker_api.py — Broker API のデータモデル、Protocol、ファクトリ
  - kabu_client.py — kabu station 実装（HTTP / WebSocket）
  - mock_client.py — MockBrokerClient（テスト用）
  - broker_factory.py — 設定に応じたクライアント生成
  - order_record.py — 注文状態機械（OrderRecord）
  - order_repository.py — SQLite 永続化（orders テーブル）
  - order_manager.py — 発注ワークフロー（create/send/sync/cancel）
  - execution_engine.py — 発注エンジン本体（シグナル処理・push 処理・kill）
  - reconciler.py — 起動時のリコンシリエーション処理
  - risk_manager.py — Gate1/2/3 の実装（リスク制御）

- monitoring/ — 監視関連（DB 初期化や SystemMonitor 等）
- data/
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS ニュース収集（セキュアな実装）

補足 / 運用上の注意
------------------
- 本番（KABUSYS_ENV=live）では LINE 通知や適切な DB 設定、kill flag の運用など慎重な設定確認が必須です。validate_config の警告は無視せず確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- KabuStationClient を本番で使う場合は kabu ステーションが動作している環境（ローカル PC 上での kabu station アプリ）を想定しています。
- スレッド・外部 API 呼び出しの例外はログ出力して処理継続する設計の箇所が多くあります。監視ログの確認・アラート設定を推奨します。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください）

問い合わせ
----------
（プロジェクトメンテナや連絡先を追記してください）

--- 
必要に応じて README をプロジェクト固有のインストール手順・運用手順や CI/CD の説明で補完してください。