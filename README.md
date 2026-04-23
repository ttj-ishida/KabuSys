README
======

概要
----
KabuSys は日本株の自動売買を想定した小規模なトレーディングフレームワークです。  
主に以下を提供します。

- 環境設定ウィザード（.env 作成 / 更新）
- 起動前の設定検証 CLI
- 実行エンジン（ExecutionEngine）によるシグナル→発注フロー
- ブローカー抽象（Mock / kabuステーション 実装）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3段階）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor 起動スクリプト）
- データ系ユーティリティ（カレンダー管理、ニュース収集など）

本リポジトリはライブラリ／実行スクリプト群が src/kabusys 配下に実装されています。

主な機能
--------
- 環境設定ウィザード（kabusys.config_setup）
  - 対話式に .env を作成・更新。シークレット項目はマスク表示。
- 設定検証 CLI（kabusys.validate_config）
  - .env や config/*.yaml（存在・パース）を起動前にチェック。--strict により警告も FAIL 扱い。
- 実行エンジン（kabusys.run_execution / ExecutionEngine）
  - DuckDB 経由でシグナルを読み、OrderManager を通じて発注。
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）。
  - paper_trading では MockBroker を使用し、本番 DB と分離。
  - PID 管理 / kill flag / WebSocket push ドレイン / ポジション記録。
- 監視ループ（kabusys.run_monitoring）
  - 定期ポーリングでシステムメトリクス等を監視。MONITOR_POLL_INTERVAL で間隔を調整可能。
- ブローカー抽象（kabusys.execution.broker_api）
  - BrokerAPIProtocol を定義。create_broker_api() で実装を生成（mock or KabuStationClient）。
- Mock ブローカー（kabusys.execution.mock_client）
  - テスト向け。一部即時約定 / 部分約定 / reject / never fill のモードをサポート。
- 注文永続化（order_repository）
  - SQLite を用いた orders テーブル。active 注文の部分ユニークインデックスを備える。
- 注文状態モデル（order_record）
  - 状態遷移検証を行う OrderRecord（不正遷移は例外）。
- リスク管理（risk_manager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視）
- リコンシリエーション（reconciler）
  - 再起動時に OrderSent な注文をブローカーと同期し、ポジション差分を検出。
- データユーティリティ（calendar_management, news_collector）
  - JPX カレンダー処理、RSS ニュース収集（正規化・SSRF対策・defusedxml使用）など。

前提 / 必要環境
---------------
- Python 3.10 以上（型アノテーションに | 演算子などを使用）
- 推奨パッケージ（主に動作・開発用）:
  - httpx
  - websocket-client
  - duckdb
  - PyYAML (validate_config の YAML 検証用。ただし未インストールでもウォーニングのみ)
  - defusedxml (news_collector 用)
- SQLite（Python 標準の sqlite3 を使用）
- kabuステーション連携を行う場合は kabuステーションアプリ（ローカル）とネットワーク接続が必要

インストール（例）
-----------------
1. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate

2. 必要パッケージをインストール（最低限の例）
   pip install --upgrade pip
   pip install httpx websocket-client duckdb PyYAML defusedxml

   （requirements.txt を提供している場合はそれを使ってください）

セットアップ手順
--------------
1. プロジェクトルートに移動（pyproject.toml または .git がある想定）
2. .env を用意する:
   - 対話式で作成: python -m kabusys.config_setup
     → 対話に従って .env を生成します（.env は絶対に Git にコミットしないでください）。
   - 既存の .env がある場合は .env.local で上書き可能。

3. 起動前検証（推奨）:
   python -m kabusys.validate_config
   必要に応じて --strict を付けると警告もエラー扱いになります。

4. DB 初期化:
   - Execution / Monitoring は起動時に必要なテーブルを初期化する処理（init_orders_db / init_monitoring_db）を呼びます。通常は各起動スクリプトが自動で担います。

主な環境変数
---------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり / オプション）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL: kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用
- KILL_FLAG_CLEAR_ON_START: 0 / 1（本番で 1 にすると危険 — 起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading のモック約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等

（Settings クラスで環境変数を読み込み、未設定時は例外を投げるものがあります）

使い方
------
- 環境設定ウィザード（対話式 .env 作成）
  python -m kabusys.config_setup
  オプション: --env-file を指定して保存先を変えられます。

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（本番 / テストで KABUSYS_ENV に応じて動作）
  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading（または development）では MockBroker を使用します。
  - KABUSYS_ENV=live は未実装の部分があり、NotImplementedError を投げる箇所があります（BrokerClientFactory）。

- 監視ループ起動
  python -m kabusys.run_monitoring
  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（デフォルト 60 秒）。

- 開発 / テスト:
  - MockBrokerClient を直接インスタンス化してユニットテストできます（fill_mode を指定して挙動を切替可）。
  - ExecutionEngine.run_session() はテストで内部メソッド（_process_signals / _drain_push_queue）を直接呼んで検証できます。

プロセス制御 / ファイル
---------------------
- PID ファイル: デフォルト data/execution.pid（Settings.pid_file_path）
- 停止フラグ: data/stop_requested.flag（存在すると監視・実行ループは終了します）
- Kill flag: data/kill.flag（存在時は ExecutionEngine 起動を拒否するか、KILL_FLAG_CLEAR_ON_START によって振る舞いが変わります）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み / Settings クラス（.env 自動読み込み）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- execution/
  - __init__.py
  - broker_api.py          — BrokerAPIProtocol / データモデル / ファクトリ
  - broker_factory.py      — Settings を参照して適切なクライアントを生成
  - kabu_client.py         — kabuステーション向け HTTP/WebSocket 実装
  - mock_client.py         — テスト用モック実装
  - order_record.py        — OrderRecord / 状態遷移ロジック
  - order_repository.py    — SQLite 永続化層（orders テーブル）
  - order_manager.py       — OrderManager（DB + broker）発注フロー
  - execution_engine.py    — ExecutionEngine（シグナル処理 / push drain / kill switch）
  - reconciler.py          — リコンシリエーション（OrderSent の同期 / ポジション照合）
  - risk_manager.py        — RiskManager（Gate1/2/3）
- monitoring/
  - monitoring_db.py       — 監視 DB 初期化・ログ関係（参照される）
  - system_monitor.py      — SystemMonitor（実装あり）
- data/
  - calendar_management.py — JPX カレンダー管理 / next_trading_day 等
  - news_collector.py      — RSS ニュース収集（SSRF 対策・正規化）
- utils/
  - logging_setup.py       — ロギング設定ユーティリティ
  - process_priority.py    — プロセス優先度設定ユーティリティ

注意事項 / 運用上のベストプラクティス
----------------------------------
- .env は機密情報を含むため、絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START などを慎重に確認してください。validate_config は live 時の追加警告を出します。
- paper_trading は MockBroker を使用して本番 DB と分離するため、安全に動作検証できます。
- Reconciler は再起動・クラッシュ後の一貫性回復に重要です。ExecutionEngine 起動時に呼び出されます。
- レート制限やサーキットブレーカーは RiskManager が担うため、API の障害や異常で自動的に保護されます。

ライセンス / 貢献
-----------------
（このテンプレートにはライセンス表記が含まれていません。必要に応じて LICENSE ファイルを追加してください。）

補足
----
README に記載した内容はコード（src/kabusys/*）の実装に基づく要約です。各モジュールの詳細な仕様やパラメータについては該当ファイルの docstring を参照してください。質問や実行上の問題があれば、該当モジュール名と発生しているエラーを添えて問い合わせてください。