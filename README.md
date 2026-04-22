KabuSys — README (日本語)
  
概要
- KabuSys は日本株自動売買システムのコアライブラリ群と実行スクリプトを含むコードベースです。
- 発注エンジン（ExecutionEngine）、リスク管理、注文永続化（SQLite）、監視ループ、カレンダー管理、ニュース収集などを含みます。
- 本リポジトリはローカル開発（development）、ペーパートレード（paper_trading）、本番（live）の各実行モードを想定しています。

主な機能
- 環境設定ウィザード（.env の対話的生成 / 更新）
- 設定検証ツール（.env と config/*.yaml の起動前検証）
- ExecutionEngine：シグナルの読み込み→発注→リコンシリエーション→WebSocket push ドレイン
- Broker クライアント抽象化：MockBrokerClient（テスト用）と KabuStationClient（kabuステーション実装）
- 注文状態機械（OrderRecord / OrderManager）と SQLite 永続化（OrderRepository）
- リスク管理（Gate1/Gate2/Gate3）・サーキットブレーカー・レート制御
- リコンシリエーション（起動時に OrderSent の注文を突合して復旧）
- 監視ループ（SystemMonitor のポーリング）と監視 DB（SQLite）
- データ系ユーティリティ：マーケットカレンダー管理、RSS ニュース収集など

前提（依存ライブラリ・環境）
- Python 3.10+（typing | match などの新仕様を使っている場合があるため最新推奨）
- 推奨インストール例（requirements.txtがない場合の最低例）:
  pip install duckdb httpx websocket-client pyyaml defusedxml
- 標準ライブラリ: sqlite3, logging, threading など

セットアップ手順
1. リポジトリをクローンしてプロジェクトルートに移動
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt が用意されている場合）
   - または必要なパッケージを個別にインストール:
     pip install duckdb httpx websocket-client pyyaml defusedxml
4. .env を作成
   - 対話的ウィザードで作成する（推奨）
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに手動で .env を配置
5. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする（CI 等で）:
     python -m kabusys.validate_config --strict

重要な環境変数（.env）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- オプション（主要）
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station ベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1、デフォルト: 0)
- 自動ロードの挙動
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の例（config_setup で生成される内容）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- LINE_CHANNEL_ACCESS_TOKEN=（任意）
- LINE_USER_ID=（任意）

使い方（起動 / CLI）
- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱い
- 実行スクリプト（監視・発注）
  - 監視ループ起動（SystemMonitor のポーリング）
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 停止フラグ: data/stop_requested.flag が存在するとループを終了
  - 発注エンジン起動（ExecutionEngine）
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）を使う
    - 停止フラグ: data/stop_requested.flag
    - PID ファイル: data/execution.pid（設定で変更可）
- その他
  - validate_config は config/*.yaml の存在と（PyYAML がインストールされていれば）パースを検証します
  - run_execution は起動時にリコンシリエーション（Reconciler）を実行して OrderSent 状態の回復を試みます

運用・注意点
- KABUSYS_ENV=live の場合は本番運用なので LINE 通知や Kill Switch 設定などを慎重に確認してください。
- kill.flag（デフォルト data/kill.flag）は起動時に残っていると起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアします（本番では推奨されません）。
- 監視・発注プロセスは data ディレクトリ下のフラグファイル（stop_requested.flag や kill.flag）と PID ファイルで制御します。
- DB（DuckDB / SQLite）の親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、事前に data ディレクトリを作成しておくと安全です。
- 本番での KabuStationClient による接続は kabuステーション® が PC 上で稼働していることが前提です。開発/テストでは MockBrokerClient を使ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数の読み込みと Settings クラス（自動 .env ロード）
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine を起動するスクリプト
  - run_monitoring.py          — SystemMonitor のポーリングスクリプト
  - data/
    - calendar_management.py   — マーケットカレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集
    - jquants_client.py        — （外部）J-Quants API クライアント（参照実装）
  - execution/
    - __init__.py
    - broker_api.py            — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py        — Settings に基づくクライアント生成
    - kabu_client.py           — kabuステーション REST API 実装
    - mock_client.py           — テスト用のモックブローカー
    - order_record.py          — 注文状態マシンのデータモデル
    - order_repository.py      — SQLite 永続化（orders テーブル）
    - order_manager.py         — 発注フロー（create/send/sync/cancel）
    - execution_engine.py      — ExecutionEngine（シグナル処理 / push ドレイン / kill_switch）
    - reconciler.py            — 起動時リコンシリエーション
    - risk_manager.py          — Gate1/2/3 を実装するリスク管理
    - ...（その他関連モジュール）
  - monitoring/
    - monitoring_db.py         — 監視 DB 初期化 / ログ
    - system_monitor.py        — システム監視ロジック
  - utils/
    - logging_setup.py         — ロギング設定ヘルパ
    - process_priority.py      — プロセス優先度設定ヘルパ
  - config/                    — 設定用 YAML（system_config.yaml 等のテンプレート）
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

補足・開発メモ
- ExecutionEngine は DuckDB から当日の signals テーブルを読み、portfolio_targets と join して発注対象を決定します（_read_signals）。
- OrderManager は「2相永続化」設計（OrderSent の永続化→ブローカー呼び出し→broker_order_id の永続化→OrderAccepted へ遷移）でクラッシュ耐性を高めています。
- Reconciler は起動時に OrderSent の注文を突合し、ポジション差分を検出してログ出力します。
- RiskManager はトークンバケツ方式のレート制御・サーキットブレーカー・ドローダウン監視を提供します。
- news_collector.py では SSRF 対策や XML パース対策（defusedxml）などセキュリティに配慮した設計になっています。

トラブルシューティング
- 設定検証で必須環境変数のエラーが出る場合は .env を見直してください（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）。
- config/*.yaml が不足している場合、validate_config は警告を出します（PyYAML がないと内容の検証はスキップされます）。
- run_execution/run_monitoring をバックグラウンドで運用する場合は PID ファイルと stop/kill フラグを適切に扱ってください。

以上。必要であれば README に含めたい追加情報（例: サンプル .env、CI での使い方、詳しい依存関係一覧、ユニットテスト実行方法など）を教えてください。