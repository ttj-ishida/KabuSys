KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリは以下の主要コンポーネントを含みます。

- 実行エンジン起動スクリプト（ExecutionEngine 起動/停止の管理）
- 監視/アラート基盤（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（銘柄選定・配分・サイズ決定・リスク調整）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援（OpenAI を用いたニュースセンチメント、レジーム判定）
- 開発用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上のポイント
- 設定は環境変数または .env ファイルで管理（config_setup でウィザード提供）
- 実行中の監視・ログは SQLite（monitoring.db）と DuckDB（分析用）を使用
- Paper trading（ペーパートレード）は本番 DB と分離（data/paper_trading.db）
- OpenAI 呼び出しは外部 API（OPENAI_API_KEY）が必要（AI 機能のみ）
- ロギングは共通ユーティリティで設定（stdout + 日次ローテーション）

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / paper_trading の DB 分離、PID ファイル書き込み、停止フラグ対応）
  - run_monitoring.py: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔指定可能）

- 設定管理・検証
  - config_setup.py: 対話式ウィザードで .env を生成/更新
  - validate_config.py: .env / config/*.yaml 等の事前検証ツール（--strict モードあり）

- 監視・リスク管理
  - monitoring/ : SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - monitoring_db: 監視用 SQLite テーブル定義・操作ユーティリティ

- ポートフォリオ構築（pure functions）
  - portfolio/: 候補選定、等重/スコア重み、位置サイズ計算、セクターキャップ、レジーム乗数

- リサーチ
  - research/: ファクター（モメンタム、ボラティリティ、バリュー）計算、将来リターン・IC・サマリー等

- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を統合して LLM にスコア付け、ai_scores テーブルへ保存
  - ai/regime_detector.py: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- 開発ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート出力（稼働率・成功率・レイテンシ等）

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリに移動
   - 例: git clone … && cd <repo>

2. Python 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール
   - 本コードで想定される主な外部依存:
     - psutil, duckdb, openai, PyYAML
   - 例:
     - pip install psutil duckdb openai pyyaml
   - （本リポジトリに requirements.txt があればそれを使用してください:
     pip install -r requirements.txt）

4. 設定ファイル（.env）を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番稼働前は --strict を付けて警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

よく使う環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — 既定: development
  - paper_trading 時は MockBroker を利用し、paper DB に記録
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定振る舞い
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db) — 監視 DB（monitoring 用）
- PAPER_TRADING_SQLITE_PATH (既定: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|...) / LOG_DIR
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

使い方（起動・ツール）
--------------------

- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いで終了コード 1 を返す

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動時に PID ファイル（data/execution.pid 既定）を扱う
    - 停止には data/stop_requested.flag を作成する（run_execution はポーリングで検出して停止）
    - Kill Switch（監視側）が作動すると data/kill.flag を生成し ExecutionEngine に停止シグナルを与える

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
    - 監視ログは settings.sqlite_path（monitoring.db）に書き込まれる（環境にかかわらず本番 sqlite_path を使用）
    - 停止には data/stop_requested.flag を作成する（run_monitoring が検知してループを終了）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB を選択可能

- AI 機能（ニューススコアリング / レジーム判定）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - 注意:
    - api_key が未指定なら環境変数 OPENAI_API_KEY を使用
    - API 呼び出しは失敗時にフォールバック動作をする設計（例: macro_sentiment=0.0）

停止 / キルフラグの扱い
- 実行停止（柔らかい停止）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して停止します
- Kill Switch（強制停止トリガ）:
  - 監視ロジックが閾値超過を検出すると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨

ロギング / 優先度
- setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）が設定されます
- 全起動スクリプトは起動直後に set_process_priority("high") を呼び CPU 優先度を上げようとします（OS 権限不足時は警告を出してスキップ）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主なファイル・ディレクトリ（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定管理（.env 自動ロード等）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

  - execution/                   — 発注エンジンまわり（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py          — SQLite テーブル定義・CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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

注意点 / 運用上のヒント
-----------------------
- 本リポジトリは実運用を想定した設計方針を多く含みます。KABUSYS_ENV=live の場合は設定・鍵類を厳重に管理し、テスト環境で十分に検証してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- Paper trading 用 DB は本番 DB と分離されています。ペーパートレードの動作検証は常に専用 DB を使ってください。
- OpenAI を使う機能（news_nlp, regime_detector）は API 呼び出し量に依存します。コストとレート制限に留意してください。
- DuckDB / SQLite ファイルのパスは環境変数で変更できます。コンテナや複数環境で使う場合はパスを環境固有に設定してください。
- logs/ ディレクトリの作成に失敗した場合、ファイル出力はスキップされ stdout のみになります。必要に応じて LOG_DIR を設定してください。

ライセンス / バージョン
------------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 "0.1.0"）。

問い合わせ
---------
不明点や拡張要望があればリポジトリの issue に記載してください。README に含めてほしい具体的な運用例やデプロイ手順があれば追記します。