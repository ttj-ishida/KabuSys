README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。本リポジトリには次の主要機能を備えたモジュール群が含まれます。

- 戦略（ファクター計算、特徴量解析）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- 実行エンジン（ブローカークライアント抽象化、注文管理、リスク管理）
- 監視（システム・注文・リスクのポーリング、Kill Switch）
- AI 補助（ニュースのセンチメント評価・レジーム判定）
- 開発ツール（環境ウィザード、設定検証、ペーパートレード検証レポート）

設計方針のポイント
- 設定は .env か環境変数で管理。自動的にプロジェクトルートの .env / .env.local を読み込みます（無効化可）。
- 実行スクリプトはプロセス優先度の設定・統一ログ設定・SQLite / DuckDB への接続を行います。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite ファイル（data/paper_trading.db）を使用します。
- AI 部分は OpenAI（gpt-4o-mini）を使用可能。API キーは環境変数 OPENAI_API_KEY で指定します。

主な機能一覧
--------------
- 環境ウィザード: python -m kabusys.config_setup により .env を対話生成
- 設定検証: python -m kabusys.validate_config により環境変数・config/*.yaml の検証
- 実行エンジン起動: python -m kabusys.run_execution — リスク管理、注文発行、リコンシリエーション
- 監視ループ起動: python -m kabusys.run_monitoring — SystemMonitor の定期ポーリング（MONITOR_POLL_INTERVAL で間隔指定可）
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report — ペーパートレード DB から指標を算出
- AI: kabusys.ai.score_news / kabusys.ai.score_regime — ニュースセンチメント、レジーム判定（OpenAI 必須）
- ポートフォリオ構築: 候補選定、等重／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数

セットアップ手順
----------------
1. Python バージョン
   - Python 3.10+ を推奨（PEP 604 の型記法などを使用）。

2. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

3. 依存ライブラリ（最低限）
   - pip install duckdb psutil openai PyYAML
   - 必要に応じて仮想環境（venv / pipenv / poetry 等）を利用してください。

4. 環境変数設定
   - 対話式ウィザード:
     - python -m kabusys.config_setup
       → .env を生成/更新します（.env は絶対にコミットしないでください）。
   - もしくは直接環境変数を設定してください。
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データベース
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

使い方（主要コマンド）
--------------------
- 環境ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
    - 設定の必須項目やファイルの存在、YAML のパースなどを確認します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV によって挙動が変わります:
      - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
      - live / development: settings.sqlite_path（デフォルト data/monitoring.db）へ接続
    - 実行中に data/stop_requested.flag が作成されると安全に停止します。
    - 実行時は data/execution.pid（デフォルト）に PID を書きます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
    - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
    - 監視は環境にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に残ります）。
    - 停止は data/stop_requested.flag の作成で行います。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH または --db で DB を指定できます。

- AI（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行スクリプトは用意していませんが、DuckDB 接続を渡すことで利用できます。

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、default: data/paper_trading.db）
- LOG_LEVEL（default: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知、任意）
- OPENAI_API_KEY（AI 機能を利用する場合必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか（0/1））

停止・Kill Switch の運用
-----------------------
- KillSwitch（kabusys.monitoring.kill_switch）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を送ります。
- run_execution / run_monitoring は data/stop_requested.flag の存在を検知すると終了します。
- 実運用では KILL_FLAG_CLEAR_ON_START を誤って 1 にしないよう注意してください（本番では 0 推奨）。

ログ
----
- 共通ロギングユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
  - LOG_DIR 環境変数または引数でログ先を指定できます。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys をプロジェクトルートに展開した想定での主要ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数・設定の読み込み
  - config_setup.py                : 対話式 .env ウィザード
  - validate_config.py             : 設定検証 CLI
  - run_execution.py               : ExecutionEngine 起動スクリプト
  - run_monitoring.py              : SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  : ペーパートレード検証レポート
  - ai/
    - news_nlp.py                   : ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py            : 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py              : SQLite 永続化層（テーブル初期化・読み書き）
    - system_monitor.py             : システム状態・データ鮮度監視
    - trade_monitor.py              : （注文監視ロジック）
    - risk_monitor.py               : ドローダウン・ポジション上限監視
    - kill_switch.py                : Kill Switch （kill.flag 書き込み）
    - monitoring_engine.py          : 各 Monitor を束ねる実行エンジン
    - alert_manager.py              : （LINE 等への通知ラッパー）
  - execution/
    - execution_engine.py           : 実行エンジン本体
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
  - data/                            : （スクリプトが参照するデフォルトの data ファイル群）
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティモジュール

補足 / 運用メモ
----------------
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に基づき行います。CWD に依存しないためパッケージ配布後も安定して動作します。
- PyYAML が未インストールの場合、validate_config は YAML の検証をスキップします（警告）。
- DuckDB の操作は research / ai モジュールで利用する想定です。データの投入・更新は別途 ETL スクリプトや pipeline を用意してください（kabusys.data.pipeline 等）。
- OpenAI 呼び出しは外部 API のためレート制限やエラーに対するリトライ実装がありますが、API キーの管理やコストには注意してください。
- 重要なファイル（.env, data/*）は Git 管理から除外してください。

ライセンス・貢献
----------------
- 本 README にはライセンス記載をしていません。リポジトリの LICENSE を参照してください。
- 貢献する場合は issue / PR にて議論してください。

以上が基本的な README 内容です。必要であれば、実際の環境変数例（.env.example）、起動手順のサンプル systemd/unit ファイル、開発用 Dockerfile / docker-compose のテンプレートなどを追加できます。どの追加ドキュメントが必要か教えてください。