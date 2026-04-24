KabuSys
=======

日本株向けの自動売買 / 研究プラットフォームのリポジトリ（パッケージ名: kabusys）。  
本READMEはコードベース（src/kabusys）をもとに、プロジェクト概要、機能、セットアップ、主要な使い方、ディレクトリ構成を日本語でまとめたものです。

要点
-----
- 本システムは実運用（live）、ペーパートレード（paper_trading）、開発（development）を切り替えて動作できます。
- 分析用に DuckDB、監視・注文ログ用に SQLite を利用します（既定のパスは data/ 配下）。
- .env による環境変数で挙動を制御します。対話式の初期設定ウィザードと設定検証ツールを提供します。
- OpenAI を用いたニュース NLP / レジーム判定などの AI 機能を含みます（APIキー必須）。

プロジェクト概要
---------------
KabuSys は日本株の自動売買アルゴリズム（戦略生成・ポートフォリオ構築・発注エンジン）と、それらを支える研究・監視・運用ユーティリティ群から成るパッケージです。  
主な設計思想は次の通りです:

- モジュール分離: 発注系（Execution）、監視系（Monitoring）、研究系（Research / AI）は明確に分離。
- DB 分離: ペーパートレード時は本番 DB と分離して data/paper_trading.db を使用。
- フェイルセーフ: API 失敗時やデータ不足時に安全側にフォールバックする実装。
- 冪等性: DB テーブル初期化や書き込みは何度実行しても問題ない（init_monitoring_db 等）。

主な機能一覧
-------------
- Execution（発注エンジン）
  - Broker クライアントの抽象化（実口座 / Mock の切替）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - PID ファイル・停止フラグ（data/stop_requested.flag）による制御

- Monitoring（システム監視）
  - SystemMonitor: CPU/Mem/Disk、データ鮮度、Execution プロセスの生存確認
  - TradeMonitor: 注文の滞留検知、約定異常検知
  - RiskMonitor: ドローダウン検知、ポジション上限監視
  - KillSwitch: 危険条件で Execution を停止する flag 書き込み
  - MonitoringEngine: 各 Monitor のポーリング束ね

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - 候補選定、等加重 / スコア加重、リスクベースの株数計算
  - セクターキャップ適用、レジーム乗数

- Research（データ処理・ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント算出（ai_scores テーブルへ保存）
  - ETF を用いた MA ベースの指標とマクロ記事の LLM センチメントの合成による市場レジーム判定

- ユーティリティ
  - .env 初期ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - 統一的なログ設定（utils.logging_setup）
  - プロセス優先度設定（utils.process_priority）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...（省略）

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無い場合は用途に応じて以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - (その他: PyYAML があれば config YAML のパース検証が可能)
   例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリに .env は含めないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL 扱いにすることを推奨:
       python -m kabusys.validate_config --strict

環境変数（主なもの）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB。デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定動作: instant|partial|never|reject)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- LOG_LEVEL (DEBUG/INFO/…)
- LOG_DIR (ログ出力ディレクトリ、デフォルト logs/)
- MONITOR_POLL_INTERVAL (monitoring のポーリング間隔秒。デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。0/1)

使い方（主要エントリポイント）
------------------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作は KABUSYS_ENV に依存:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録します。
  - 実行制御:
    - data/stop_requested.flag を作成すると実行スレッドが検知して停止します。
    - PID は data/execution.pid（デフォルト）に書き込みます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒、デフォルト 60）。
  - 監視は設定にかかわらず本番 sqlite_path を使用して監視ログを保存します（monitoring は本番 DB を参照）。
  - 停止フラグは data/stop_requested.flag を参照。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能）

- AI 機能（プログラムからの呼び出し例）
  - ニューススコアリング:
      from kabusys.ai import score_news
      # conn: duckdb connection, target_date: datetime.date
      score_news(conn, target_date, api_key="...")  # api_key 省略時は OPENAI_API_KEY を参照
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

ログ
----
- ログはデフォルトで stdout に出力され、加えて logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリ）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。
- LOG_DIR 環境変数で変更可能。

安全上の注意
--------------
- .env に API キーやパスワードを含めますが、.env は絶対にバージョン管理システムにコミットしないでください。
- KABUSYS_ENV=live の場合は設定内容（特に決済手数料・リスクパラメータ・Kill Switch 設定）を十分にレビューしてください。
- KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（Kill Switch が自動でクリアされてしまうため）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                  — ニュース NLP（OpenAI 呼び出し・ai_scores 書込）
  - regime_detector.py           — レジーム判定（MA + マクロセンチメント）
  - __init__.py

- monitoring/
  - monitoring_db.py             — SQLite 永続層（テーブル作成・読み書きユーティリティ）
  - system_monitor.py            — システム状態 / データ鮮度監視
  - trade_monitor.py             — 注文監視（存在・滞留・異常約定） ← 実装あり
  - risk_monitor.py              — ドローダウン / ポジション数監視
  - kill_switch.py               — kill.flag 管理ロジック
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - alert_manager.py             — （アラート送信を担うモジュール想定）

- execution/
  - execution_engine.py          — ExecutionEngine 本体
  - order_manager.py             — 注文管理
  - order_repository.py          — DB 上の注文レポジトリ（SQLite 等）
  - broker_factory.py            — Broker クライアント生成（本番 / Mock 切替）
  - reconciler.py                — 注文状態整合処理
  - risk_manager.py              — 実行時リスク制御

- portfolio/
  - portfolio_builder.py         — 候補選定 / 重み算出
  - position_sizing.py           — 株数決定 / aggregate cap
  - risk_adjustment.py           — セクターキャップ / レジーム乗数
  - __init__.py

- research/
  - factor_research.py           — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - __init__.py

- data/                          — データスクリプト（pipeline 等。prices_daily, raw_financials を扱う）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - __init__.py
- utils/
  - logging_setup.py             — ログ設定ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - __init__.py

データ・ログファイル（既定）
----------------------------
- data/kabusys.duckdb           — DuckDB（デフォルト: DUCKDB_PATH）
- data/monitoring.db            — 監視 SQLite（デフォルト: SQLITE_PATH）
- data/paper_trading.db         — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid            — Execution の PID（デフォルト）
- data/stop_requested.flag      — 起動済みプロセスに停止要求を伝えるフラグファイル
- data/kill.flag                — KillSwitch による強制停止フラグ（Execution 停止用）
- logs/<app_name>.log           — ログファイル（デフォルト logs/）

開発 / テストに関する補足
------------------------
- DuckDB / SQLite へはローカルファイルで接続するので、テスト時は専用の一時ファイルを渡すと安全です。
- AI 周り（OpenAI 呼び出し）は外部依存のため、ユニットテストでは API 呼び出し関数をモックする設計になっています（内部で _call_openai_api を差し替え可能）。
- config.py の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト向け）。

最後に
------
この README はコードベースの主要な使い方と構成をまとめたものです。実際の運用では .env と各種設定 YAML（config/*.yaml）を適切に整備し、validate_config による確認を行ってから実行してください。追加の実行オプションや内部 API の詳細はそれぞれのモジュールの docstring を参照してください。