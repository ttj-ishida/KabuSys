KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買・リサーチ・監視ユーティリティ群をまとめたパッケージです。
主要コンポーネントは実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、
ファクター計算・研究ツール、AI（ニュースセンチメント・レジーム判定）などです。

この README はローカル開発者・運用担当者向けに、プロジェクト概要、機能一覧、セットアップ手順、
起動方法、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
- 自動売買エンジン（ExecutionEngine）とその監視基盤（Monitoring）を備えた日本株向けシステム。
- DuckDB を用いた時系列・ファイナンスデータの集計・ファクター計算（research）。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離してテスト可能。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価、マクロセンチメントを利用した
  市場レジーム判定（AI モジュール）。
- 監視機能は稼働率・プロセス生存・データ鮮度・注文の滞留や約定異常、ドローダウン等を検出し
  kill.flag による ExecutionEngine 停止シグナルを発行できる。

主な機能一覧
-------------
- Execution
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - Paper Trading と Live（本番）を切り替え可能。paper_trading では MockBroker を使用して専用 DB に記録。
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視（data/stop_requested.flag）。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング実行）。
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを持つ SQLite 永続層。
  - kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine の停止をトリガー。
- Portfolio（銘柄選定・配分・リスク調整）
  - 候補選定、等配分・スコア加重、ポジションサイズ計算、セクターキャップ適用など純粋関数群。
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー 等）。
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等。
- AI（OpenAI）
  - ニュース記事から銘柄別センチメント（ai_scores）を生成する工具: kabusys.ai.news_nlp
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム判定（bull/neutral/bear）
- CLI / ユーティリティ
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
  - ログ設定ユーティリティ、プロセス優先度ユーティリティなど

セットアップ手順
----------------

1. Python 環境準備
   - Python 3.10+ を推奨。仮想環境を作成して依存ライブラリをインストールしてください。
     例:
       python -m venv .venv
       source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージ（例）
   - 以下パッケージが使用されています（バージョンはプロジェクトに合わせて固定してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - pip でインストール例:
       pip install duckdb psutil openai pyyaml

3. プロジェクトルートの検出と .env の自動読み込み
   - config.py はプロジェクトルート（.git または pyproject.toml を探索）を検出して
     .env / .env.local を自動で読み込みます。
   - 自動読み込みを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. .env の作成（対話ウィザード）
   - 初期設定は対話式ウィザードで作成できます:
       python -m kabusys.config_setup
   - ウィザード実行後、.env が生成されます（.env を Git にコミットしないでください）。

