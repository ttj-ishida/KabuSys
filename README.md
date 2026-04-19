KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株の自動売買システム（KabuSys）のモジュール群を含みます。
本 README はコードベース（src/kabusys/*）の概要、機能、セットアップ手順、起動方法、
主要なディレクトリ構成を日本語でまとめたものです。

要点
----
- 環境依存設定は .env ファイルまたは環境変数で行います（config_setup で対話的作成可能）。
- 実行系（ExecutionEngine）と監視系（Monitoring）が分離され、監視は本番の監視 DB を参照します。
- Paper Trading モードでは発注はモック実装を使用し、専用の SQLite DB に記録します。
- AI（OpenAI）を利用する機能（ニュース NLP / レジーム判定）が含まれます（API キー必須）。

主な機能一覧
-------------
- execution:
  - 実際の発注エンジン（ExecutionEngine）。リスク管理、オーダー管理、照合（reconciler）等を含む。
  - Paper Trading モードでのモック発注（本番 DB と分離）。
- monitoring:
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセスの監視、データ鮮度チェック。
  - TradeMonitor / RiskMonitor: 注文レコード・リスク（ドローダウン・ポジション数）監視。
  - KillSwitch: 条件に応じて data/kill.flag を作成して Execution を停止させる仕組み。
  - Monitoring DB: SQLite に監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を永続化。
- portfolio:
  - 銘柄選定、等ウェイト・スコア重み、ポジションサイズ計算、セクター上限・レジーム乗数の計算。
- research:
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、特徴量探索、IC・統計サマリ等（DuckDB を利用）。
- ai:
  - news_nlp: OpenAI を用いたニュースのセンチメントスコアリング（ai_scores への書き込み）。
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定（market_regime へ書込）。
- tools:
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成。
- utils:
  - logging_setup: 統一的なログ設定（stdout と日次ローテーションファイル）。
  - process_priority: プロセス優先度・CPU affinity 設定。

セットアップ手順
----------------
1. Python 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール:
   - 必須例:
     - duckdb
     - psutil
     - openai
     - (optional) PyYAML（config ファイル検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトが配布パッケージ化されている場合は pip install -e . 等を利用してください。）

3. .env を作成:
   - 対話的ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照してください（リポジトリにある場合）。

4. .env の検証:
   - python -m kabusys.validate_config
   - オプション --strict を付けると警告も失敗扱いになります。

5. データディレクトリ:
   - デフォルトの DB / PID / flag ファイルは data/ に作成されます（必要に応じてパーミッションを確認してください）。
   - ログは logs/ に日次ローテーションで出力されます（LOG_DIR 環境変数で変更可能）。

重要な環境変数（抜粋）
---------------------
（Settings クラスにより取得。デフォルト値は括弧内に示します）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

任意 / デフォルト:
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live) （default: development）
- LOG_LEVEL             : ログレベル (DEBUG/INFO/...)
- DUCKDB_PATH           : DuckDB ファイルパス (data/kabusys.duckdb)
- SQLITE_PATH           : 監視 SQLite パス (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite (data/paper_trading.db)
- PAPER_FILL_MODE       : paper_trading 時の模擬約定モード (instant|partial|never|reject) (default: instant)
- OPENAI_API_KEY        : OpenAI API キー（AI 機能使用時必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか (0 or 1, default 0)
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒。run_monitoring で上書き可、デフォルト 60）

使い方（主要スクリプト／コマンド）
---------------------------------

- 環境設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告を FAIL 扱い）

- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 動作: Settings に応じて本番 DB または paper_trading 用 DB に接続。別スレッドで engine.run_session を実行。
  - 注意: data/stop_requested.flag が存在すると起動しない／停止します（外部停止フラグ）。

- Monitoring 起動（ポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可（デフォルト 60 秒）。
  - Monitoring は常に本番 sqlite_path を使用して監視ログを記録します（KABUSYS_ENV にかかわらず）。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ライブラリ的利用）:
  - ニューススコアリング（DuckDB 接続を渡す）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # 書き込み件数を返す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ログと監視
-----------
- ログ設定:
  - kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します。
  - 出力: stdout（常に） + 日次ローテーションファイル logs/<app_name>.log（LOG_DIR で変更可）。
- 監視/停止フラグ:
  - data/kill.flag : KillSwitch により作成されると ExecutionEngine の停止トリガーになります。
  - data/stop_requested.flag : run_monitoring や run_execution の外部停止判定に使用されます。
  - PID ファイル: data/execution.pid（設定で変更可）。

データベースとマイグレーション
----------------------------
- init_monitoring_db(conn) により monitoring 用 SQLite のテーブルは冪等で作成されます（起動時に自動作成）。
- DuckDB は分析用途（prices_daily、raw_financials、raw_news 等のテーブル）として利用します。
- 一部のマイグレーション（カラム追加）は起動時に自動的に行われます（例: dashboard.peak_value, trade_logs.latency_ms）。

ディレクトリ構成（主要部分）
---------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, ...）
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 制御
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — （アラート送信機能、実装ファイルが存在する場合）
- portfolio/
  - portfolio_builder.py   — 銘柄選定、重み計算
  - position_sizing.py     — 株数計算
  - risk_adjustment.py     — セクター制限、レジーム乗数
- research/
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン、IC、rank、summary
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity

備考・運用上の注意
-----------------
- 本番運用（KABUSYS_ENV=live）では .env の設定ミスが致命的になり得ます。validate_config で入念にチェックしてください。
- Kill Switch（kill.flag）や KILL_FLAG_CLEAR_ON_START の設定は本番では特に注意が必要です（自動クリアは推奨しません）。
- OpenAI など外部 API 使用箇所は API キーや課金に注意してください。API 呼び出しはリトライ・フォールバック処理が実装されていますが、失敗時はスコア算出をスキップまたは中立値でフォールバックします。
- DuckDB / SQLite のパスは環境変数で容易に切り替えられるため、テスト環境と本番環境で DB を分離してください（paper_trading では paper_sqlite_path を使用）。

サンプルコマンドまとめ
---------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア生成（例: Python REPL）:
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, date(2026,4,10), api_key="sk-...")

最後に
-----
この README はコード内の docstring / コメントを基に要点を整理したものです。各モジュールの詳細な使用法・パラメータは該当ソースファイルの docstring を参照してください。運用・デプロイ時にはログ・バックアップ・監視設定（LINE 等）を適切に構成してください。質問や追加のドキュメント化が必要であればお知らせください。