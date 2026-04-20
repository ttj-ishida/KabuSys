KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本レポジトリは以下の主要機能を備えたモジュール群で構成されています。

- 発注実行エンジン（ExecutionEngine）とブローカークライアント抽象化
- 監視サブシステム（System / Trade / Risk の各監視）と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・株数決定・セクター制御）
- 研究・ファクター計算（DuckDB を用いたファクター群・IC 計算など）
- AI 補助モジュール（ニュースセンチメント、レジーム判定：OpenAI API 利用）
- ユーティリティ、ログ設定、環境設定ウィザード、検証スクリプト、レポート生成ツール

主要な設計方針：
- 実行時の環境変数・.env による構成
- DuckDB（分析用）と SQLite（監視／発注履歴用）の明確な分離
- Paper Trading モードでは本番 DB と分離して安全に検証可能
- 外部 API 呼び出し（OpenAI 等）は明示的なキー指定で制御

機能一覧
--------
- 環境セットアップウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- 監視（ポーリング）起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- DuckDB を用いたファクター計算・研究関数（calc_momentum / calc_value / calc_volatility 等）
- ニュース NLP スコアリング（OpenAI 経由）: kabusys.ai.score_news
- 市場レジーム判定（MA + LLM 合成）: kabusys.ai.regime_detector.score_regime
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）

前提／依存
----------
必須（主要）依存ライブラリ:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- PyYAML（config/*.yaml の検証を行う場合、任意）

インストール例（venv 推奨）:
- python -m venv .venv
- source .venv/bin/activate
- pip install -U pip
- pip install duckdb psutil openai pyyaml

（requirements.txt がある場合は pip install -r requirements.txt を利用してください）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ
   - git clone <repo>
   - cd <repo>

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

3. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークン、kabu API パスワード、DB パス等を入力します
   - ウィザードは .env を作成します（.env は絶対に Git にコミットしないでください）

4. 設定検証（必須環境変数等を事前にチェック）
   - python -m kabusys.validate_config
   - 本番移行前に --strict を付けて警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

主な環境変数（要約）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し paper DB（PAPER_TRADING_SQLITE_PATH）に記録
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視のポーリング秒数（run_monitoring で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（実行制御用）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）

使い方（起動・主要コマンド）
-------------------------

1) 発注エンジン（ExecutionEngine）を起動
- 通常（開発/本番）:
  - python -m kabusys.run_execution
- Paper Trading（KABUSYS_ENV=paper_trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合、MockBrokerClient が使われ PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に結果を記録します

停止制御:
- data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します
- Kill Switch（監視）によって data/kill.flag が書かれると ExecutionEngine 停止指示が出されます

2) 監視プロセスを起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL で間隔を秒で指定（例: MONITOR_POLL_INTERVAL=30）
- 監視は常に settings.sqlite_path（監視 DB）を使用してログを永続化します

3) .env の作成・更新（ウィザード）
- python -m kabusys.config_setup

4) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で DB パスを明示可能

プログラムからの利用（API）
-------------------------
例: DuckDB 接続を渡してファクター計算を呼ぶ
- from kabusys.research import calc_momentum
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")
- records = calc_momentum(conn, target_date)

AI 機能（ニューススコアなど）
- from kabusys.ai.news_nlp import score_news
- score_news(conn, date(2026,4,1), api_key="sk-...")

ポートフォリオ構築関数（純関数）
- from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- これらは副作用が無く単体テストしやすい純関数実装です

ログ
----
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテーション）へ出力されます
- LOG_DIR 環境変数で変更可能
- setup_logging(app_name="execution") が標準的な設定呼び出しです

データ・フラグファイル
--------------------
- data/monitoring.db (デフォルト): 監視用 SQLite（init_monitoring_db でテーブル作成）
- data/paper_trading.db: paper_trading モード用 DB（分離）
- data/execution.pid: ExecutionEngine の PID 管理用（設定により使用）
- data/kill.flag: Kill Switch が書く停止フラグ
- data/stop_requested.flag: ユーザが作成して run_* スクリプトを停止させるためのフラグ

ディレクトリ構成（抜粋）
----------------------
ルートパッケージは src/kabusys 以下にあります。主要ファイルを抜粋すると:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数/.env の読み込みと Settings クラス
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (生成されるデータ・ログファイル等)

（注）上記は主要モジュールの抜粋です。実際のコードベースにはさらに補助モジュール・ユーティリティが含まれます。

運用時の注意
-----------
- .env は決してバージョン管理にコミットしないでください（秘密情報を含む）。
- KABUSYS_ENV=live は本番モードです。validate_config の警告をよく確認してください。
- Kill Switch（data/kill.flag）や KILL_FLAG_CLEAR_ON_START の設定は本番運用で特に重要です（誤クリアに注意）。
- Paper Trading は本番 DB と完全分離されるよう設計されていますが、環境変数の指定ミスに注意してください。
- OpenAI API を利用する機能は API キーの漏洩に注意してください。利用料金が発生します。

トラブルシューティング
------------------------
- SQLite / DuckDB 関連のパスが存在しない場合、validate_config が警告を出します。必要に応じてディレクトリを作成してください（logging_setup は自動で logs/ ディレクトリを作成しようとします）。
- psutil によるプロセス優先度設定は権限により失敗する場合があります（警告ログのみ）。
- OpenAI API 呼び出しは 429 / タイムアウト / 5xx に対してリトライ処理を行いますが、それでも失敗した場合はフォールバックロジックにより安全に継続します（例: macro_sentiment=0.0）。

ドキュメント / 追加情報
---------------------
- 各モジュールの docstring に詳細な実装意図と使用例が記載されています。実装側のコメントを参照してください。
- PortfolioConstruction.md / StrategyModel.md 等の設計文書に依存する実装箇所があります（リポジトリ内に設計書がある場合は併せて参照してください）。

ライセンス
---------
- リポジトリに含まれるライセンスファイル（存在する場合）を参照してください。

問い合わせ
----------
- 実装や使い方に関する質問はリポジトリの issue を利用してください。