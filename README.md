README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォーム向けライブラリ群です。  
主な目的は以下です。

- データの集計・ファクター計算（DuckDB を利用）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- 実行エンジン（ExecutionEngine）・発注管理（paper/live 切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- AI（OpenAI）を使ったニュース NLP / レジーム判定の統合
- 開発向けツール（.env ウィザード、設定検証、検証レポート）

このリポジトリはライブラリとしての各モジュール群と、起動用スクリプト（python -m で実行可能）を含みます。

主要機能
--------
- 環境設定読み込み・管理（.env 自動ロード / Settings）
- ExecutionEngine：本番 / ペーパートレード切替、発注・Order 管理、リスク制御
- Monitoring：System / Trade / Risk の定期チェック、ログ永続化（SQLite）
- Kill Switch：閾値を超えた場合に data/kill.flag を書き込み ExecutionEngine を停止
- Portfolio：候補選定、重み計算、ポジションサイズ計算（単元丸め・集約キャップ）
- Research：ファクター計算（Momentum / Volatility / Value）、IC・統計集計
- AI：ニュースのセンチメントスコアリング（OpenAI）と市場レジーム判定
- ユーティリティ：ロギングセットアップ、プロセス優先度設定、各種 CLI ツール
- 開発支援ツール：.env 対話ウィザード、設定検証、Paper Trading 検証レポート生成

セットアップ
----------
前提
- Python 3.8+（ソース内での互換を想定）
- SQLite（標準ライブラリに含まれます）
- 任意で DuckDB、psutil、openai、PyYAML など

推奨手順（ローカル）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - YAML 検証を行いたい場合: pip install pyyaml

   （requirements.txt が無い場合は上記を手動でインストールしてください）

3. .env の準備
   - 対話ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成してプロジェクトルートに配置

4. 環境変数自動ロード
   - デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の挙動（instant|partial|never|reject）

使用法（エントリポイント）
-----------------------

起動スクリプト（モジュール実行）
- 監視ループを起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
  - 監視は監視用 SQLite（settings.sqlite_path）を使用（環境にかかわらず本番 sqlite_path を使う）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag がある場合は起動をスキップ

- 設定検証 CLI
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告を FAIL 扱いにする）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

ツール
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

ライブラリ API の使い方（抜粋）
- AI ニューススコアリング
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト（関数内でニュースウィンドウを計算）
    - api_key が None の場合は OPENAI_API_KEY を参照
- レジームスコア
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
- Research（ファクター）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - 各関数は DuckDB 接続と target_date を受け取り純粋関数として結果を返す
- Portfolio
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

監視・停止関連ファイル（フラグ）
- data/stop_requested.flag: run_monitoring / run_execution が監視する「停止要求」用フラグ（存在すると監視ループやエンジンが停止）
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 停止トリガーとして機能
- data/execution.pid: ExecutionEngine 用 PID ファイルパス（Settings.pid_file_path）

ロギング
-------
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...") を呼び出すことで
  - stdout ストリームハンドラと logs/<app_name>.log への日次ローテーション出力を設定
  - ログディレクトリは引数、環境変数 LOG_DIR、デフォルト "logs" の順で決定
- デフォルトでログは INFO レベル（LOG_LEVEL 環境変数で上書き可能）

データベースとスキーマ
--------------------
- DuckDB: data/kabusys.duckdb（分析用）
- SQLite（監視）: data/monitoring.db（MonitoringDB がテーブルを自動作成）
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に分離して使用）

主なテーブル（monitoring DB）
- system_status: システム稼働ログ（cpu/memory/disk/process_ok）
- trade_logs: 発注イベントログ、latency_ms カラム含む
- positions: 保有ポジション
- risk_logs: リスク関連イベント（DD・ポジション上限など）
- dashboard: ダッシュボード集計（id=1 の単一行）

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys の主要なファイル / パッケージ構成の要約です。

- src/
  - kabusys/
    - __init__.py
    - config.py               # Settings（.env 自動読み込み・検証）
    - config_setup.py         # .env 対話ウィザード
    - validate_config.py      # 設定検証 CLI
    - run_monitoring.py       # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py        # ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py      # ログ設定ユーティリティ
      - process_priority.py   # プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py      # SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py      # （アラート送信の統制）
    - execution/              # 実行エンジン周り（BrokerFactory, ExecutionEngine, OrderManagerなど）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py           # ニュース NLU / OpenAI 呼び出し
      - regime_detector.py    # レジーム判定（MA + マクロセンチメント）
    - tools/
      - paper_verification_report.py

注意点・運用に関する備考
--------------------
- 環境（KABUSYS_ENV）が paper_trading の場合、発注はモック化され、Paper 用 SQLite に記録されます。本番 DB と完全に分離されます。
- run_monitoring は Settings.env に関わらず監視用 sqlite_path（本番）を使います。監視は本番データの安全性・可用性に関係するためです。
- .env ファイルには機密情報（API キー等）が含まれるため、絶対に Git にコミットしないでください（config_setup.py の出力にも注意喚起あり）。
- OpenAI を利用する機能を動かす際は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフェイルセーフ（失敗時のフォールバック）を組み込んでいますが、利用上のコスト・レート制限に注意してください。
- Monitoring / KillSwitch はリスク管理の一部です。設定閾値（ドローダウン比率・最大ポジション数など）は config/*.yaml や環境変数で調整してください。

トラブルシューティング
---------------------
- ログが出力されない / ファイルハンドラ作成に失敗する場合は、ディレクトリ権限や LOG_DIR 環境変数を確認してください。ログディレクトリ作成に失敗しても stdout ログは出力されます。
- .env 自動ロードを無効にしたい（テスト等）は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / PyYAML が未インストールだと一部機能（research の高速クエリ、validate_config の YAML パース検証）が制限されますが、コア機能の一部は動作します（ただし推奨されません）。

ライセンス / 貢献
-----------------
（ここに適切なライセンスや貢献ガイドラインを記載してください。リポジトリに LICENSE ファイルがあればその参照を追加してください。）

補足
----
この README はコード内のドキュメント文字列（docstring）や設定コードを元に要点をまとめたものです。各モジュールの詳細な挙動やパラメータについては、該当ソースファイルの docstring を参照してください。質問や改善点があれば教えてください。