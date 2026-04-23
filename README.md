README
=====

概要
----
KabuSys は日本株の自動売買を想定した小規模なシステム基盤です。本リポジトリは発注フロー（ExecutionEngine）、発注状態管理（OrderManager / OrderRepository / OrderRecord）、リスクガード（RiskManager）、リコンシリエーション（Reconciler）、市場カレンダー・ニュース収集等のデータ系ユーティリティ、監視ループなどを含みます。kabuステーション（またはモック）経由での注文送信・状態照会を想定して設計されています。

主な特徴
--------
- 環境設定管理（.env 自動読み込み、対話式ウィザード）
- 起動前設定検証 CLI（必須環境変数や config/*.yaml の存在 / パース確認）
- ExecutionEngine：シグナルプル型の発注エンジン（発注窓口 / WebSocket ドレイン）
- Order 管理：OrderRecord（状態遷移ロジック）・OrderRepository（SQLite 永続化）
- Broker 抽象化：BrokerAPIProtocol / KabuStationClient（実装） / MockBrokerClient（テスト用）
- RiskManager：Gate1/2/3 の 3 段階リスクガード（余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン）
- Reconciler：起動時の OrderSent 照合とポジション差分検査
- 監視プロセス（SystemMonitor）用ループと監視 DB 初期化
- データ系ユーティリティ（DuckDB を利用したマーケットカレンダー管理やニュース収集）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone でチェックアウトしてください。

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb httpx websocket-client defusedxml PyYAML
   - 上記はコード内で使用されている主要ライブラリの例です。requirements.txt がある場合は pip install -r requirements.txt を使用してください。
   - validate_config は PyYAML がない場合 YAML 内容検証をスキップします（警告を出力）。

4. プロジェクトルートに .env を用意
   - 対話式ウィザードで作成できます（下記参照）。
   - もしくは .env.example を参考に手動作成してください（.env.example は本リポジトリ内に存在する想定です）。

5. ディレクトリ作成
   - デフォルトで使われる DB や PID/flag の親ディレクトリを作成しておくと良いです:
     - data/ ディレクトリ（DUCKDB_PATH や SQLITE_PATH の親）
   - ただし多くは起動時に自動作成されることがあります。

環境変数（主なもの）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーションの API パスワード（必須）

任意 / 設定例:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログ出力レベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

.env 自動読み込み
-----------------
- 自動読み込み順序: OS 環境変数 > .env.local > .env
- プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して決定します（CWD に依存しない）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

主要 CLI / 実行方法
------------------

1) 環境設定ウィザード（.env 作成・更新）
   - 実行:
     - python -m kabusys.config_setup
   - オプション:
     - --env-file PATH で保存先を指定可能（デフォルトはプロジェクト直下の .env）
   - 対話形式で入力 → 確認後 .env に保存します。

2) 設定検証 CLI（起動前チェック）
   - 実行:
     - python -m kabusys.validate_config
   - オプション:
     - --strict — 警告も FAIL として exit(1) で終了
   - 検証内容:
     - 必須環境変数の有無 / プレースホルダ検出
     - KABUSYS_ENV の妥当性（development/paper_trading/live）
     - LOG_LEVEL の妥当性
     - DB パスの親ディレクトリ存在確認
     - config/*.yaml（system_config.yaml 等）の存在チェックおよび PyYAML がある場合はパース検証
     - KABUSYS_ENV=live のときの追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）

3) 実行エンジン（Execution）
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - Settings を読み込み、DB 接続（paper_trading なら paper_sqlite_path を使用）
     - Broker クライアントは設定に応じて Mock または（将来的に）Live 実装を提供
     - ExecutionEngine を起動しシグナル処理（8:50-9:10）と WebSocket ドレイン（9:10-15:30）を実行
     - PID ファイルを書き、停止は data/stop_requested.flag の検出や kill.flag によって行われる
     - KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に kill.flag を自動クリア可能（本番は推奨しない）

4) 監視プロセス（Monitoring）
   - 実行:
     - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
     - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB にログを残す（監視専用）

主要な設計メモ（運用上のポイント）
--------------------------------
- Order の状態遷移は OrderRecord と OrderManager で厳密に管理されています。OrderSent の永続化タイミングやクラッシュ時の再同期シナリオ（Reconciler）を考慮した 2 相永続化が行われます。
- DuplicateOrder（同一 signal_id の active 注文重複）は DB 制約とアプリ側チェックで防止します。
- RiskManager は 3 段階（Gate1: シグナル・余力等、Gate2: レート制限・サーキットブレーカー、Gate3: ドローダウン）で発注可否を判定します。
- MockBrokerClient を利用することで kabuステーション が無くてもローカルで動作確認・単体テストが可能です（fill_mode: instant/partial/never/reject）。
- .env は絶対に Git にコミットしないでください（config_setup が注意文を出力します）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — 監視ループ起動スクリプト
  - execution/
    - broker_api.py — BrokerAPIProtocol、データモデル、ファクトリ
    - kabu_client.py — kabuステーション REST API クライアント実装
    - mock_client.py — テスト用 MockBrokerClient
    - broker_factory.py — Settings に基づくブローカー生成
    - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン）
    - order_record.py — OrderRecord（状態遷移）
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — OrderManager（外向け API、発注フロー）
    - reconciler.py — 起動時の再同期処理
    - risk_manager.py — 3 段階リスクガード
    - (その他: order_*、risk config 等)
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ関数（参照される）
    - system_monitor.py — SystemMonitor（監視ロジック）（参照される）
  - data/
    - calendar_management.py — 市場カレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集（defusedxml 等で安全に実装）
  - utils/
    - logging_setup.py — ロギングの初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

補足（よくある運用タスク）
--------------------------
- .env を生成 → python -m kabusys.config_setup
- 設定チェック → python -m kabusys.validate_config [--strict]
- 実際に発注テスト（ローカル / CI） → KABUSYS_ENV=paper_trading + MockBrokerClient（デフォルトで Mock が選択されます）
- 本番運用時は KABUSYS_ENV=live に注意（validate_config は live 時の重要な警告を出します）
- 監視・停止: data/stop_requested.flag の作成で優雅に停止。kill.flag は即時 kill 判定に使われ、起動時の自動クリアは KILL_FLAG_CLEAR_ON_START で制御。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE を参照してください（存在する想定）。
- バグ修正・機能追加は PR を送ってください。議論の前に issue を立てていただけると助かります。

以上。必要であれば、README に含める動作フロー図や具体的な .env のサンプル（例：.env.example の抜粋）、実運用チェックリストなども追加できます。どの情報を追加したいか教えてください。