5. 設定の検証
   - 作成した .env と config/*.yaml（存在する場合）を検証:
       python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
       python -m kabusys.validate_config --strict

6. data/ と logs/ ディレクトリの作成（通常は自動で行われますが事前作成しておくと安心）
   - data/monitoring.db（デフォルト）、data/paper_trading.db（paper_trading 用）、
     logs/ にログファイルが生成されます。

基本的な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 / デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB / デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、開発用）

使い方（よく使うコマンド）
------------------------

1. 実行エンジン起動（ExecutionEngine）
   - 本番/ペーパーを .env の KABUSYS_ENV で切り替え可能。
   - 起動:
       python -m kabusys.run_execution
   - 挙動:
     - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
     - paper_trading 環境では settings.paper_sqlite_path を使用して本番 DB と分離します。
     - data/stop_requested.flag が存在すると起動をスキップまたは停止します。
     - PID は data/execution.pid（デフォルト）に書き込まれます。

2. 監視ループ起動（Monitoring）
   - 起動:
       python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
     例:
       export MONITOR_POLL_INTERVAL=30
   - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（production）を使用します。
   - 停止フラグ: data/stop_requested.flag を作成するとループが終了します。

3. Paper Trading 検証レポート
   - SQLite（ペーパー用）から各種指標（稼働率・成功率・レイテンシ等）を出力します。
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
       python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。
   - ニューススコア（例: スクリプトやアプリ内から呼ぶ）:
       from kabusys.ai.news_nlp import score_news
       score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は DuckDB 接続
   - レジーム判定:
       from kabusys.ai.regime_detector import score_regime
       score_regime(duckdb_conn, target_date, api_key="...")

5. .env ウィザードと検証（運用準備）
   - .env を作成:
       python -m kabusys.config_setup
   - 検証:
       python -m kabusys.validate_config

ログとデータ
-------------
- ログ
  - デフォルト: logs/<app_name>.log（run_execution → logs/execution.log、monitoring → logs/monitoring.log）
  - 日次ローテーション（30日分保持）。ログ出力は stdout とファイル両方に行われます。
- SQLite（監視ログ）
  - data/monitoring.db（デフォルト） — system_status / trade_logs / positions / risk_logs / dashboard のテーブルを持ちます。
  - paper_trading の場合は data/paper_trading.db（既定）を使用して本番 DB と分離可能。
- DuckDB（分析）
  - data/kabusys.duckdb（デフォルト）に時系列等の分析用テーブルを格納します。

停止・Kill Switch / フラグ
-------------------------
- 停止要求（run_execution / run_monitoring）
  - data/stop_requested.flag を作成すると、run_execution のループや run_monitoring が検知して安全に停止します。
- Kill Switch（運用上の緊急停止）
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を作成すると ExecutionEngine に停止信号を送る設計です。
  - KillSwitch は RiskMonitor 等の結果に応じて kill.flag を書き込みます（冪等）。起動時に自動クリアしたい場合は
    KILL_FLAG_CLEAR_ON_START=1 を .env に設定できますが、本番では 0 を推奨します。

設計上の注意・運用注意点
-----------------------
- run_monitoring は監視 DB に対して「本番 sqlite_path」を使う設計になっています（コメント参照）。
- run_execution は KABUSYS_ENV=paper_trading なら paper_sqlite_path を使って DB を分離します。
- OpenAI 関連機能は API 呼び出しに失敗した場合にフェイルセーフ動作（スコア=0 等）で継続する設計ですが、
  API キーの漏洩に注意してください。
- .env は機密情報（API トークンやパスワード）を含むため Git 管理は厳禁です。
- duckdb/psutil/openai などの外部ライブラリを事前にインストールしてください。PyYAML は config 検証のためにあると便利です。

ディレクトリ構成
----------------
（ここでは主要なファイルを抜粋して示します）

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数・設定読み込み / Settings クラス
    - config_setup.py         — .env 対話式ウィザード
    - validate_config.py      — 起動前の設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート
    - utils/
      - logging_setup.py      — 共通ロギング設定
      - process_priority.py   — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py      — SQLite 永続層（テーブル作成・読み書き）
      - monitoring_engine.py  — Monitor を束ねるエンジン
      - system_monitor.py     — システム状態監視
      - risk_monitor.py       — ドローダウン・ポジション上限監視
      - kill_switch.py        — kill.flag 管理
      - ... (trade_monitor, alert_manager などが想定)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py           — ニュースセンチメント（OpenAI）
      - regime_detector.py    — 市場レジーム判定（OpenAI + ETF MA）
    - data/ (ランタイムで生成されることが多い)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - stop_requested.flag
      - kill.flag
    - logs/
      - execution.log
      - monitoring.log
      - ... 日次ローテーションで保持

ドキュメント・補足
-----------------
- 各モジュールの docstring に設計意図や注意点が記載されています。実運用前には validate_config による検証を必ず行ってください。
- AI モジュール（news_nlp / regime_detector）は外部 API（OpenAI）に依存します。API レート制限やエラーに対して指数バックオフ等の対策が組み込まれていますが、
  料金・呼び出し回数管理に注意してください。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores など）は research/ai モジュールと連携して利用します。データ投入パイプラインは別モジュール（data.pipeline 等）を参照してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。
- バグ報告や機能要望は Issue を立ててください。プルリクエストは歓迎します。

以上が基本的な README 相当の説明です。補足の要求や、特定の導入手順（Docker 化、systemd ユニット作成、CI 設定など）が必要であれば、その目的に合わせて追加で記述します。