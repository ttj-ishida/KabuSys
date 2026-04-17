KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買システム（リサーチ / ポートフォリオ構築 / 発注実行 / 監視 / AI 補助）を想定した Python コードベースです。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）と発注周りのコンポーネント
- 監視（Monitoring）：システム状態・注文滞留・リスク監視、Kill Switch
- リサーチ（Research）：ファクター計算・特徴量解析
- ポートフォリオ構築（Portfolio）：候補選定・重み付け・ポジションサイズ計算
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI 利用）
- ユーティリティ：設定ウィザード・設定検証・各種ツール（ペーパートレード検証レポート等）

主な機能一覧
--------------
- 設定管理:
  - .env 自動読み込み（プロジェクトルート基準）
  - 対話式設定ウィザード (kabusys.config_setup)
  - 設定検証 CLI (kabusys.validate_config)
- 実行/監視:
  - run_execution: 発注エンジン起動（paper_trading 環境では MockBroker を使用し専用 DB に記録）
  - run_monitoring: SystemMonitor をポーリングして監視ログを記録
  - Kill Switch による ExecutionEngine 停止（ファイルフラグ）
- 監視 / アラート:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - LINE プッシュ通知用 AlertManager（トークン未設定時はログ出力のみ）
- リサーチ:
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- ポートフォリオ構築:
  - 候補選定、等金額・スコア加重、リスク調整（セクターキャップ・レジーム乗数）
  - 株数決定（リスクベース / 等分配 / スコアベース）、単元株丸め、aggregate cap
- AI:
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントスコアリング
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースでレジーム判定
- ユーティリティ:
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローンし、Python 仮想環境を作成
   - 推奨: Python 3.9+（コードは型注釈を使用）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必須ライブラリをインストール
   - 使用されている主要パッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - （任意）PyYAML — config/*.yaml の検証に利用
   - 例:
     - pip install duckdb psutil openai requests pyyaml

   ※ requirements.txt がある場合はそちらを使用してください。

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（以下は最低限必要な環境変数の例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...

   - 注意: .env はリポジトリにコミットしないでください。

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトで data/ 以下のファイルを利用します（自動作成されることが多いですが念のため）:
     - data/ — SQLite / DuckDB などのデータファイル保存先
     - data/execution.pid — ExecutionEngine が作成する PID ファイル
     - data/stop_requested.flag — 外部からループ停止を指示するフラグ（run_* スクリプトでチェック）
     - data/kill.flag — Kill Switch 用のフラグ

使い方
------

- 実行エンジン（ExecutionEngine）起動
  - 本番環境 / paper_trading 環境に応じて .env の KABUSYS_ENV を設定してください。
  - 起動:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録（settings.paper_sqlite_path）
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine 内の停止処理によって行われます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。1 未満または不正値はデフォルトにフォールバック。
  - run_monitoring は常に settings.sqlite_path（本番監視 DB）を使って monitoring を行います（KABUSYS_ENV に依存しません）。
  - run_monitoring は data/stop_requested.flag を検出するとループを抜けます。

- 停止・Kill Switch
  - Kill Switch が発動すると data/kill.flag が書かれ、ExecutionEngine はその存在に応じて停止できます（設定により動作）。
  - 手動でクリアする場合:
    - rm data/kill.flag
  - ExecutionEngine の PID ファイル: data/execution.pid

- 設定ウィザード／検証
  - .env の作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール
  - OpenAI API を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
  - 例: kabusys.ai.score_news(conn, target_date, api_key=None) — api_key が None の場合は環境変数を参照します。
  - レート制限やネットワークエラーに対してはバックオフ・リトライ実装がありますが、API キーの管理に注意してください。

設定項目・重要な環境変数
-----------------------
（主要なものを抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード: instant|partial|never|reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI 機能に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定時は送信をスキップ）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_PATH — Kill Switch 用ファイルパス（Settings.kill_flag_path で上書き可能）
- PID_FILE_PATH — ExecutionEngine の pid_file（Settings.pid_file_path）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと説明です（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 初期化 / 永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成／判定
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — LINE Push 通知（クールダウン機構）
  - execution/ (発注周りのコンポーネント群)
    - order_repository.py, order_manager.py, reconciler.py, execution_engine.py, broker_factory.py, ...
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・集約上限処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py — ペーパートレードのレポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity

運用に関する注意点
-----------------
- 本コード内ではファイルフラグ（data/stop_requested.flag・data/kill.flag）を利用して外部プロセスから制御します。ファイルベースの制御は簡易ですが、誤操作に注意してください。
- run_monitoring/run_execution は起動直後にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足や未対応 OS では警告が出ます。
- Paper trading は本番 DB と分離しているため、PAPER_TRADING_SQLITE_PATH を設定し安全にテストできます。
- AI 機能は OpenAI API の利用に伴うコストが発生します。必ず API キーの管理と使用量を確認してください。
- config/*.yaml の検証には PyYAML が必要です。インストールされていない場合は警告になります。

開発者向け
----------
- 各モジュールはなるべく副作用を抑え、テストしやすい形で設計されています（pure function / DB 依存の明確化など）。
- DuckDB コネクションを渡して処理する関数が多く、データ取得は SQL を介して行います。分析やテストは DuckDB にテストデータを入れて実行してください。
- テスト時は OpenAI 呼び出し部分（_call_openai_api）をモックすることを推奨します（news_nlp, regime_detector 内に差し替えポイントあり）。
- monitoring_db.init_monitoring_db は IDEMPOTENT（冪等）なので既存 DB に対して安全に呼べます。マイグレーションの一部（カラム追加）も含まれます。

よく使うコマンドまとめ
--------------------
- .env を作る: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視ループ開始: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン開始: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（コードから呼び出す）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

ライセンス / バージョン
------------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報や貢献ガイドラインが別途ある場合はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本サンプルには含まれていません）。

お問い合わせ
------------
- 実装や設定に関する質問はリポジトリの issue や開発チームの連絡先へお願いします。