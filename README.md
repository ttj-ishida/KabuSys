KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株を対象とした自動売買システムのコードベースです。
主要な責務はシグナルの読み込み → リスクガード → ブローカー発注 → リコンシリエーション／監視です。
設計は実運用を想定しており、発注永続化（SQLite）、分析用 DB（DuckDB）、監視 DB（SQLite）、
およびブローカー抽象化（実ブローカー / モック）を備えています。

主な設計方針:
- 発注フローはクラッシュ耐性を考慮（2相永続化、Reconciliation）
- リスク管理は 3 段階（Gate1/2/3）
- 環境設定は .env ベース、対話式ウィザードと起動前検証 CLI を提供
- paper_trading（モック）と development（ローカル）を想定。live は注意が必要

機能一覧
--------
- 環境設定ウィザード (.env ファイルの作成/更新) — kabusys.config_setup
- 起動前設定検証（.env / config/*.yaml） — kabusys.validate_config
- ExecutionEngine：シグナル処理 → 発注 → WebSocket push ドレイン — kabusys.run_execution
- SystemMonitor：リソース・監視ポーリングループ — kabusys.run_monitoring
- ブローカー抽象化（BrokerAPIProtocol）／MockBrokerClient／KabuStationClient
- 注文永続化（SQLite）と OrderState マシン
- 起動時リコンシリエーション（Reconciler）
- カレンダー管理／ニュース収集などの Data モジュール

必要要件
--------
- Python 3.10 以上（型アノテーションに | 演算子を利用）
- 推奨／オプションパッケージ:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（validate_config による YAML パース検証用、未インストール時は警告）
  - その他（logging 等は標準ライブラリ）
- SQLite は標準ライブラリ sqlite3 を使用

セットアップ手順
--------------
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
     （用途に応じて他のパッケージや開発用ツールを追加）
4. データディレクトリを準備（必要な場合）
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。実行時に自動作成されることが多いですが、
     権限や構成に応じてあらかじめ用意しておくと安全です。

環境変数（.env）管理
--------------------
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意／推奨の環境変数（例）:
  - KABUSYS_ENV (development | paper_trading | live). デフォルト: development
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - KABU_API_BASE_URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
  - KILL_FLAG_CLEAR_ON_START（0/1）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）

.env の自動読み込み:
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、
  .env を読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

.env 作成: 対話式ウィザード
------------------------
対話式で .env を作成/更新するには:
- python -m kabusys.config_setup
  - 質問に従って値を入力し、最後に保存を確認します。
  - シークレットは表示されません（保存後は .env に平文で書かれますが、リポジトリには絶対コミットしないでください）。

設定検証
--------
起動前に設定状況をチェックする CLI:
- python -m kabusys.validate_config
- --strict を付けると警告も FAIL（exit code 1）として扱います：
  - python -m kabusys.validate_config --strict

このツールは:
- 必須環境変数の有無チェック
- KABUSYS_ENV の妥当性チェック
- LOG_LEVEL, DB パスの親ディレクトリ存在チェック
- config/*.yaml ファイルの有無と（PyYAML があれば）パース検証
- KABUSYS_ENV=live の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）

実行方法
--------
1) 実行エンジン（Execution）
- 実際の発注セッションを開始します（通常はスケジューラから起動）
- 起動:
  - python -m kabusys.run_execution
- 注意:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（本番 DB と分離して PAPER_TRADING_SQLITE_PATH に記録）
  - KABUSYS_ENV=live の場合は BrokerClientFactory で NotImplementedError を補足するため、現状は paper_trading/development を推奨
  - 起動時に data/execution.pid（デフォルト）に PID を書き込み、data/kill.flag で起動停止を制御します

2) 監視ループ（Monitoring）
- システム監視をポーリングで実行します
- 起動:
  - python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）
- 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring は実運用向け）

開発／テスト用（モック）
----------------------
- MockBrokerClient を用いてブローカー非依存の単体テスト・ローカル実行が可能
- 設定:
  - KABUSYS_ENV を paper_trading または development にし、PAPER_FILL_MODE を指定
    - PAPER_FILL_MODE の有効値: instant | partial | never | reject
      - instant: 発注時に全量約定
      - partial: 半額約定（テストで手動で fill_order を呼んで全量約定にできる）
      - never: 注文番号発行後 pending（OrderSentPendingError）
      - reject: 発注拒否（OrderRejectedError）
- BrokerClientFactory.create() が mock を生成するため、外部設定不要で動作します

主要モジュール解説（簡易）
------------------------
- kabusys.config
  - .env 自動ロードロジック、Settings クラス（環境変数をプロパティとして提供）
- kabusys.config_setup
  - .env を対話式に作成するウィザード
- kabusys.validate_config
  - 起動前設定の検証 CLI
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（PID/kill flag 制御、DB 初期化、スレッド実行）
- kabusys.run_monitoring
  - SystemMonitor ポーリングループ起動スクリプト
- kabusys.execution.*
  - broker_api: クライアント Protocol、データモデル、create_broker_api
  - kabu_client: 実際の kabu station REST API クライアント（httpx）
  - mock_client: テスト用のモック実装
  - order_record / order_repository / order_manager: 注文状態管理と永続化
  - execution_engine: シグナル処理メインループ（Gate1-3、WebSocket ドレイン等）
  - reconciler: 起動時の自動復旧・突合
  - risk_manager: 3 段階リスクガード（余力/重複/ポジション上限、レート制限・CB、ドローダウン）
- kabusys.data.*
  - calendar_management: マーケットカレンダー管理と営業日計算
  - news_collector: RSS からニュース収集（前処理・SSRF 対策等）
- kabusys.monitoring.*
  - 監視 DB 初期化・SystemMonitor 実装（run_monitoring で使用）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境設定読み込み（Settings）
- config_setup.py          — .env ウィザード
- validate_config.py       — 起動前検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
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
- data/
  - calendar_management.py
  - news_collector.py
  - (jquants_client など外部連携モジュール)
- monitoring/
  - monitoring_db.py
  - system_monitor.py
- utils/
  - logging_setup.py
  - process_priority.py
- config/                  — 設定 YAML の格納場所（system_config.yaml など）
- data/                    — デフォルトの DB / PID / flag 保存場所（実行時作成されることが多い）

運用上の注意点
--------------
- .env は絶対に Git 等にコミットしないこと（README やテンプレートのみ管理する）
- KABUSYS_ENV=live を設定する場合は十分な確認が必要（本番の発注を行います）
  - 現在 BrokerClientFactory は live を NotImplementedError にしているため注意
- kill.flag（デフォルト data/kill.flag）や PID ファイルを用いた外部停止制御を行います
- validate_config を運用前に必ず実行し、--strict モードで CI 等に組み込むとより安全です

よくあるコマンドまとめ
---------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring

補足
----
- README に書いてある多くの値（DB パス、LOG_LEVEL など）は環境変数で柔軟に変更できます。
- 開発時は KABUSYS_ENV=paper_trading / PAPER_FILL_MODE=instant を設定してモックで安全に動作確認することを推奨します。
- 追加のユーティリティや設定テンプレート（.env.example、config/*.yaml のサンプル）がプロジェクトにあれば併せて参照してください。

以上。必要であれば README にサンプル .env の雛形や起動フローチャート、よくある障害対応（ログの見方、Reconciler が検出する状態など）を追記します。どの情報を詳しく書き足しますか？