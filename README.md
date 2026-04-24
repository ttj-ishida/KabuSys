# KabuSys

バージョン: 0.1.0

KabuSys は日本株を対象とした自動売買 / 研究用のユーティリティ群および実行基盤です。本リポジトリは発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP）などのモジュールを含み、開発・ペーパートレード・本番の各実行モードをサポートします。

以下はコードベースの概要、主要機能、セットアップ / 実行手順、ディレクトリ構成の説明です。

プロジェクト概要
- 日本株自動売買システムの基盤ライブラリ。
- 発注ロジック（ExecutionEngine）と監視（Monitoring）を分離して実装。
- Paper Trading（完全に分離された SQLite DB を使用）対応。
- DuckDB を使ったリサーチ/ファクター計算モジュール。
- OpenAI を用いたニュース NLP / レジーム判定モジュール（API キー必要）。
- 設定管理は .env（自動ロード機能あり）と config/*.yaml を想定。

主な機能一覧
- Execution
  - ExecutionEngine（発注の実行管理）
  - BrokerClientFactory による本番/モックブローカー切替（KABUSYS_ENV=paper_trading により MockBrokerClient を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler（発注管理・リスク制御）
- Monitoring
  - SystemMonitor: CPU/メモリ・ディスク・プロセスの監視、データ鮮度チェック
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン、ポジション上限の監視と kill switch 発動
  - MonitoringEngine: 上記を束ねたポーリングエンジン
  - monitoring_db: SQLite に永続化するテーブル群（system_status / trade_logs / positions / risk_logs / dashboard）
- Portfolio Construction
  - 候補選定、等分配・スコア加重、ポジションサイズ計算（lot 単位、リスク制約・集約上限処理）
  - セクター制限、レジーム乗数計算
- Research
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースを組合せて market_regime を算出
- ツール
  - config_setup: .env の対話式ウィザード生成
  - validate_config: .env / config/*.yaml の起動前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート出力

セットアップ手順（開発 / ローカル実行向け）
1. Python (推奨 3.10+) の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低以下をインストール）
     - pip install duckdb psutil openai
     - PyYAML は validate_config で YAML 検証を行う場合に必要: pip install PyYAML

3. .env の初期作成（推奨）
   - python -m kabusys.config_setup
   - 対話式で必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定します。
   - 注意: .env は Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL とする場合: python -m kabusys.validate_config --strict

5. ログディレクトリの作成（任意）
   - デフォルトでは logs/ に出力されます。自動で作られますが、パーミッション等問題がある場合は事前に作成してください。

環境変数の主な一覧（重要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行 / 動作関連:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - LOG_DIR: ログディレクトリ（デフォルト: logs）
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- Paper Trading 動作設定:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI:
  - OPENAI_API_KEY（news_nlp, regime_detector を使う場合）
- Monitoring 関連:
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH など（Settings から参照）

実行方法（主要スクリプト）
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に従って monitoring DB（sqlite）/ duckdb に接続
    - SystemMonitor を初期化してポーリング（MONITOR_POLL_INTERVAL 秒間隔）
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します
- 発注エンジン（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient によるシミュレーションで DB に記録します（本番 DB と分離）
    - エンジンは別スレッドで run_session を実行。stop/kill フラグで停止管理
    - 起動前に data/stop_requested.flag が存在している場合は起動せず終了
- .env の生成/編集
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能、または --db PATH で直接指定

停止・Kill Switch の仕組み
- 停止要求（ループの自然終了）
  - プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring / run_execution 側が検知して安全に終了します。
- Kill Switch（ExecutionEngine 停止用）
  - kabusys.monitoring.kill_switch が条件に応じて data/kill.flag を書き込みます（例: ドローダウン閾値超過、ポジション上限超過）。
  - ExecutionEngine は kill.flag の存在を参照して停止します。
  - Settings.kill_flag_clear_on_start が 1 の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ・監視データ
- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30 日保持）および stdout に出力
- 監視 DB（SQLite）:
  - デフォルトファイル: data/monitoring.db
  - 主要テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - init_monitoring_db() により起動時にテーブル作成・簡易マイグレーションを行います

AI（OpenAI）機能の注意
- news_nlp と regime_detector は OpenAI API を利用します。使用には OPENAI_API_KEY が必要です。
- API 呼び出しは レート制限 / ネットワーク障害 / 5xx を考慮してリトライ実装が組み込まれていますが、APIキーと利用上限に注意してください。
- テストやローカル実行時は環境変数または関数引数で API キーを渡してください。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（ファイルに抜粋なし）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック、抜粋なし）
  - execution/
    - execution_engine.py    — ExecutionEngine（抜粋なし）
    - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py
  - data/                    — 実行時に使われるデータ/フラグ/PID ファイル（例: stop_requested.flag, kill.flag, *.db）
  - logs/                    — ログ出力先（デフォルト）

注意事項 / ベストプラクティス
- 本番実行時（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config は live モードでの追加警告を行います。
- .env ファイルに秘密情報（API トークン等）を保存する場合、Git などにコミットしないでください。
- Paper Trading は本番 DB と完全分離するように設計されています（PAPER_TRADING_SQLITE_PATH をご利用ください）。
- OpenAI API 呼び出しはコストが発生します。大量バッチ運用の際は課金に注意してください。
- process_priority.set_process_priority によりプロセス優先度を上げますが、OS・権限により設定できないことがあります（警告が出ます）。

開発者向け補足
- DuckDB 接続を渡して純粋関数群（research, portfolio 等）をテストできます。多くの関数は外部副作用を持たないよう設計されています。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。
- OpenAI 呼び出し部分は単体テストでは外部 API を呼ばないようにモック可能（各モジュールの _call_openai_api をパッチすることを想定）。

よく使うコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

この README はコードベースの主要な使い方と構成をまとめたものです。追加の詳細（API 仕様、内部設計、Strategy/PortfolioConstruction ドキュメント）は別ファイル（ドキュメントディレクトリ）やソース内の docstring を参照してください。