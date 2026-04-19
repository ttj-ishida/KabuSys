KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・研究基盤を想定した Python パッケージ群です。  
主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）と監視（Monitoring）を分離して実行可能
- ペーパートレード用の完全分離 DB をサポート（KABUSYS_ENV=paper_trading）
- DuckDB を使った研究（因子計算・特徴量解析）用モジュール群
- OpenAI を利用したニュース NLP / 市場レジーム判定のユーティリティ
- 監視ログは SQLite（monitoring.db）に永続化

主な機能一覧
-------------
- 実行系
  - run_execution.py: ExecutionEngine を起動／停止制御（PID・停止フラグ対応）
  - Broker クライアントの切替（paper_trading 時は MockBroker を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の実装（起動時に組み立て）

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine：システム状態・注文滞留・ドローダウン等の監視
  - KillSwitch（data/kill.flag）で ExecutionEngine を強制停止可能
  - 監視ログ: SQLite（data/monitoring.db）に system_status/trade_logs/positions/risk_logs/dashboard

- 研究・分析
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 参照）
  - research.feature_exploration: 将来リターン計算・IC（Information Coefficient）等
  - portfolio: 候補選定・重み計算・ポジションサイズ算出・セクター制限・レジーム乗数

- AI（OpenAI）
  - ai.news_nlp.score_news: ニュース記事を LLM でセンチメント化し ai_scores テーブルに書き込み
  - ai.regime_detector.score_regime: ETF とマクロニュースを合成して日次レジーム判定を行い DB に保存

- ユーティリティ
  - config_setup.py: .env の対話式作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml 等の起動前チェック CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト
  - utils.logging_setup: 統一的なログ設定（console + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
1. Python（3.10+ を推奨）を用意します。

2. 必要パッケージをインストールします（環境に応じて仮想環境を推奨）。

   例:
   pip install duckdb psutil openai PyYAML

   注:
   - PyYAML は config/*.yaml の内容検証に必要（必須ではありません）
   - openai は ai 機能を使う場合に必要

3. .env を用意します（プロジェクトルートに配置）。
   - 対話式で作る: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成

4. 自動環境読み込み
   - ソース実行時、プロジェクトルートに .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須・主要な環境変数（抜粋）
----------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / パス関係
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - DUCKDB_PATH: data/kabusys.duckdb（分析用データ）
  - SQLITE_PATH: data/monitoring.db（監視ログ）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（KABUSYS_ENV=paper_trading 時の専用 DB）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

- AI
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.* を使うとき）

- 監視ループ等
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）

使用方法（CLI）
----------------
- 環境ウィザード（.env 生成／更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）。
  - run_monitoring は監視用 DB（settings.sqlite_path）を常に使用します（環境に依らず本番 DB パスを参照する仕様に注意）。

- 実行エンジン（ExecutionEngine）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究機能（ライブラリ関数として利用）
  - ニューススコア付与（例: Python REPL）
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    # OPENAI_API_KEY を環境変数にセットするか、api_key 引数で渡す
    score_news(conn, target_date=date(2026,4,10), api_key=os.environ.get('OPENAI_API_KEY'))

  - 市場レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key=...)

注意事項・運用メモ
-----------------
- Kill/Stop フラグ
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine を停止させるために使用
  - data/stop_requested.flag: run_execution / run_monitoring のループを安全に停止させるためのローカルフラグ
  - PID ファイル: data/execution.pid に ExecutionEngine の PID を書き込む

- DB の分離
  - 監視（monitoring）は settings.sqlite_path（デフォルト data/monitoring.db）を使用
  - Paper trading は環境により paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する

- ログ
  - logs/<app_name>.log に日次ローテーションで出力（utils.logging_setup を各起動スクリプトで呼び出し）
  - コンソール出力は stdout に向けられているため、cron 等で集約しやすい

- .env 読み込み挙動
  - OS 環境変数 > .env.local > .env の順で解決される
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

- 依存パッケージ
  - duckdb, psutil, openai（ai 機能用）, PyYAML（config 検証時に推奨）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI 経由のセンチメント付与）
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py         — （アラート送信ロジック）
- execution/
  - execution_engine.py      — 実行エンジン本体
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

付録（よくある運用コマンド）
----------------------------
- 起動前検証:
  python -m kabusys.validate_config

- .env 生成:
  python -m kabusys.config_setup

- 監視開始（デーモン化は外部ツールで）:
  python -m kabusys.run_monitoring &

- 実行エンジン開始:
  python -m kabusys.run_execution &

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

最後に
-------
この README はコードベースの主要な挙動・起動手順をまとめたものです。  
詳細な設計（PortfolioConstruction.md、StrategyModel.md 等）や追加の CLI / スクリプトはプロジェクト内のドキュメントを参照してください。必要なら README に追記してほしい点（例: デプロイ手順、systemd サービス定義、CI 設定等）を教えてください。