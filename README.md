KabuSys — 日本株自動売買システム
================================

本ドキュメントはリポジトリ内の主要機能と使い方をまとめた README です。
以下はコードベース（src/kabusys）から抽出した要点を日本語で整理したものです。

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
主な役割は次のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・研究（research）
- ポートフォリオ構築、ポジションサイズ計算（portfolio）
- ExecutionEngine による発注処理（実口座 / ペーパートレード）
- 監視モジュール（system / trade / risk）による稼働監視と Kill Switch
- ニュースの NLP（OpenAI）を用いたセンチメント計算（ai）
- ペーパートレードの検証レポート作成ツール

主な特徴・機能
---------------
- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - Settings クラスによる環境変数ラッパ
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 監視
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading 用 DB/Mock を使用）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - Kill Switch: 監視結果に基づき data/kill.flag を書き込んで ExecutionEngine を停止可能
  - 停止制御: data/stop_requested.flag を置くと起動中ループを終了
- データベース
  - DuckDB（分析用）: デフォルト data/kabusys.duckdb
  - SQLite（監視 / 履歴）: デフォルト data/monitoring.db
  - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
- 研究・リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、ファクターサマリー等
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重、セクターキャップ、ポジションサイジング（lot 単位）
- AI（LLM）
  - news_nlp: raw_news を集約して OpenAI で銘柄別センチメントを計算、ai_scores に格納
  - regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成して日次レジーム判定
- ツール
  - Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.10+（コードは型ヒントに Union | を使用）
- 必要なライブラリ（例: duckdb, psutil, openai, PyYAML（任意）など）

1. クローン / 依存インストール
   - リポジトリをクローンし、仮想環境を作成して依存パッケージをインストールしてください。
     例:
       python -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt
     （requirements.txt がない場合は duckdb, psutil, openai, PyYAML 等を個別にインストール）

2. 環境変数（.env）作成
   - 対話式ウィザード:
       python -m kabusys.config_setup
     これによりプロジェクトルートに .env が生成されます。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 重要な環境変数（主なものとデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - KILL_FLAG_CLEAR_ON_START: 0 or 1
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - OPENAI_API_KEY: OpenAI API を使う機能で必要
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
   - 自動ロード:
     - .env / .env.local は Settings モジュールで自動ロードされます（プロジェクトルート検出に .git または pyproject.toml を使用）。
     - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

3. 設定検証（任意だが推奨）
   - 作成した .env や config/*.yaml を検証:
       python -m kabusys.validate_config
     --strict を付けると警告も失敗扱い（exit 1）になります。

4. DB（DuckDB / SQLite）初期化
   - 実行スクリプトで必要なテーブルは起動時に作成（init_monitoring_db 等）されます。事前に空の data ディレクトリを作成しておくと良いです。
   - ログディレクトリも作成されます（logs/ がデフォルト）。

使い方
------
基本的な実行コマンド（プロジェクトルートで実行）:

- 実行エンジン起動（発注プロセス）
    python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 実行中は data/execution.pid に PID を書き込みます。

- 監視ループ起動（SystemMonitor）
    python -m kabusys.run_monitoring

  補足:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は Settings が示す sqlite_path（monitoring DB）に接続します（環境に依らず本番の sqlite_path を使用）。
  - data/stop_requested.flag が作られるとループを終了します。

- 設定ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    --db オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

ログとローテーション
-------------------
- ログはデフォルトで stdout（コンソール）とファイル出力（logs/<app_name>.log）に出ます。
- 日次ローテーション・30 日分保持（TimedRotatingFileHandler）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

停止・Kill Switch
-----------------
- 手動停止トリガ:
  - data/stop_requested.flag: run_execution や run_monitoring のループを停止させるために使用（起動スクリプトで参照）。
  - data/kill.flag: KillSwitch が書き込むファイル。存在すると ExecutionEngine 停止シグナルとして扱われる（Settings.kill_flag_path でパス指定可）。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で許可できますが、本番では推奨されません。

AI（OpenAI）機能
-----------------
- news_nlp.score_news および ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）が必要です。
- API 呼び出しはリトライ/バックオフやレスポンス検証を行うように実装されていますが、API キー未設定時は例外を発生します。

主要ファイルとディレクトリ構成
------------------------------
以下は src/kabusys 以下の主要ファイルを抜粋したディレクトリ構成（簡易）です。

- src/kabusys/
  - __init__.py                 （パッケージ定義、__version__）
  - config.py                   （Settings クラス、.env 自動ロード）
  - config_setup.py             （対話式 .env ウィザード）
  - validate_config.py          （設定検証 CLI）
  - run_execution.py            （ExecutionEngine 起動スクリプト）
  - run_monitoring.py           （SystemMonitor ポーリング起動スクリプト）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - execution/                   （ExecutionEngine, OrderManager 等：起動時に使用）
  - data/                        （デフォルト DB / フラグ / pid を置くディレクトリ）
  - logs/                        （ログファイルの出力先デフォルト）

（注）上記はコードベースから抜粋した主要モジュールです。細かいファイルはリポジトリを参照してください。

重要な設計上の注意点
--------------------
- .env は絶対にリポジトリへコミットしないこと（config_setup.py にも警告あり）。
- KABUSYS_ENV が live の場合は設定を慎重に扱ってください（validate_config は本番ガードを含みます）。
- Paper Trading モードは本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を用いる機能は API コストとレイテンシ、失敗時のフォールバックを考慮してください（実装は部分的にフォールバックあり）。
- プロセス優先度や CPU affinity の設定はセットアップ時に行われますが、OS によっては失敗する場合があります（権限の問題など）。

よく使うコマンドまとめ
---------------------
- .env 作成:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
- ExecutionEngine 起動:
    python -m kabusys.run_execution
- Monitoring 起動:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

最後に
------
この README はリポジトリ内のコードを元に手早く導入・運用できるよう要点をまとめたものです。実際の運用やデプロイ時には config/*.yaml（もしあれば）やログ、データベースのバックアップ方針、監視アラートの受信先（LINE 等）の設定を必ず確認してください。