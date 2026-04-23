KabuSys
======

日本株自動売買システム（開発中） — シグナル駆動の発注エンジン / 監視 / 設定ツール一式を含むライブラリ兼実行パッケージです。  
このリポジトリはローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を想定した構成となっており、環境変数ベースの設定管理と各種 CLI スクリプトを提供します。

主な特徴
--------
- 環境変数（.env/.env.local）からの自動読み込みと対話式設定ウィザード
- 起動前の設定検証ツール（必須環境変数・YAML 設定ファイルの存在/パースチェック等）
- ExecutionEngine：シグナルに基づく発注フロー（Gate1/Gate2/Gate3 の 3 段階リスクガード）
- Mock ブローカークライアントを用いたペーパートレード対応（実際の kabu station を不要にする）
- Reconciler：再起動時の OrderSent 状態照合およびポジション差分検出
- Monitoring：システム監視用ループ（監視 DB を使ったログ収集）
- データ処理ユーティリティ（マーケットカレンダー管理、RSS ニュース収集等）

主要機能一覧
--------------
- 設定ウィザード（kabusys.config_setup）：.env の生成/更新を対話的に支援
- 設定検証（kabusys.validate_config）：起動前に .env と config/*.yaml を検査
- 発注エンジン起動（kabusys.run_execution）：ExecutionEngine の起動スクリプト
- 監視ループ起動（kabusys.run_monitoring）：SystemMonitor のポーリングループ
- ブローカー抽象化（execution.broker_api / broker_factory）：Mock / 実ブローカーの切替
- 注文永続化（execution.order_repository）：SQLite ベースの orders テーブル
- 注文状態管理（execution.order_record / order_manager）
- リスク管理（execution.risk_manager）：レート制限、サーキットブレーカー、ドローダウン等
- カレンダー管理（data.calendar_management）：DuckDB ベースの JPX カレンダー管理
- ニュース収集（data.news_collector）：RSS 収集・正規化・保存

セットアップ手順
----------------
1. リポジトリを取得し、Python 仮想環境を作成・有効化します（例: venv / virtualenv / pyenv-venv）。
   - Python 3.9+ を推奨（コードは typing / Path 等を使用）

2. 依存パッケージをインストールします（requirements.txt がある場合はそちらを利用）。
   代表的な依存例（必要に応じて調整）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - pyyaml (任意：YAML 検証を有効にするなら必須)
   - その他（実環境では pyproject.toml / requirements.txt を参照）

   例:
   python -m pip install duckdb httpx websocket-client defusedxml pyyaml

3. プロジェクトルートに .env を配置します（または対話式ウィザードで生成）。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須環境変数（最小セット）
--------------------------
- JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API パスワード（必須）

よく使う任意 / 推奨環境変数
- KABUSYS_ENV            — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL      — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1）

使い方（CLI）
--------------
- 環境設定ウィザード（.env を新規作成または更新）
  python -m kabusys.config_setup
  オプション:
  --env-file PATH  : .env のパスを指定（デフォルトはプロジェクトルートの .env）

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  オプション:
  --strict         : 警告も失敗扱いにして exit code 1 を返す

  validate_config は .env と config/*.yaml（下記参照）の存在や簡易チェックを行います。PyYAML 未導入の場合は YAML 内容チェックはスキップされます。

- 発注エンジンを起動（本番/ペーパーどちらも Settings による判定）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV が paper_trading または development なら MockBrokerClient を使用
  - KABUSYS_ENV=paper_trading の場合、監視 DB（SQLite）は paper_trading 専用パスを使用して本番 DB と分離
  - 停止フラグ: data/stop_requested.flag が存在するとループを終了
  - PID ファイル: data/execution.pid（Settings.pid_file_path）に PID を書き込む

- システム監視ループを起動
  python -m kabusys.run_monitoring

  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）をオーバーライド可能（デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path を使用する（監視は実 DB を見る設計）

内部ファイル / 挙動の要点
-----------------------
- .env の管理:
  - .env と .env.local を自動で読み込み（OS 環境変数が優先）
  - 値のパースはシェル風に対応（export を無視、シングル/ダブルクォート、エスケープ等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み抑止

- 設定検証:
  - 必須環境変数の未設定はエラー
  - プレースホルダ値（* _here / your_value 等）は警告
  - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）
  - config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml） の存在確認と PyYAML によるパースチェック（PyYAML がインストールされている場合）
  - KABUSYS_ENV=live のときは追加の安全チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告等）

- データベース:
  - DuckDB は分析・シグナルデータ格納用（デフォルト: data/kabusys.duckdb）
  - SQLite は監視・orders 永続化用（デフォルト: data/monitoring.db / ペーパー用は data/paper_trading.db）
  - orders テーブルは init_orders_db() で作成（冪等）

- 停止フラグ / PID:
  - stop_requested.flag（data/stop_requested.flag）を置くと監視・実行が安全に停止
  - PID ファイルは settings.pid_file_path（デフォルト data/execution.pid）へ書き込む

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要なモジュール構成（抜粋）です:

- kabusys/
  - __init__.py              — パッケージ定義（__version__ など）
  - config.py                — 環境変数・Settings 管理（自動 .env ロード、Settings クラス）
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — 発注エンジン起動スクリプト（ExecutionEngine）
  - run_monitoring.py        — 監視ループ起動スクリプト（SystemMonitor）
  - execution/
    - broker_api.py          — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に基づく Broker クライアント生成
    - kabu_client.py         — kabu station 実 API クライアント（httpx/websocket）
    - mock_client.py         — テスト用 MockBrokerClient
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 注文フロー管理（create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py          — 再起動時リコンシリエーション
    - risk_manager.py        — Gate1/2/3 リスクチェック
  - data/
    - calendar_management.py — マーケットカレンダー（DuckDB）管理
    - news_collector.py      — RSS ニュース収集・前処理
    - jquants_client.py      — （データ取得用クライアント、別途実装）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 初期化・ログ関数（init_monitoring_db 等）
    - system_monitor.py      — SystemMonitor 実装（別ファイルに定義）
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

注意事項 / 運用上のヒント
-------------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないこと（config_setup.py のヘッダにも明記）。
- KABUSYS_ENV=live の場合は特に設定を慎重に確認してください。validate_config の --strict モードで警告を FAIL 扱いにできます。
- 本番での自動 kill_flag クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。通常は 0（クリアしない）を推奨します。
- ペーパートレードは MockBrokerClient を用いて DB を分離しているため、本番 DB を汚染せずに動作検証が可能です。
- YAML の設定ファイル群（config/*.yaml）はプロジェクト設定の主要な定義を含む想定です。存在しない場合はスクリプトから生成するユーティリティ（python scripts/generate_config.py）参照の旨のメッセージが出ます（本リポジトリにスクリプトがあればそれを使って生成してください）。

最小実行例（ローカルで動かす場合）
---------------------------------
1. 仮想環境作成・依存インストール
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install duckdb httpx websocket-client defusedxml pyyaml

2. .env を作成（対話式）
   python -m kabusys.config_setup

3. 設定検証
   python -m kabusys.validate_config

4. ペーパートレードで実行（MockClient を使用）
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution

5. 監視ループ起動（別プロセス）
   python -m kabusys.run_monitoring

ライセンス / 貢献
-----------------
- ライセンス情報・貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING を参照してください（本 README に記載なしの場合はリポジトリルートを確認）。

問題報告 / 開発
----------------
- 不具合報告や機能追加の提案は Issue を作成してください。実装の背景や再現手順を添えると早く対応できます。

以上がこのコードベースの概要と基本的な使い方です。詳細な設計方針や API の仕様（例: broker_api のデータモデル、ExecutionEngine の詳細なループ、DB スキーマ）は各モジュールの docstring を参照してください。