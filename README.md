# KabuSys — 日本株自動売買システム

簡潔な紹介:
KabuSys は日本株の自動売買プラットフォーム向けに設計されたモジュール群です。データパイプライン、ファクター計算、ポートフォリオ構築、ポジション決定、実行エンジン、監視・アラート、AI を用いたニュースセンチメント / レジーム判定、並びに運用支援ツールを含みます。ライブラリとしても利用でき、個別の機能（ファクター計算やポジション計算など）は DuckDB 接続や純粋関数として呼び出せる設計です。

主な特長:
- ポートフォリオ構築（候補選定、等金額／スコア加重）
- ポジションサイズ計算（リスクベース・等配分など）、単元株丸め、集計上限処理
- セクター制限・レジームに応じた投資量調整
- 実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper_trading 用の分離）
- 監視サブシステム（System / Trade / Risk Monitor）と Kill Switch、アラート連携
- AI モジュール：OpenAI を使ったニュースセンチメント（news_nlp）とレジーム判定（regime_detector）
- Research ツール：ファクター計算・将来リターン・IC 計算など（DuckDB ベース）
- 運用支援 CLI：.env ウィザード、設定検証、Paper Trading の検証レポート生成

以下、導入・運用方法と主要ファイル構成を記載します。

目次
- プロジェクト概要
- 機能一覧（もう少し詳細）
- セットアップ手順
- 使い方（起動・停止・ツール）
- 主要環境変数
- ディレクトリ構成（抜粋）
- 運用上の注意

----------------------------
プロジェクト概要
----------------------------
KabuSys はモジュール化された自動売買システムです。内部的には以下の役割で構成されています。
- データ（DuckDB）に格納された市場データ / 財務データを用いたファクター計算
- シグナル -> 候補選定 -> 重み付け -> ポジションサイズ算出の一連ロジック（純粋関数）
- ExecutionEngine による注文送信と OrderManager / RiskManager による制御
- 監視（status / trade / risk）とアラート、Kill Switch による自動停止
- OpenAI を利用したニュースセンチメントと市場レジーム判定（オプション）

----------------------------
機能一覧（詳細）
----------------------------
- portfolio/
  - 候補選定（select_candidates）
  - 重み計算（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- research/
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC・統計サマリー
- execution/
  - ExecutionEngine、OrderManager、RiskManager（設定に応じて本番 or ペーパートレード）
  - BrokerClientFactory によりブローカークライアントを抽象化
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor、MonitoringEngine
  - monitoring_db: SQLite による監視ログ永続化（マイグレーション含む）
  - KillSwitch（条件に応じた停止フラグ書き込み）
- ai/
  - news_nlp.score_news: OpenAI を用いた銘柄ごとのニュースセンチメント
  - regime_detector.score_regime: ETF MA とマクロニュースを統合したレジーム判定
- utils/
  - ログ設定（setup_logging）、プロセス優先度設定、etc.
- tools/
  - paper_verification_report: ペーパートレード結果の集計・判定レポート

----------------------------
セットアップ手順
----------------------------
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   必要パッケージ（代表）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください）

4. 初期ディレクトリ作成
   デフォルトでは以下のパスが使われます。存在しない場合は作成してください。
   - data/           （SQLite / PID / フラグファイルの配置）
   - logs/           （ログファイル）
   例:
     mkdir -p data logs

5. .env の作成
   対話式ウィザードを用意しています：
     python -m kabusys.config_setup

   または手動で .env を作成（主な変数例）:
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     OPENAI_API_KEY=xxxxx         # AI 機能を使う場合
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

   補足:
   - 自動で .env をプロジェクトルートから読み込みます（.env, .env.local）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

