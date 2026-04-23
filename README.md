KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアライブラリ群です。
本 README は開発者向けにプロジェクト概要、主要機能、セットアップ手順、使い方（起動スクリプト／ツール）、
およびディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は以下の役割を持つコンポーネント群で構成されています。

- ExecutionEngine: 発注、注文管理、リスク管理、約定再突合せなどの実行ロジック
- Monitoring: システム状態、注文状況、リスク（ドローダウンやポジション数）を定期監視しアラート／Kill Switch を運用
- Research / Data: DuckDB を利用したファクター計算・研究用モジュール（価格・財務データ参照）
- AI モジュール: OpenAI を用いたニュースの NLP 評価や市場レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ロギング設定、プロセス優先度設定など

主要機能一覧
-------------
- 環境管理
  - .env の自動ロード（.env / .env.local）と Settings API（kabusys.config）
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）

- 実行 / 監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB に完全分離保存
    - プロセス優先度を高く設定して実行
  - Monitoring 起動スクリプト（run_monitoring.py）
    - 定期ポーリングで System / Trade / Risk のチェックを実行
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
    - 監視は常に本番（production）用 sqlite_path を使用

- 監視・Kill Switch
  - MonitoringDB（SQLite）に system_status / trade_logs / positions / risk_logs / dashboard を保持
  - KillSwitch（kill.flag）により ExecutionEngine 停止シグナルを発行
  - stop_requested.flag により外部から実行プロセスを安全停止可能

- ポートフォリオ構築（純関数）
  - 候補選定、等配分／スコア加重、ポジションサイズ計算、セクター上限・レジーム調整

- 研究・AI
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - OpenAI を用いたニュースセンチメント集計（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順（開発環境）
--------------------------
以下は一般的なセットアップ手順の例です。プロジェクトに requirements ファイルが無い場合は必要なパッケージを個別にインストールしてください。

1. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージ（例）
   - pip install duckdb psutil openai PyYAML
   - （実行環境によって追加で必要なパッケージがあるかもしれません）

3. プロジェクトルートで .env を用意
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照してください）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. 初回起動用ディレクトリ等（任意）
   - データ／ログディレクトリを作成
     - mkdir -p data logs

主要な環境変数（主要なデフォルト値を併記）
-----------------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- PAPER_TRADING_SQLITE_PATH (paper_trading DB): data/paper_trading.db
- SQLITE_PATH (監視 DB): data/monitoring.db
- DUCKDB_PATH (分析 DB): data/kabusys.duckdb
- LOG_LEVEL: INFO（例: DEBUG, INFO, WARNING）
- LOG_DIR: logs（ログを保存するディレクトリ）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方（主要スクリプト）
-----------------------

1) 実行エンジン（ExecutionEngine）起動
- コマンド:
  - python -m kabusys.run_execution
- 動作概要:
  - Settings を読み込み、適切な SQLite（paper_trading 時は専用 DB）と DuckDB に接続
  - BrokerClientFactory により本番または MockBroker を生成（KABUSYS_ENV に依存）
  - ExecutionEngine をデーモンスレッドで実行し、stop_requested.flag を監視して終了

- 停止:
  - 外部から data/stop_requested.flag を作成すると実行中のエンジンにより検出され停止します
  - monitoring 側が条件を満たした場合 kill.flag を書き込んで停止させる仕組みもあります

2) 監視プロセス起動
- コマンド:
  - python -m kabusys.run_monitoring
- 動作概要:
  - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60 秒）
  - SystemMonitor / TradeMonitor / RiskMonitor を用いてチェック
  - 必要に応じて KillSwitch を書き込み（kill.flag）および AlertManager で通知

3) 設定ウィザード（.env の生成）
- コマンド:
  - python -m kabusys.config_setup
- 対話で .env を作成・更新します

4) 設定検証
- コマンド:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

5) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 引数:
  - --db で SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

6) AI / 研究機能の利用例（プログラムから呼ぶ）
- 例: ニューススコアを生成して ai_scores に書き込む
  - Python スクリプト内で:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - count = score_news(conn, target_date=datetime.date(2026,4,20), api_key="YOUR_OPENAI_KEY")

停止ファイル / Kill スイッチ
--------------------------
- data/stop_requested.flag
  - run_execution / run_monitoring がループを終了するための外部停止フラグ（存在すると起動時に起動しない場合あり／実行中に検出して停止）
- data/kill.flag
  - Monitoring の KillSwitch が書き込むファイル。ExecutionEngine に対して即時停止を要求する意図のフラグ
- PID ファイル:
  - data/execution.pid 等、ExecutionEngine が PID を書き出すことで外部監視や停止に使える

ロギング
--------
- ロガーは共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用して初期化されます
- デフォルト: logs/<app_name>.log 日次ローテーション（30日保持） + コンソール出力（stdout）
- LOG_DIR 環境変数でログディレクトリを変更可能

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys の主要なファイルと役割です（完全な一覧ではありません）。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — Settings クラス（.env 自動読み込み・環境変数ラッパ）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト

  - execution/  — Execution 関連（Engine, OrderManager, RiskManager 等）※詳細実装は個別ファイル
  - monitoring/
    - monitoring_db.py — SQLite による監視データ永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 複数モニタの束ね（run loop）
    - kill_switch.py, alert_manager.py — Kill Switch / 通知管理
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・上限・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム／ボラティリティ／バリュー等の計算（DuckDB）
    - feature_exploration.py — IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント評価（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

補足・運用上の注意
-----------------
- KABUSYS_ENV=paper_trading のとき、発注は MockBroker を使い paper_trading DB に完全分離されます。本番 DB を誤って汚さないよう確認してください。
- monitor（run_monitoring）は監視用 DB（SQLITE_PATH）を使用します。Monitoring は起動時に常に本番 sqlite_path を使う設計です（環境に依存せず本番監視を行うため）。
- OpenAI 関連の API 呼び出しはエラー時にフォールバックする実装がされていますが、APIキーの管理（OPENAI_API_KEY）は適切に行ってください。
- .env は機密情報を含むため Git 等にコミットしないでください（config_setup でもヘッダにその旨が書かれます）。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると Kill Flag が自動クリアされるため危険です（推奨は 0）。

FAQ / トラブルシューティング（よくある項目）
-------------------------------------
- 「.env が自動で読み込まれない」
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 がセットされていると自動ロードを無効化します。テスト時はこの変数を使います。
  - プロジェクトルートが自動検出できない場合（.git も pyproject.toml も無い）自動ロードはスキップされます。

- 「ログファイルが生成されない」
  - LOG_DIR 環境変数を確認、あるいはログディレクトリ作成権限を確認してください。作成に失敗するとコンソールのみ出力になります。

- 「Execution が起動しない / すぐ終了する」
  - data/stop_requested.flag が既に存在していると起動をスキップします。起動前に該当フラグを削除してください（監視から書かれる可能性あり）。

その他
-----
より詳しい設計文書や運用手順（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも参照してください。

何か特定の部分（例: ExecutionEngine の構造や OrderManager の API、DuckDB テーブルスキーマ、AI モジュールの挙動）について詳しい README を作成したい場合は、対象箇所を指定してください。必要に応じてコマンド例や環境変数テンプレート、運用チェックリストを追加で作成します。