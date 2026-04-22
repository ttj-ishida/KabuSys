KabuSys — 日本株自動売買システム（簡易ドキュメント）
=================================================

本リポジトリは、KabuSys（日本株自動売買システム）のコアモジュール群です。
ここではリポジトリ全体の概要、機能、セットアップ方法、主要スクリプトの使い方、ディレクトリ構成を日本語でまとめます。

重要: この README はソースのドキュメント（src/kabusys/*.py）を元に作成しています。実運用では .env と config/*.yaml の設定を必ず最初に行い、validate_config で検証してください。

プロジェクト概要
----------------
KabuSys は日本株の自動売買を想定したコンポーネント群です。主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）：シグナルを取り込み、発注・状態管理・リコンシリエーションを行う
- Broker クライアント層：kabuステーション向けクライアントとテスト用の Mock クライアント
- 注文永続化（SQLite）と Order 状態管理（OrderRecord）
- リスク管理（3 段階ガード: Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を用いた run_monitoring）
- 環境設定ウィザード（config_setup）と設定検証 CLI（validate_config）
- データ関連ユーティリティ（DuckDB ベースのカレンダー・ニュース収集など）

主な機能一覧
-------------
- config_setup: 対話式に .env を作成/更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env と config/*.yaml を起動前に検査する CLI（python -m kabusys.validate_config）
- run_execution: ExecutionEngine を起動するスクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading / development では MockBrokerClient を使用
  - paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- run_monitoring: 監視（SystemMonitor）用のポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
- Broker クライアント実装:
  - KabuStationClient: kabuステーション REST API（httpx + websocket-client）
  - MockBrokerClient: テスト・開発用モック（fill_mode 等を指定可能）
- 注文/状態管理:
  - OrderRecord: 状態遷移の検証・更新（DBには触れない純粋ロジック）
  - OrderRepository: SQLite を使った永続化
  - OrderManager: 発注フローのオーケストレーション（create/send/sync/cancel）
- RiskManager: Gate1（信号レベル） / Gate2（実行レベル） / Gate3（メトリクス）を実装
- Data 側ユーティリティ:
  - カレンダー管理（market_calendar を DuckDB に保持）
  - ニュース収集（RSS 収集、正規化、SSRF 対策等）

前提 / 推奨環境
---------------
- Python 3.10 以上（Union 演算子や型注釈スタイルを使用）
- 推奨パッケージ（主要依存）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（validate_config の YAML 検証に使用。インストールしなくても警告になるだけ）
  - defusedxml
- 標準ライブラリ: sqlite3, pathlib, logging 等を利用
- 実ブローカー連携（KabuStationClient）を使う場合は kabuステーション® アプリがローカルで起動している必要あり

セットアップ手順
----------------
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 例:
     - pip install duckdb httpx websocket-client pyyaml defusedxml
   - ※requirements.txt がある場合は pip install -r requirements.txt を利用
4. data ディレクトリを作成（スクリプトや起動時に自動作成される箇所もあるが、手動作成しておくと安全）
   - mkdir -p data
5. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（下の「重要な環境変数」を参照）
6. 設定検証:
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗とする）: python -m kabusys.validate_config --strict
7. DB 初期化（Orders テーブル等はスクリプトまたは起動時に作成されます）
   - 注: OrderRepository.init_orders_db 相当が実行される箇所（run_execution 等）で初期化される想定

重要な環境変数（必須 / オプション）
----------------------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

オプション（よく使われるもの）:
- KABUSYS_ENV — execution 実行モード: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（本番では必須に近い）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロードの挙動
--------------------
- デフォルトではプロジェクトルート（.git または pyproject.toml を基準）から .env を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- テストや強制的に自動読込を無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

主要な CLI / スクリプトの使い方
------------------------------

1) 環境設定ウィザード
- コマンド:
  - python -m kabusys.config_setup
- 説明:
  - 対話式に .env を生成 / 更新します。シークレットはマスク表示されます。
  - 生成後に python -m kabusys.validate_config で検証することを推奨。

2) 設定検証 CLI
- コマンド:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 説明:
  - .env（および config/*.yaml）に対して基本チェックを実行します。
  - エラーがあると exit code 1 を返します。--strict を付けると警告も失敗扱いになります。
  - 検査対象 YAML:
    - config/system_config.yaml
    - config/data_config.yaml
    - config/strategy_config.yaml
    - config/risk_config.yaml
    - config/execution_config.yaml
    - config/monitoring_config.yaml
  - PyYAML 未インストールの場合は YAML の中身検証をスキップして警告を出します。

3) 実行エンジン（Execution）
- コマンド:
  - python -m kabusys.run_execution
- 説明:
  - ExecutionEngine を起動します。KABUSYS_ENV に応じて MockBrokerClient を選択します（paper_trading/development）。
  - PID ファイル: data/execution.pid（デフォルト）。停止時は flag ファイルを立てる（data/stop_requested.flag）か kill flag（data/kill.flag）による制御。
  - 起動前に validate_config を実行してください。

4) 監視ループ
- コマンド:
  - python -m kabusys.run_monitoring
- 説明:
  - SystemMonitor のポーリングループを起動します。MONITOR_POLL_INTERVAL で間隔を調整可能。
  - 監視は環境にかかわらず本番 sqlite_path を使用する設計です。

停止・フラグ制御
----------------
- 停止要求: data/stop_requested.flag（存在を検出してループを抜ける）
- Kill Switch: settings.kill_flag_path（デフォルト data/kill.flag）
  - 起動時に kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合のみ自動クリアして起動）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/ 以下（抜粋）:

- __init__.py
  - パッケージ初期化。__version__ など。

- config.py
  - 環境変数読み込みロジック（.env のパーサ、Settings クラス、auto load 機能）
  - Settings: 各種設定値取得メソッド

- config_setup.py
  - .env 対話ウィザード（run_wizard / _write_env）

- validate_config.py
  - 起動前検証 CLI（必須環境変数、KABUSYS_ENV、YAML ファイル存在/パース等）

- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、エンジンスレッド管理）

- run_monitoring.py
  - 監視ループ起動スクリプト（SystemMonitor のポーリング）

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、create_broker_api()
  - kabu_client.py — KabuStationClient（httpx + websocket）
  - mock_client.py — MockBrokerClient（開発/テスト用）
  - broker_factory.py — Settings に基づくクライアント生成
  - order_record.py — OrderRecord / OrderState（状態遷移ロジック）
  - order_repository.py — SQLite 永続化層（init_orders_db 等）
  - order_manager.py — 発注フロー（create/send/sync/cancel）
  - reconciler.py — 起動時リコンシリエーション
  - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン・kill）
  - risk_manager.py — RiskManager（Gate1/2/3）

- data/
  - calendar_management.py — JPX カレンダー管理（DuckDB）
  - news_collector.py — RSS ニュース収集（SSRF 対策、正規化）

- monitoring/
  - monitoring_db.py (参照される) — 監視用 DB 初期化 / ログ保存（run_monitoring/run_execution から呼ばれる）

（注）上記以外にも多くの補助モジュールやテストユーティリティが存在する想定です。全ファイルは src/kabusys 以下を参照してください。

設定例（.env の簡易サンプル）
------------------------------
.env の最低限の例:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

※実運用時はプレースホルダ値（_here 等）を置き換えてください。validate_config がプレースホルダ検出で警告を出します。

注意事項 / 運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知や kill flag の設定を確認してください。validate_config は live 時に追加警告を行います。
- run_execution は既存の stop_requested.flag や kill.flag の存在をチェックします。意図せず起動しない・停止しない事象に注意してください。
- Order のクラッシュ耐性を考慮して、OrderSent の状態遷移は 2 フェーズ永続化の設計になっています（詳しくは order_manager.py のコメント参照）。
- リコンシリエーション（Reconciler）は起動時に不整合を自動で補正し、ポジション差分をログに出します。起動ログを必ず確認してください。
- YAML コンフィグを git 管理する場合は機密情報を含めないこと。.env は絶対にコミットしないでください（config_setup でも明記あり）。

トラブルシュート
----------------
- validate_config で PyYAML 未インストールの警告が出る:
  - yaml パーサを有効にするには pip install pyyaml
- 実環境での kabu station 接続エラー:
  - KabuStationClient はローカルの kabuステーションアプリの起動を前提とします。KABU_API_BASE_URL とパスワードを確認してください。
- DuckDB / SQLite 関連のファイルパスエラー:
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合は自動で作成される箇所もありますが、事前に data ディレクトリを作成しておくと安全です。

開発者向けメモ
---------------
- 自動 .env ロードを無効にしてユニットテストを実行したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MockBrokerClient は単体テストでの振る舞い検証に便利です（fill_mode: instant/partial/never/reject）。
- コード内の docstring とコメントが設計上の判断・注意点を多く含んでいます。新機能追加時はコメントの整合性を保ってください。

最後に
------
この README はソースコードから抽出した情報に基づく概要ドキュメントです。運用前には必ず手元で .env と config を設定・検証し、テスト環境で挙動を確認してください。必要であれば README に追記したい項目（例: 追加の実行方法・運用チェックリスト・開発用コマンド等）を教えてください。