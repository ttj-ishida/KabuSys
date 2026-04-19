README
======

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本プロジェクトは以下の主要機能を備え、実運用（live）、ペーパートレード（paper_trading）、開発（development）向けに設定を切り替えて利用できます。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視（Monitoring）: プロセスの生存、システムリソース、データ鮮度、取引リスクの継続的監視
- キルスイッチ（Kill Switch）による自動停止（フラグファイル）
- ポートフォリオ構築、ポジションサイジング、セクター制約などの純粋関数群
- リサーチ/ファクター計算（DuckDB を用いた時系列ファクター）
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- Paper Trading の検証レポート生成ツール
- .env 対話式ウィザード、設定検証ユーティリティ

主な設計方針は「本番データへの不必要なアクセスを避ける」「ルックアヘッドバイアス回避」「失敗時はフェイルセーフで継続する」です。

機能一覧
--------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - kabusys.config.Settings: 環境変数/.env を一元管理
  - python -m kabusys.config_setup : .env 対話式ウィザード
  - python -m kabusys.validate_config : 設定検証 CLI（--strict オプションあり）
- 監視
  - MonitoringEngine による監視ループ
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / Alert 管理
  - 監視ログは SQLite（settings.sqlite_path）へ永続化（monitoring_db.init_monitoring_db によりテーブル作成）
- Execution / 発注周り
  - BrokerClientFactory によるブローカークライアントの切替（paper_trading 時は Mock）
  - OrderRepository / OrderManager / ExecutionEngine / Reconciler / RiskManager
  - paper_trading 環境は paper_sqlite_path（デフォルト data/paper_trading.db）へ完全分離して記録
- ポートフォリオ
  - 候補選定（select_candidates）、重み計算（等分／スコア加重）
  - ポジションサイジング（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- リサーチ
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials を基にファクター算出
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価と統計
- AI（OpenAI 統合）
  - kabusys.ai.score_news: ニュースを統合して銘柄ごとにセンチメントを ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime: マクロセンチメント + ETF MA を合成して市場レジーム判定・書き込み
  - OpenAI APIキー（OPENAI_API_KEY）を利用
- ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成（期間指定可）

前提（Prerequisites）
--------------------
- Python 3.10 以上（PEP 604 の型 | を使用）
- pip
- SQLite（標準で付属）
- 推奨 Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML パーサを使う場合）
  
インストール例:
  pip install duckdb psutil openai pyyaml

プロジェクトのセットアップ
------------------------
1. リポジトリをクローン／展開
   - 例: git clone <repo_url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai pyyaml

   （パッケージ一覧が requirements.txt にまとまっている場合は pip install -r requirements.txt を使用）

4. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（.env.example を参照）

   必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要なオプション環境変数
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading の場合に使用）
   - OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp / regime_detector）
   - LOG_LEVEL, LOG_DIR
   - PAPER_FILL_MODE: paper_trading のモック成行充足挙動（instant, partial, never, reject）
   - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に data/kill.flag を自動クリアする (0|1)

5. データディレクトリやログディレクトリの作成（必要に応じて）
   - デフォルトでログは logs/ に出力されます。自動で作成されますが権限が必要な場合は手動で作成してください。
   - data/ 以下に SQLite 等が作成されます。

使い方（起動・コマンド）
----------------------

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL とする）: python -m kabusys.validate_config --strict

- .env 対話式セットアップ
  - python -m kabusys.config_setup

- ExecutionEngine を起動（デフォルト: settings.env に従う）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH に結果が記録されます。
  - 起動中の PID は data/execution.pid に書き込まれます。
  - 停止: data/stop_requested.flag を作成すると起動ループは停止します（run_execution と run_monitoring 共通の停止フラグ）。KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止シグナルを発行します。

- Monitoring（ポーリング）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き（デフォルト 60 秒）。
  - 監視は settings.sqlite_path を常に使用（monitoring は環境に依存せず本番 sqlite_path を参照する点に注意）。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（デフォルトは env または data/paper_trading.db）

- AI / リサーチ関数（プログラム内呼び出し）
  - ニューススコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")  # api_key を None にすると環境変数 OPENAI_API_KEY を使用
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
  - ファクター計算（研究モジュール）:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    calc_momentum(duckdb_conn, target_date)

運用上の注意
------------
- KABUSYS_ENV=live の場合は実際に発注が行われます。設定・キー類は厳重に扱ってください。
- Kill Switch（data/kill.flag）を書き込むと ExecutionEngine を停止させる仕組みがあります。KILL_FLAG_CLEAR_ON_START の値を慎重に設定してください（本番では 0 推奨）。
- monitoring は常に settings.sqlite_path を使うため、monitoring 用 DB のパス設定に注意してください。
- OpenAI API を使用する機能は API 呼び出しに失敗した場合にフェイルセーフ（スコアやセンチメントを 0 にするなど）で継続する設計ですが、APIキーの漏洩・コストには留意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR で出力先を変更できます。

ディレクトリ構成
----------------
（プロジェクトルートが存在し、src/kabusys にパッケージが格納されている想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数/.env 読み込みと Settings
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリングスクリプト
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層
      - system_monitor.py          — システム監視ロジック
      - risk_monitor.py            — ドローダウン / ポジション上限監視
      - trade_monitor.py           — （取引監視モジュール; 参照あり）
      - monitoring_engine.py       — 各 Monitor を束ねる
      - kill_switch.py             — kill.flag 管理
      - alert_manager.py           — アラート送信管理（LINE 等、実装による）
    - execution/
      - execution_engine.py        — ExecutionEngine 本体
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
      - (その他発注関連モジュール)
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
      - news_nlp.py                 — ニュースセンチメント取得ロジック（OpenAI）
      - regime_detector.py          — 市場レジーム判定（OpenAI + ETF MA）
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - utils/
      - logging_setup.py            — ログ設定ユーティリティ
      - process_priority.py         — プロセス優先度設定ユーティリティ
      - __init__.py
    - data/                         — 実行時に生成される（DB/flag/pid 等）
    - logs/                         — デフォルトのログ格納先（自動作成）

よくある質問（FAQ）
------------------
Q: ペーパートレードと本番 DB は分離されていますか？
A: はい。KABUSYS_ENV=paper_trading のとき、ExecutionEngine は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db とは分離されます。ただし monitoring (run_monitoring) は settings.sqlite_path を常に参照します。

Q: 監視・実行の停止方法は？
A: run_execution/run_monitoring は data/stop_requested.flag の存在を監視しています。手動停止したい場合はプロジェクトルートの data/stop_requested.flag を作成してください。また KillSwitch はデータ駆動で data/kill.flag を作成し ExecutionEngine 停止を要求します。

Q: OpenAI を使わずに実行できますか？
A: はい。AI 機能は任意で、OPENAI_API_KEY を設定しなければ ai.score_news / regime_detector.score_regime を呼ぶと例外になるため、呼び出し側でキーの有無を確認して使用を制御してください。AI 依存部はフェイルセーフ設計されています。

貢献・開発
----------
- 新機能追加やバグ修正は pull request を通して行ってください。
- 主要モジュールには docstring と単体テストを追加してください（本リポジトリにはテストスイートのテンプレートを用意することを推奨します）。

ライセンス
---------
（ここにプロジェクトのライセンス情報を明記してください）

補足
----
本 README はコードベース内の docstring・コメントを基に作成しています。実際の運用前に python -m kabusys.validate_config を実行して設定を検証し、.env を適切に構成してから起動してください。