6. 設定検証
   .env や config/*.yaml の不備をチェックします:
     python -m kabusys.validate_config
   厳格モード（警告も失敗扱い）:
     python -m kabusys.validate_config --strict

----------------------------
主要環境変数（代表）
----------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- OPENAI_API_KEY (AI 機能を使う場合)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- LOG_DIR (ログ出力ディレクトリ、default: logs)
- KILL_FLAG_CLEAR_ON_START (0|1) — Execution 起動時に kill.flag を自動消去するか

その他:
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔、秒。default: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env 読込を無効化）

----------------------------
使い方（起動 / 停止 / ツール）
----------------------------

起動スクリプト（パッケージモジュールとして実行可能）
- 監視プロセス起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を本番 DB として使用します（環境に関係なく）。

- 実行（ExecutionEngine）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、DB は paper_sqlite_path（default: data/paper_trading.db）に記録され本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID が書き込まれます。

停止・制御
- 停止フラグ:
  - data/stop_requested.flag を作ると run_monitoring / run_execution が検知して安全に停止します（起動ループが定期的にチェック）。
- Kill Switch:
  - リスク条件に応じて KillSwitch が data/kill.flag を書き込み、ExecutionEngine を停止するよう設計されています。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動で消去します（本番では 0 を推奨）。

ログ
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30日保持）へ出力します。
- LOG_DIR を指定するとログディレクトリを変更できます。

ツール
- .env 対話式作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプションで --db PATH に DB を指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

ライブラリとしての利用例（Python から直接呼ぶ）
- DuckDB 接続を作り、research の関数を利用:
  import duckdb
  from kabusys.research import calc_momentum
  conn = duckdb.connect('data/kabusys.duckdb')
  result = calc_momentum(conn, date(2026,4,1))

- AI スコア付け（news_nlp）:
  from kabusys.ai import score_news
  # conn: DuckDB connection
  score_news(conn, target_date=date(2026,4,1), api_key="xxxx")

注意: AI 関連は OpenAI API キー（OPENAI_API_KEY）を必要とします。

----------------------------
実装上のポイント（運用メモ）
----------------------------
- run_monitoring は「監視用 DB（SQLITE_PATH）」を環境にかかわらず使用します。つまり監視は常に本番 DB を参照する設計です。
- run_execution は KABUSYS_ENV=paper_trading の場合 DB を分離します（PAPER_TRADING_SQLITE_PATH）。
- process_priority.set_process_priority() により起動時にプロセス優先度を上げようとします（権限により失敗することがあります）。
- monitoring_db.init_monitoring_db() は既存 DB のマイグレーション（カラム追加）処理を行います。
- ai.news_nlp と ai.regime_detector は API 呼び出しで 429 / ネットワーク断 / 5xx をリトライするロジックを備えています（指数バックオフ）。
- logging_setup は既存ハンドラを一度クリアして再設定するため、複数回呼んでも重複しません。

----------------------------
ディレクトリ構成（抜粋）
----------------------------
以下は主要ファイル・ディレクトリの抜粋です。

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/                    # データ・フラグ・PID 等（手動で作成）
  - monitoring.db          # デフォルト SQLITE_PATH
  - paper_trading.db       # PAPER_TRADING_SQLITE_PATH
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                    # ログ（デフォルト）
  - execution.log
  - monitoring.log
  - ...

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
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
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - tools/
    - paper_verification_report.py

（実際のファイル構成はリポジトリを参照してください）

----------------------------
運用上の注意
----------------------------
- 本番（KABUSYS_ENV=live）では kill.flag を自動クリアしない設定（KILL_FLAG_CLEAR_ON_START=0）を推奨します。
- .env は絶対に Git にコミットしないでください（config_setup でも注意書きがあります）。
- OpenAI など外部 API を使う処理は失敗時にフォールバックする設計ですが、API キーとレート制限には注意してください。
- psutil を使った優先度設定や CPU affinity の変更は権限に依存し、失敗する場合があるためログで確認してください。
- monitoring のポーリング間隔（MONITOR_POLL_INTERVAL）を短くしすぎると負荷が高まるため注意してください。

----------------------------
サポート / 開発
----------------------------
- 追加機能の実装やバグ修正はモジュール単位で行いやすいように設計されています。
- テストや CI を追加する際は、環境変数の自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして .env に依存しない設計を推奨します。

以上が README の要約です。リポジトリに合わせて README.md をプロジェクトルートに配置して運用してください。必要であれば、README によく使うコマンド集やトラブルシューティング（ログの見方、よくあるエラーと対処）を追記できます。