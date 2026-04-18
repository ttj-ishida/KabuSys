README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリは以下を含みます。

- 実行エンジン起動スクリプト（ExecutionEngine）と監視モジュール（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助モジュール（ニュース NLP によるセンチメントスコアリング、レジーム判定）
- 監視用 DB 層・アラート・キルスイッチ等の運用ユーティリティ
- ペーパートレード検証用レポート生成ツール

設計方針のポイント
- 本番とペーパートレードはデータベースを分離（PAPER_TRADING 用 DB を使用）
- 環境依存は .env または環境変数で管理（config_setup.py でウィザード生成可能）
- OpenAI 呼び出し等はフェイルセーフ（リトライ・フォールバック）を備える
- DuckDB を分析用 DB、SQLite を監視 / 発注ログ用に使用

主な機能
---------
- 実行エンジンの起動（run_execution.py）
  - KABUSYS_ENV に応じて本番 / ペーパートレード（MockBroker）を切り替え
  - リスク管理（RiskManager）、注文管理（OrderManager）、再調整（Reconciler）等を起動
  - 停止フラグ（data/stop_requested.flag）による安全停止サポート

- 監視プロセスの起動（run_monitoring.py）
  - システム状態（CPU/MEM/DISK）、データ鮮度、プロセス生存監視
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch 書き込み
  - ポーリング間隔は MONITOR_POLL_INTERVAL で調整可能（デフォルト 60 秒）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup: 対話式に .env を作成・更新
  - python -m kabusys.validate_config: .env と config/*.yaml の事前検証（--strict オプション有）

- ポートフォリオ構築ユーティリティ
  - 候補選定・等金額／スコア加重の重み算出（portfolio.portfolio_builder）
  - セクター集中制限・レジーム乗数（portfolio.risk_adjustment）
  - 発注株数算出（position_sizing）: 単元丸め、リスクベースやスケールダウンロジック

- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター（research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ（research.feature_exploration）

- AI 補助
  - ニュース NLP による銘柄別センチメント算出（ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 を使った日次市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しはリトライ・JSON バリデーションを実施

- 運用・監視
  - SQLite ベースの監視 DB（monitoring.monitoring_db）
  - RiskMonitor / TradeMonitor / SystemMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine の強制停止、stop_requested.flag による優雅な停止

前提 / 必要環境
---------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- SQLite（Python 標準ライブラリで利用可）

インストール例
--------------
プロジェクトルートで仮想環境を作成し、必要パッケージをインストールします（実際の requirements.txt はプロジェクトに応じて用意してください）。

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. .env 作成（対話式推奨）
   - python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参照）

2. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK 表示。--strict を付けると警告もエラー扱いになります。

3. データディレクトリ作成
   - デフォルトでは data/ 以下に DB やフラグファイルが作られます。必要に応じて .env の SQLITE_PATH / DUCKDB_PATH を変更してください。

4. ログディレクトリ
   - デフォルトは logs/。権限等で作成に失敗した場合はコンソールのみ出力されます。

運用上の注意
-------------
- KABUSYS_ENV: "development", "paper_trading", "live" のいずれか
  - paper_trading: 発注は MockBrokerClient、PAPER_TRADING_SQLITE_PATH を使用
  - live: 実際に発注されます。LINE トークン等アラート設定を必ず確認してください

- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 停止を促します（原因メッセージをファイルに保存）
  - 停止要求（優雅停止）は data/stop_requested.flag を作成すると run_* スクリプトが検知して終了します
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨

- ロギング
  - setup_logging によって stdout と logs/<app_name>.log に日次ローテートで出力します

使い方（CLI）
--------------
- 実行エンジン起動（バックグラウンド稼働等は別途プロセスマネージャで管理）
  - python -m kabusys.run_execution

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

ライブラリ API（主なもの）
------------------------
- kabusys.portfolio
  - select_candidates(buy_signals, max_positions=...)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)

- kabusys.ai
  - score_news(conn, target_date, api_key=None)  — ニュース NLP スコアを ai_scores テーブルへ書き込み
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime へ書き込み

- kabusys.monitoring
  - MonitoringDB, RiskMonitor, SystemMonitor, MonitoringEngine, KillSwitch

環境変数一覧（主要）
-------------------
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ログ
  - KABUSYS_ENV (development|paper_trading|live)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - LOG_DIR

- DB パス
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB)

- OpenAI
  - OPENAI_API_KEY

- LINE 通知（任意だが本番では推奨）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- 監視関連
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
  - KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアするか。1=有効）

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (省略表示)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (省略表示)
  - utils/
    - logging_setup.py
    - process_priority.py

（注）ここに示したファイル一覧は主要ファイルを抜粋したものです。詳しい実装は src/kabusys 以下の各モジュールを参照してください。

運用上の推奨ワークフロー
---------------------
1. 開発環境で .env を作成（config_setup.py）
2. validate_config.py で設定チェック
3. DuckDB / SQLite に必要テーブルを初期化（スクリプトまたはアプリ起動時に自動作成されます）
4. まず run_monitoring を起動して監視が動作することを確認
5. run_execution を起動して発注フローを稼働（paper_trading でまず検証）
6. 定期的に tools.paper_verification_report でペーパートレード品質をチェック

トラブルシュート
-----------------
- ログファイルが作成されない / パーミッションエラー:
  - logs/ ディレクトリの権限を確認、または LOG_DIR を書き込み可能なパスに変更してください
- OpenAI API エラー:
  - OPENAI_API_KEY を設定。API レート制限やネットワーク障害は自動リトライロジックで吸収しますが、頻繁に失敗する場合はキーやネットワーク設定を確認してください
- kill.flag / stop_requested.flag:
  - 運用者が明示的に停止する場合は data/kill.flag または data/stop_requested.flag を作成してください（kill.flag は ExecutionEngine に停止原因を通知します）

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください（本リポジトリに含まれている場合）

最後に
------
この README はコードベースの主要機能・運用手順のサマリです。詳細な設計文書（例: PortfolioConstruction.md, StrategyModel.md）や運用手順書が別途存在する想定です。実運用前には必ずステージング／ペーパートレードでの十分な検証を行ってください。