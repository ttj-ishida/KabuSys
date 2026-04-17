# KabuSys

日本株向け自動売買システムのコンポーネント集（ライブラリ + CLI / デーモン起動スクリプト等）。

この README はリポジトリ内の主要モジュール群（execution / monitoring / portfolio / research / ai 等）を概観し、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

注意: ここに記載の挙動・環境変数はソースコード（src/kabusys 以下）から抽出しています。実運用前は必ず `python -m kabusys.validate_config` で設定検証を行ってください。

---

プロジェクト概要
- 日本株の自動売買（ExecutionEngine）とそれを支える周辺機能を提供するライブラリ群。
- 主な機能:
  - 注文管理・リスク制御・発注エンジン（paper_trading / live モード対応）
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
  - リサーチ（ファクター計算、将来リターン、IC 等）
  - AI 補助（ニュースの NLP スコアリング、レジーム判定 via OpenAI）
  - 監視（プロセス・データ鮮度・注文滞留・ドローダウン監視）と Kill Switch
  - 運用支援ツール（対話式 .env ウィザード、設定検証、Paper Trading 検証レポート生成）

機能一覧（主な機能）
- Execution
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading と live を切替）
  - BrokerClientFactory による broker クライアント生成（paper_trading では Mock を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてトレード実行
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で制御）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine による総合監視
  - MonitoringDB: SQLite ベースの監視ログ永続化（system_status / trade_logs / risk_logs / dashboard / positions）
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止
- Portfolio
  - 候補選定（select_candidates）、等重配分・スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）：リスクベース・等金額・スコアベースなど
  - セクター上限適用、レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - feature_exploration: 将来リターン、IC、統計サマリー等
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores へ書込
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースから日次レジーム判定を実施、market_regime に書込
  - OpenAI API キーが必要（OPENAI_API_KEY）
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の基本チェック
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

セットアップ手順（開発者向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境
   - 推奨 Python バージョン: 3.9+
   - 仮想環境作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML (config の YAML 検証が必要な場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 初期設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（最低限必要な環境変数を設定）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - OPENAI_API_KEY=... (AI 機能利用時)
   - 自動読み込み:
     - config.Settings はプロジェクトルートの .env / .env.local を自動読込します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合はエラーメッセージに従って修正
   - --strict を付けると警告も失敗扱いにできます

6. data ディレクトリとファイル
   - 実行前に `data/` ディレクトリが必要な場合があるため、存在しない場合は作成してください。ただし多くは起動時に自動でディレクトリが作られます。
   - 特殊フラグファイル:
     - data/stop_requested.flag: run_execution / run_monitoring が停止を検知するために使用
     - data/kill.flag: KillSwitch が作成するファイル（Execution 停止要求）
     - data/execution.pid: ExecutionEngine の PID（デフォルト）

使い方（起動例 / CLI）
- 環境の例（ペーパートレード）
  - export KABUSYS_ENV=paper_trading
  - export PAPER_FILL_MODE=instant
  - （または .env を作成）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
    - 実行中は data/execution.pid に PID を書く
    - data/stop_requested.flag を作成するとスレッドが停止します

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - オプション / 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 挙動:
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用（monitoring 用 DB を init して利用）
    - SystemMonitor / TradeMonitor / RiskMonitor を定周期で実行し、必要時に kill.flag を書く

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 使用例（厳格モード）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で SQLite ファイルを直接指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラムから呼ぶ）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=None)
    - api_key を None の場合は OPENAI_API_KEY を参照
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - 両関数は DuckDB 接続（DuckDBPyConnection）と target_date（日付）を受け取ります

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI 利用時に必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading の専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject、デフォルト "instant"）
- MONITOR_POLL_INTERVAL: 監視のポーリング秒数（run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

停止・Kill の取り扱い
- 管理者が実行環境を停止したい場合:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検出して安全に停止します
- システム側の安全停止（Kill Switch）:
  - RiskMonitor 等の判定で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine の起動時/監視で停止に使われます
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定読み込みロジック
  - config_setup.py         — .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルあり)
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - execution/               — 注文実行関連（OrderManager, Engine, BrokerFactory など）※詳細は該当ファイル参照
  - monitoring/              — 上記監視関連
  - utils/
    - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py

補足・運用上の注意
- DB と .env は機密情報を含むため Git 管理しないこと（config_setup でも注意書きがあります）。
- AI 機能（news_nlp / regime_detector）は OpenAI API コストやレート制限の影響を受けます。OPENAI_API_KEY の管理および利用上限に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL に従って無限ループで動作します。停止は stop_flag ファイルか Ctrl+C（KeyboardInterrupt）。
- Monitoring は本番 sqlite_path を常に使用します（監視ログは本番 DB に保存される想定）。
- Paper Trading は本番 DB と分離された専用 SQLite を使用する（PAPER_TRADING_SQLITE_PATH）。
- プロセス優先度設定（set_process_priority）を行いますが、権限不足やプラットフォームの違いでスキップされる場合があります。

開発・貢献
- 新しい機能追加やバグ修正は該当モジュールのユニットテストと合わせて PR を出してください
- 仕様書（PortfolioConstruction.md / StrategyModel.md 等）に基づく実装が多くあるため、設計文書の参照を推奨します（リポジトリに含まれる想定）

この README はコードベースから抽出した情報をまとめたものです。詳細は各モジュールの docstring を参照してください（src/kabusys 以下の各 .py に詳細な説明と注意が書かれています）。