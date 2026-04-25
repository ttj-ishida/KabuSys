README.md

プロジェクト概要
- KabuSys は日本株（kabuステーション）向けの自動売買・研究基盤です。
- 株価・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
  Paper Trading 用検証ツール、AI を使ったニュース解析・レジーム判定などのコンポーネントを含みます。
- 設計方針の主なポイント:
  - 本番データとペーパートレードを分離（Paper Trading は専用 SQLite を使用）
  - DuckDB を分析・研究用データストアに利用
  - LLM（OpenAI）をニュース解析・レジーム判定に利用（フェイルセーフ設計）
  - ロギング・プロセス優先度設定・Kill Switch 等による運用上の配慮

主な機能一覧
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により実発注 / ペーパートレード切替）
  - run_monitoring: SystemMonitor のポーリングループ起動（監視ログは monitoring DB に永続化）
- 設定管理 / 検証
  - config_setup: 対話式に .env を生成・更新
  - validate_config: .env や config/*.yaml の事前検証（--strict オプションあり）
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch により条件に応じて data/kill.flag を作成して ExecutionEngine を安全停止
  - monitoring_db: 監視用 SQLite のスキーマと読み書き API
- 発注関連（execution）
  - BrokerClientFactory による実ブローカ or MockBroker の切替（paper_trading モード）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine 等
- ポートフォリオ構築（portfolio）
  - 候補選定、重み算出、ポジションサイズ決定、セクター制約、レジーム乗数など
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（ai）
  - news_nlp: ニュース全文を LLM で解析して ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定（market_regime へ保存）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

セットアップ手順（開発環境）
1. 依存パッケージのインストール（最低限の例）
   - duckdb, psutil, openai, PyYAML（設定検証で必要）等
   例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がプロジェクトにあればそれを使用してください。

2. プロジェクトルートに移動（.git または pyproject.toml を含むディレクトリ）
   - config_setup や自動 .env ロードはプロジェクトルートを基準に動作します。

3. .env の初期作成（対話式ウィザード）
   - コマンド:
       python -m kabusys.config_setup
   - 出力例: .env を project_root/.env に保存します。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_PATH など

4. 設定検証
   - コマンド:
       python -m kabusys.validate_config
   - 厳格モード（警告もエラー扱い）:
       python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトでは data/ 下に DB・フラグファイル・PID ファイルが作成されます（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）。
   - logs/ にアプリログ（例: logs/execution.log, logs/monitoring.log）が日次ローテーションで保存されます。

使い方（起動例・コマンド）
- ExecutionEngine を起動
  - 本番（KABUSYS_ENV=live）や開発（development）は .env に応じて動作
  - ペーパートレード（MockBroker）を使う:
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading のときは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止要求は data/stop_requested.flag / data/kill.flag により行います（Kill Switch は監視側で作成）。

- Monitoring を起動
  - コマンド:
      MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
    - 停止には data/stop_requested.flag を作成するか KeyboardInterrupt。

- Paper Trading 検証レポート
  - コマンド:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
      python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し PASS/FAIL 判定を出します。

- AI 関連（プログラムからの呼び出し例）
  - news_nlp の実行例（Python REPL 等）:
      from kabusys.ai.news_nlp import score_news
      import duckdb, datetime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026, 4, 10), api_key="sk-xxxx")
  - regime_detector の実行例:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, datetime.date(2026, 4, 10), api_key="sk-xxxx")
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定可能。未指定時は例外になります。

運用上の注意
- Kill Switch / stop フラグ
  - KillSwitch は RiskMonitor の判定等で data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります（フラグの存在は is_flagged() で確認可能）。
  - run_execution、run_monitoring は data/stop_requested.flag を監視してループを終了します。外部から安全に停止させたい場合はこのファイルを作成してください。
  - Settings.kill_flag_clear_on_start=1 を本番で使うと危険（自動クリアされるため）。本番では 0 推奨。

- ロギング
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション）が有効になります。
  - LOG_DIR, LOG_LEVEL を環境変数で指定できます。

- DB の分離
  - ペーパートレード時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 monitoring DB を汚しません。
  - Monitoring は常に Settings.sqlite_path（monitoring.db）を使いログを保存します（設計上の明確化）。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / .env 自動読み込み、Settings クラス
    - config_setup.py        — 対話式 .env ウィザード
    - validate_config.py     — 起動前設定検証 CLI
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py     — ログ設定ユーティリティ
      - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py     — 監視 DB スキーマ + 操作 API
      - system_monitor.py    — システム・データ鮮度監視
      - risk_monitor.py      — ドローダウン / ポジション上限監視
      - trade_monitor.py     — 発注ログ監視（略）
      - monitoring_engine.py — 監視の束ね実装
      - kill_switch.py       — kill.flag の書き込みロジック
      - alert_manager.py     — （アラート送信管理: LINE など）（略）
    - execution/             — 発注エンジン周りの実装群（Engine, OrderManager, BrokerFactory 等）
    - portfolio/             — ポートフォリオ構築（builder, sizing, risk_adjustment）
    - research/              — ファクター計算・探索（factor_research, feature_exploration）
    - ai/
      - news_nlp.py          — ニュース NLP（OpenAI）で ai_scores を書き込む
      - regime_detector.py   — 市場レジーム判定（ma200 + LLM）
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - data/                  — （実行時生成）DB、フラグ、PID、ログ等出力先（デフォルト）
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - config/                — 各種 YAML 設定ファイル（system_config.yaml 等。validate_config で検証）

補足（開発者向け）
- .env 自動読み込み
  - プロジェクトルートを .git または pyproject.toml を基準に探索し、.env → .env.local の順に読み込みます（OS 環境変数は上書きされません）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト / モック
  - ペーパートレード（MockBroker）や OpenAI 呼び出し（内部の _call_openai_api） は unittest.mock で差し替えてテスト可能な設計になっています。
- 依存ライブラリ
  - DuckDB、psutil、openai、PyYAML（任意）等が利用されます。テスト・CI ではこれらのインストールが必要です。

問題報告・貢献
- バグや改善提案は issue を作成してください。設計意図や運用面の注意点はソース内コメントに詳細を記載していますので参照してください。

以上。README の不足箇所・追加してほしい具体例（起動スクリプトの systemd / docker 化例、CI/テスト手順 など）があれば教えてください。