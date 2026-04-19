README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。
このリポジトリには以下の主要な機能群が含まれます:

- 発注実行エンジン（ExecutionEngine）起動スクリプト
- 監視（Monitoring）コンポーネント（システム状態、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み付け、株数算出、セクター制限）
- リサーチ／ファクター計算（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- AI ベースのニュース NLU（OpenAI を用いたニュースセンチメント、レジーム判定）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- ペーパートレード検証レポート生成ツール

主な設計方針
- 本番／ペーパートレードの DB を分離（paper_trading 環境時のみ専用 SQLite を使用）
- ルックアヘッドバイアスを避ける設計（date.today / datetime.now の不用意な使用を抑制）
- フェイルセーフ：外部 API エラー時はスキップして処理継続（ログ出力）
- 関数は可能な限り純粋関数化しテストしやすく実装

機能一覧
--------
- 環境設定ウィザード: .env を対話的に作成・更新 (kabusys.config_setup)
- 設定検証 CLI: .env と config/*.yaml のチェック (kabusys.validate_config)
- Execution 起動スクリプト: 発注エンジンを起動（KABUSYS_ENV によりペーパートレード用クライアント切替）
- Monitoring 起動スクリプト: SystemMonitor のポーリングループ
- Monitoring 以下:
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - trade_monitor: 注文の滞留・約定異常の検出（trade_logs 参照）
  - risk_monitor: ドローダウン／ポジション上限の監視（dashboard / positions 参照）
  - kill_switch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止信号を送る
  - monitoring_db: SQLite を使った永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring_engine: 各 Monitor を束ねて定期実行・アラート発火
- Portfolio:
  - 銘柄候補選定、等金額／スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research:
  - ファクター計算（momentum, volatility, value）
  - 特徴量解析（forward returns, IC, 統計サマリ）
- AI:
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector: マクロニュース + ETF MA200 乖離で市場レジーム判定
- ツール:
  - paper_verification_report: ペーパートレード DB を解析し Pass/Fail レポートを出力

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - (本 README の参照元はパッケージが src/kabusys 配下にあることを想定)

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なパッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML (config YAML の検証を行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合はそれを利用してください）

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - PAPER_FILL_MODE（paper_trading 時の約定動作: instant|partial|never|reject）  
   - 自動 .env ロード:
     - パッケージ起動時にプロジェクトルート（.git か pyproject.toml）を探し .env/.env.local を自動で読み込みます。
     - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

使い方（主要コマンド）
--------------------
- ExecutionEngine を起動（本番 or ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - プロセス優先度を "high" に設定（psutil を利用、可能な場合のみ）

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境にかかわらず本番 DB に書き込む点に注意）
  - 実行中に data/stop_requested.flag を作るとループを抜けて終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼ぶ）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または引数で指定）
  - ニューススコアを書き込む:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb connection を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトのログディレクトリ: logs/
- 各アプリケーションごとにログファイルが生成されます（例: logs/execution.log, logs/monitoring.log）
- ログローテーション: 日次、30日分保持

停止制御 / フラグファイル
------------------------
- stop_requested.flag:
  - run_execution / run_monitoring は起動時やループ内で data/stop_requested.flag を確認します。ファイルが存在すると動作を停止または起動を行いません。
- kill.flag:
  - KillSwitch（監視側）によって生成され、ExecutionEngine に対する安全停止シグナルとして機能します。
  - Settings.kill_flag_clear_on_start が 1 の場合、Execution 起動時に自動クリアされる設定になっていることに注意（本番では 0 を推奨）。

設定の主要項目（概要）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: 分析用 DuckDB ファイル（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（既定: data/paper_trading.db）
- LOG_LEVEL: ログレベル
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring ポーリング間隔（秒、デフォルト 60）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋。実際は src/kabusys 配下にモジュールが配置されています。）

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数 / .env 自動読み込み / Settings クラス
    - config_setup.py             # .env ウィザード CLI
    - validate_config.py          # 設定検証 CLI
    - run_execution.py            # ExecutionEngine 起動スクリプト
    - run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py          # ログ設定ユーティリティ
      - process_priority.py       # プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py          # monitoring DB （SQLite）初期化・簡易ラッパ
      - system_monitor.py
      - trade_monitor.py          # （参照されるが省略）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py          # （参照されるが省略）
    - execution/
      - execution_engine.py       # ExecutionEngine 本体（参照）
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/                  # 上で説明済み
    - tools/
      - paper_verification_report.py

補足 / 注意点
-------------
- DB ファイル・ログディレクトリ等はデフォルトで data/ や logs/ に作成されます。必要に応じて .env でパスを変更してください。
- 本番環境（KABUSYS_ENV=live）では Kill Switch や LINE 通知設定等を特に注意して設定してください。validate_config は本番向けのガードチェックをいくつか行います。
- OpenAI を使う機能は API コストとレイテンシを考慮して運用してください。API キーの管理は厳重に行ってください。
- psutil の優先度設定や CPU affinity の操作は OS 権限に依存します。権限不足の場合は警告を出してスキップされます。

ライセンス / バージョン
------------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリに含めてください（本リポジトリにはライセンスファイルが含まれていない可能性があります）。

問題報告 / 貢献
----------------
不具合や改善提案は Issue を立ててください。PR は歓迎します。テスト・型チェック・ドキュメントの追加は特に助かります。

以上。セットアップや実行で不明点があれば使用環境（OS、Python バージョン、環境変数、エラーログ）を添えて質問してください。