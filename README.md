KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を目的とした軽量なフレームワークです。  
シグナル駆動の発注エンジン、ブローカークライアント（kabuステーションのラッパーおよびモック実装）、監視（Monitoring）、リスク管理、リコンシリエーション機能などを提供します。本リポジトリはコアの実装（発注フロー、注文状態管理、DB 永続化、カレンダー管理、ニュース収集など）を含みます。

主な機能
--------
- 簡易設定ウィザード（.env の対話式生成）  
- 起動前の設定検証 CLI（環境変数と config/*.yaml のチェック）  
- ExecutionEngine：シグナル読み取り→Gate1/2によるリスクチェック→発注→pushドレインのセッション実行  
- Broker API 抽象化（Protocol）／MockBrokerClient（テスト用）／KabuStationClient（kabuステーション向け実装）  
- OrderState を中心とした状態遷移ロジックと SQLite 永続化（orders テーブル）  
- 起動時の Reconciler による OrderSent の突合・ポジション差分検出  
- RiskManager：Gate1(シグナル) / Gate2(実行) / Gate3(メトリクス) の 3段階リスクガード  
- 監視プロセス（SystemMonitor）を起動する run_monitoring スクリプト  
- データ系ユーティリティ（DuckDB を使ったマーケットカレンダー管理、ニュース収集等）

動作要件
--------
- Python 3.10 以上（Union 型 A | B を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML （config のパース検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, pathlib など

（requirements.txt が無い場合は上のパッケージを仮想環境にインストールしてください）

セットアップ手順（Quickstart）
----------------------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話に従って必要な値（J-Quants トークン、Kabu API パスワード等）を入力します。
     - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

主要な実行スクリプト
--------------------
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（実運用／テスト）
  - python -m kabusys.run_execution
    - KABUSYS_ENV により動作が変わります（paper_trading / development はモック、live は未実装の旨エラー）。
    - 停止は data/stop_requested.flag ファイルを作成することで行えます（同梱の仕組み）。
- 監視ループ
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1）

使い方例（よく使う流れ）
---------------------
1. .env を用意（config_setup）
2. validate_config で問題がないかチェック
3. 実運用（paper_trading や development）で挙動を確認
   - python -m kabusys.run_execution
   - 別プロセスで監視を起動: python -m kabusys.run_monitoring
4. ログや data ディレクトリ内のファイル（PID、flag、DB）で実行状態を監視・制御

開発者向け API
---------------
- 設定取得:
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.duckdb_path などのプロパティ経由で取得
- ブローカークライアント生成:
  - from kabusys.execution import create_broker_api もしくは BrokerClientFactory.create(settings)
  - テスト時は mock=True を使うか KABUSYS_ENV を paper_trading に設定すると MockBrokerClient を使用します。
- ExecutionEngine の単体テスト:
  - EngineConfig を作成して ExecutionEngine(...).run_session() を呼ぶか、内部メソッド（_process_signals / _drain_push_queue）を直接テストできます。

停止・安全対策
--------------
- 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成すると run_execution / run_monitoring はループを終了します。
- Kill Switch: 設定または RiskManager の判定で kill_switch() が発動すると、全 active 注文をキャンセルします。
- 起動時の kill.flag 存在チェック:
  - settings.kill_flag_clear_on_start が 1 の場合は自動クリアし起動（危険なので本番では 0 推奨）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
  - パッケージ定義、バージョン等
- config.py
  - .env 自動読み込み、Settings クラス（環境変数プロパティ）
- config_setup.py
  - 対話式 .env 生成ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine を起動するエントリスクリプト
- run_monitoring.py
  - SystemMonitor をポーリングループで実行するスクリプト

サブパッケージ: execution/
- broker_api.py
  - BrokerAPIProtocol、データモデル、例外、ファクトリ
- kabu_client.py
  - KabuStationClient（kabuステーション REST / websocket 実装）
- mock_client.py
  - MockBrokerClient（テスト用）
- broker_factory.py
  - Settings に基づいてクライアントを返すファクトリ
- order_record.py
  - OrderState 列挙と OrderRecord（状態遷移ロジック）
- order_repository.py
  - SQLite による永続化レイヤ（orders テーブル）
- order_manager.py
  - OrderRecord と Repository / Broker を繋ぐ外向き API（create/send/sync/cancel）
- execution_engine.py
  - ExecutionEngine 本体（セッション制御・push ドレイン）
- reconciler.py
  - 起動時のリコンシリエーション（OrderSent 照合、ポジション差分）

サブパッケージ: data/
- calendar_management.py
  - DuckDB ベースのマーケットカレンダー管理ユーティリティ
- news_collector.py
  - RSS を収集して正規化・DB 保存するモジュール
- （jquants_client 等、外部 API を扱うモジュールが想定）

サブパッケージ: monitoring/, utils/, strategy/, execution/（他）
- 監視やログセットアップ、プロセス優先度設定、戦略関連はそれぞれのモジュールに実装されます（README の抜粋には載せきれないため、コードコメントを参照してください）。

注意事項・運用上のヒント
-----------------------
- .env は機密情報を含むため Git に含めないでください（config_setup のヘッダにも警告あり）。  
- KABUSYS_ENV=live は本番モードとして扱われます。現在コードの一部（BrokerClientFactory の live ブランチ等）はまだ未実装や注意喚起があります。まずは paper_trading / development で十分に検証してください。  
- validate_config では PyYAML がインストールされていると config/*.yaml のパースチェックを行います。インストールしておくと安心です。  
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、事前に data/ ディレクトリを用意しておくと安全です。  
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます。

ライセンス等
------------
- 本 README ではライセンス表記は含めていません。実運用・配布する際は適切なライセンスファイル（LICENSE）を追加してください。

---

必要であれば README にサンプル .env（例示）や単体テストの実行方法、詳細な設定値一覧（全 env 変数の表）を追加します。どの情報を優先して追加しますか？