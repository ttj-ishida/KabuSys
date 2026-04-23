KabuSys — 日本株自動売買システム
================================

この README は、リポジトリ内の主要モジュールを基に作成した日本語の導入ドキュメントです。
実行スクリプト、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などの主要機能を含みます。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム向けライブラリ兼ランタイム群です。主な役割は次のとおりです。

- ExecutionEngine：実際の発注・注文管理・リスク管理を行うエンジン（本番・ペーパートレード対応）。
- Monitoring：システム状態・注文状態・リスクを監視し、Kill Switch（停止フラグ）やアラートを発行。
- Portfolio：銘柄選定、重み算出、ポジションサイズ計算などのポートフォリオ構築ロジック。
- Research：DuckDB 上の価格・財務データからファクターや将来リターン、IC などを計算。
- AI：OpenAI（gpt-4o-mini など）を用いたニュースセンチメント分析と市場レジーム判定。
- Tools：ペーパートレード検証レポート生成などのユーティリティスクリプト。
- Utils：ログ設定、プロセス優先度設定などの補助ユーティリティ。

主要機能一覧
------------
- 環境設定ウィザード（config_setup）で .env を対話的に作成／更新
- validate_config による起動前チェック（必須環境変数や YAML ファイル、DB パス等）
- ExecutionEngine（run_execution）：
  - KABUSYS_ENV に応じて本番／ペーパートレードを切替
  - ブローカークライアント生成、OrderManager、RiskManager、Reconciler を組み合わせて実行
  - 停止フラグによりエンジンを安全に停止
- Monitoring（run_monitoring / MonitoringEngine）：
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - kill.flag の書き込み（KillSwitch）による ExecutionEngine 停止
  - 監視データを SQLite（monitoring.db）に永続化（init_monitoring_db）
- Portfolio モジュール：
  - 候補選定、等分配／スコア加重、セクター上限適用、レジーム乗数、株数算出（単元丸め・aggregate cap）
- Research：
  - Momentum / Volatility / Value ファクター算出
  - 将来リターン・IC・統計サマリ（DuckDB を直接利用）
- AI モジュール：
  - ニュースを LLM で評価し ai_scores に書き込む（score_news）
  - ETF ベースの MA200 とマクロニュースで市場レジームを判定し DB に保存（score_regime）
- ツール：
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定のレポートを生成

セットアップ手順
---------------
前提
- Python 3.10+ を推奨（typing の表記や機能を利用）
- DuckDB, psutil, openai（および任意で PyYAML）が必要

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージ一覧はリポジトリに requirements.txt がある場合はそれを使用。
   - 例:
     pip install duckdb psutil openai

   - 追加（YAML 検証を使う場合）:
     pip install pyyaml

3. .env を準備
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を作成する（.env は絶対にコミットしないこと）。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があるときは --strict を付けて警告も失敗扱いにできます:
     python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で削除（1=有効、デフォルト 0）

使い方（コマンド例）
------------------
- 環境ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）:
  python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合はペーパートレード DB に記録され、本番 DB と分離されます。
  - stop フラグ: data/stop_requested.flag（プロジェクトルート配下）を作成すると実行中のエンジンが停止手続きを開始します。
  - 実行中に使用される PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- 監視プロセス起動（SystemMonitor をポーリング）:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60）。
  - 監視は monitoring DB（Settings.sqlite_path）へログを記録します。
  - Monitoring は KABUSYS_ENV にかかわらず production sqlite_path を参照して監視テーブルを初期化します。

- ペーパートレード検証レポート生成:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

ライブラリ API（主要）
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.ai
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)  （ai/regime_detector.py 内で提供）

ログ設定
--------
- kabusys.utils.logging_setup.setup_logging(app_name="execution") を全スクリプトが呼び出して統一的にログを管理します。
- デフォルトログディレクトリ: logs/
- 日次ローテーション（30 日保持）でログファイルを出力します。ログ出力は標準出力（stdout）とファイルの両方に行われます。

監視・停止フラグ関連
--------------------
- Kill Switch:
  - RiskMonitor や TradeMonitor / SystemMonitor の結果に応じて KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこの kill.flag を検知して安全に停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。
- 停止要求（手動）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが停止します（プロセス内で定期チェック）。

データベース初期化
-----------------
- run_execution および run_monitoring は起動時に init_monitoring_db を呼び出し、監視用のテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等的に作成します。
- ペーパートレード用 DB は KABUSYS_ENV=paper_trading のときに paper_sqlite_path を使用して分離されます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py                # .env 対話ウィザード
- validate_config.py             # 設定検証 CLI
- run_execution.py               # ExecutionEngine 起動スクリプト
- run_monitoring.py              # SystemMonitor ポーリング起動スクリプト

パッケージ別（抜粋）
- kabusys/utils/
  - logging_setup.py
  - process_priority.py

- kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (存在)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (存在)

- kabusys/execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- kabusys/research/
  - factor_research.py
  - feature_exploration.py

- kabusys/ai/
  - news_nlp.py
  - regime_detector.py

- kabusys/tools/
  - paper_verification_report.py

開発上の注意点・ヒント
--------------------
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動読み込みします。
  - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続:
  - research/ai モジュールは DuckDB 接続を受け取って SQL を実行します。データは prices_daily / raw_financials / raw_news 等のテーブルを前提とします。
- テスト時のモック:
  - OpenAI 呼び出しは内部でラップされており、ユニットテスト時は _call_openai_api をパッチして応答を差し替えることが容易にできます。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading を使えば本番 DB と完全に分離された挙動で検証できます。PAPER_FILL_MODE を適切に設定して約定挙動をシミュレートしてください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス・貢献ポリシーはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
------
この README はコード内の docstring とモジュール構成をもとに作成しています。実運用前に python -m kabusys.validate_config による検証を行い、.env の値（特に API トークン・KABUSYS_ENV・DB パス・LOG_LEVEL）を慎重に設定してください。質問や追加情報が必要であれば教えてください。