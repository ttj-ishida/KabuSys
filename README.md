# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼起動スクリプト群）。

このリポジトリは戦略・ポートフォリオ構築、発注エンジン、監視、研究用ユーティリティ、AI を用いたニュース解析などを含むコンポーネントで構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド / スクリプト）
- 環境変数（主要）
- ディレクトリ構成（概要）

---

プロジェクト概要
- 「KabuSys」は日本株自動売買に関する機能群をまとめたパッケージです。
- 発注エンジン（ExecutionEngine）、監視モジュール（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築ユーティリティ、研究用ファクター計算、AI を使ったニュースセンチメント評価などを含む。
- SQLite / DuckDB をデータ永続化・分析に使用。
- OpenAI（gpt-4o-mini など）を使ったニュース解析やレジーム判定を実装可能（APIキー必要）。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV により paper_trading（モックブローカー）／live（実ブローカー）を切り替え
  - Paper Trading 時は専用 SQLite（data/paper_trading.db）で本番 DB と分離
  - プロセス優先度設定 / PID ファイル管理 / 停止フラグの監視
- MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - システム資源監視（CPU/メモリ/ディスク）
  - データ鮮度チェック、プロセス死活監視、取引ログ監視、ドローダウン・ポジション上限監視
  - kill.flag による ExecutionEngine 停止（Kill Switch）
- Monitoring DB 層（monitoring_db）
  - system_status/trade_logs/positions/risk_logs/dashboard テーブルの作成・読み書き
- ポートフォリオ構築
  - 候補選定、スコア重み付け、等配分、ポジションサイズ計算（単元丸め含む）、セクター上限適用、レジーム乗数
- 研究・因子計算（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等
- AI モジュール（ai）
  - news_nlp: raw_news を LLM で解析して銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジームを判定・永続化
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の妥当性検証 CLI
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順（概要）
1. 推奨 Python バージョン
   - Python 3.10 以上（typing の | Union 構文などを使用しているため）
2. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合はそれを利用してください）
4. 環境変数設定（.env を作成）
   - 対話式に .env を作る: python -m kabusys.config_setup
   - あるいは .env を自分で作成（.env.example を参考に）
   - 自動ロードはデフォルトで有効。無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合は --strict を付ける
6. 必要なディレクトリ
   - デフォルトでは data/ logs/ が使われます。起動スクリプトが自動作成しますが、権限等に注意してください。

使い方（主要コマンド）
- ExecutionEngine を起動（本番 / ペーパートレードを KABUSYS_ENV で切り替え）
  - python -m kabusys.run_execution
  - 動作:
    - Settings を読み込み、SQLite / DuckDB 接続を確立
    - paper_trading の場合は専用 DB を使用（設定: PAPER_TRADING_SQLITE_PATH）
    - Engine がバックグラウンドスレッドで run_session を実行。data/stop_requested.flag を作ると停止
- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を参照
  - 停止は data/stop_requested.flag の作成で検知
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file PATH
- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH (環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能)
- ライブラリ API（コードから呼ぶ場合）
  - ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research.calc_momentum(conn, date)
  - portfolio.calc_position_sizes(...)
  - など、モジュールは duckdb.DuckDBPyConnection や sqlite3.Connection を引数に受ける純粋関数多数

重要なファイル・フラグ
- data/stop_requested.flag
  - run_execution / run_monitoring が停止を検知するためのフラグファイル
- data/kill.flag
  - KillSwitch が条件を満たしたときに作成され、ExecutionEngine 停止のトリガーとして機能
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリア（本番では 0 推奨）
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb (Settings.duckdb_path)
  - Monitoring SQLite: data/monitoring.db (Settings.sqlite_path)
  - Paper Trading SQLite: data/paper_trading.db (Settings.paper_sqlite_path)

主要な環境変数（サマリ）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB 関連
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- OpenAI
  - OPENAI_API_KEY（ai モジュール使用時に必要）
- ログ
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR（ファイルログ保存先、デフォルト: logs/）
- その他
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
  - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: 0/1）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定すると .env の自動ロードを無効化）

ロギング
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）を設定
  - デフォルトで 30 日分のバックアップを保持

注意事項 / 運用上のポイント
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知や kill switch の設定を確認してください。
- Paper Trading は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API を使う処理は API 利用料が発生します。API キーの管理に注意してください。
- 各モジュールは「ルックアヘッドバイアス」に配慮して実装されています（target_date 未満のデータのみ使用等）。
- データベースやログディレクトリの作成に失敗した場合、ログのファイル出力が無効化されコンソールのみの出力になります。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA200）
  - research/
    - factor_research.py      — Momentum, Volatility, Value 等
    - feature_exploration.py  — forward returns, IC, summary
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装により存在)
  - execution/                 — Execution 関連（Engine, BrokerFactory, OrderManager 等）
  - data/                      — データ処理 / pipeline etc.
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

（注）上記はリポジトリ内の代表的ファイルのみ抜粋しています。詳細はソースコードをご参照ください。

貢献 / 拡張
- config/*.yaml による細かな設定や、ブローカークライアントの追加実装（BrokerClientFactory）で外部実ブローカー連携が可能です。
- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news 等）を充実させることで研究・AI モジュールの精度向上が期待できます。

---

問題や設定で不明点があれば、どのスクリプトをどう動かしたいか（例: paper_trading でのレポート生成、OpenAI を使ったレジーム判定の実行など）を教えてください。具体的な実行コマンドや .env のサンプル設定例を提示します。