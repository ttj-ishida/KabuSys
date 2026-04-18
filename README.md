KabuSys
=======

日本株向けの自動売買システム（モジュール群）の簡易ドキュメントです。  
このリポジトリは取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ／ファクター計算、LLM を使ったニュース解析など、実運用を念頭に置いたコンポーネント群で構成されています。

概要
----
KabuSys は以下を目的とする Python パッケージ群です。

- 注文発行・注文管理・リスク管理を行う ExecutionEngine（実行エンジン）
- システム稼働状況・注文ログ・リスクイベント等を記録する監視（Monitoring）
- ペーパートレード用の分離された DB サポート（テスト環境）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- DuckDB を用いたファクター計算・リサーチモジュール
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP によるセンチメント評価／レジーム判定
- 簡易的な CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

主な機能
--------
- ExecutionEngine：ブローカークライアント経由での発注、注文管理、リスクチェック、実行ログ記録
- Paper trading モード：KABUSYS_ENV=paper_trading により MockBroker を使用し、本番 DB と分離
- Monitoring：system_status / trade_logs / risk_logs / positions / dashboard などの永続化
- Kill Switch：条件（ドローダウン超過やポジション上限超過等）で data/kill.flag を書き込み、ExecutionEngine を停止
- RiskManager / Reconciler / OrderManager：発注前のリスク制御や発注結果整合性チェック
- Portfolio モジュール：候補選定、重み付け（等重・スコア加重）、ポジションサイズ算出（単元株丸め・最大利用率調整）
- Research：DuckDB 接続でモメンタム、ボラティリティ、バリューなどのファクター計算と統計解析機能
- AI モジュール：ニュースを LLM でスコアリング（ai/news_nlp.py）、マクロニュース＋ETF MA によるレジーム判定（ai/regime_detector.py）
- ツール：環境設定ウィザード（config_setup）、設定検証 CLI（validate_config）、Paper Trading 検証レポート（tools/paper_verification_report）

セットアップ手順（ローカル）
-------------------------
1. リポジトリをクローンする:
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストールする（requirements.txt がある場合はそれを利用）。主な依存例:
   pip install duckdb psutil openai

   ※ 本リポジトリに requirements ファイルが無い場合、上記パッケージを少なくともインストールしてください。
   - duckdb: データ解析用 DB
   - psutil: プロセス優先度・リソース取得
   - openai: LLM 呼び出し（ニュース NLP / レジーム判定）
   - （必要に応じて）PyYAML: config 検証で YAML を検証する場合

4. 環境変数設定 (.env) を作成する:
   - 対話式ウィザードを実行して .env を作成できます:
     python -m kabusys.config_setup

   - 必須の主要環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境:
     - KABUSYS_ENV: development | paper_trading | live
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を環境変数に設定（または各関数の api_key 引数で指定）

5. 設定検証（起動前チェック）:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

基本的な使い方
-------------
- ExecutionEngine を起動する:
  python -m kabusys.run_execution

  説明:
  - 起動時にプロセス優先度を高く設定します（utils.process_priority）。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBroker を利用します。実運用（live）では本番 DB を使用します。
  - 起動中は data/stop_requested.flag を置くと安全にスレッドを停止します。
  - kill.flag（Kill Switch）により ExecutionEngine に停止指示を出すことができます。

- Monitoring を起動する（監視ループ）:
  python -m kabusys.run_monitoring

  説明:
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可（秒数）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（monitoring は常に本番 DB パスを参照する設計）。
  - data/stop_requested.flag を置くと監視ループを終了します。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 環境設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

注意・運用上のポイント
--------------------
- .env は絶対にソース管理にコミットしないでください（config_setup のヘッダでも注意喚起あり）。
- paper_trading モードは本番データベースとは分離されます（デフォルト: data/paper_trading.db）。
- Monitoring は常に本番 sqlite_path を使用するため、監視用 DB の運用を考慮してください。
- 停止・強制停止:
  - 管理者が停止したい場合は data/stop_requested.flag（run_*.py が監視しているフラグ）を作成します。
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させます。
- ログ:
  - setup_logging により logs/<app_name>.log に日次ローテーションでログが出力されます（デフォルトログディレクトリ: logs/）。
  - LOG_DIR 環境変数でログディレクトリを変更できます。

設定（主な環境変数）
------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR / PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など多数（config.py を参照）

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定管理
- config_setup.py           — .env 対話式生成ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリングループ起動スクリプト

subpackages:
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

補足（開発者向け）
-----------------
- DB 初期化:
  monitoring_db.init_monitoring_db() は自動的にテーブルと必要なマイグレーション（カラム追加等）を行います。通常はスクリプト起動時に自動で呼ばれます。
- テスト／モック:
  - paper_trading モードや各モジュールの関数は純粋関数化（副作用の少ない設計）が意識されており、ユニットテストやモックで差し替えやすくなっています。
  - OpenAI の呼び出しは内部で分離されており、テスト時は該当関数をパッチして差し替えられます。
- ログ / エラーハンドリング:
  - setup_logging を各起動スクリプトで呼ぶ設計。起動後すぐにプロセス優先度を set_process_priority("high") で上げる処理が組み込まれています（プラットフォーム依存で失敗した場合は警告）。

ライセンス・貢献
----------------
（この README にはライセンス情報は含めていません。必要であればリポジトリルートに LICENSE を置いてください。）

問い合わせ
----------
運用上の質問やバグ報告はリポジトリの Issue を使用してください。README の改善提案も歓迎します。

以上。README を読み、まずは python -m kabusys.config_setup で .env を作成 → python -m kabusys.validate_config で検証 → python -m kabusys.run_execution / python -m kabusys.run_monitoring を順に試してください。