KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。  
主なコンポーネントは次の通りです。

- ExecutionEngine: 発注・リスク管理・約定管理（paper_trading / live の切替あり）
- Monitoring: システム稼働状態・注文状況・リスク指標のポーリング監視とアラート / Kill Switch
- Research: DuckDB を用いたファクター計算・将来リターン解析・特徴量探索
- Portfolio: 候補選定、重み付け、ポジションサイズ決定、セクター制約・レジーム補正
- AI モジュール: ニュース NLP（OpenAI）によるセンチメント評価・レジーム判定
- CLI ツール: 環境設定ウィザード・設定検証・Paper Trading 検証レポート生成 等

機能一覧
--------
主な機能・挙動（抜粋）:

- .env ウィザード（config_setup）で環境変数ファイルを対話的に生成
- validate_config による起動前の設定検証（--strict で警告を fail 扱い）
- ExecutionEngine は KABUSYS_ENV に応じて実運用（live）／ペーパートレード（paper_trading）を切替
  - paper_trading は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）に記録
- Monitoring は定期ポーリングで system / trade / risk をチェックし、条件で data/kill.flag を書込んで停止シグナルを送る
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - Monitoring は環境設定に関わらず本番 sqlite_path を使用して監視データを記録
- DuckDB を用いた研究用クエリ（prices_daily, raw_financials など）
- OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント評価／レジーム判定（API キー必要）
- ログ設定ユーティリティ（コンソール出力 + 日次ローテートファイル出力）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 利用）

セットアップ手順
----------------

1. Python 環境を用意
   - 推奨: Python 3.10+（本リポジトリの typing 表記を考慮）
   - 必要なパッケージ: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（validate_config の YAML 検証を行う場合）など
   - 例: poetry / pipenv / pip を利用してインストール

2. リポジトリルートで .env を作成（自動読み込みが有効）
   - 対話式ウィザードで生成する:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードを使いたくない／自動化する場合は .env を直接作成してください。
   - 自動環境読込を無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 必須環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI モジュールを使う場合）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト instant）

4. ログディレクトリ
   - デフォルトは logs/
   - LOG_DIR 環境変数で変更可能
   - ログは日次ローテーションで最大 30 日保持されます

5. DB 初期化
   - Monitoring 用のテーブルは起動時に自動で作成されます（init_monitoring_db）
   - DuckDB は分析用に必要なテーブル（prices_daily, raw_financials, raw_news など）を用意する必要があります（ETL/データロードは別途）

使い方（コマンド/実行例）
-----------------------

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # strict モード（警告も失敗扱い）
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動
  - 通常（パッケージ実行）:
    ```
    python -m kabusys.run_execution
    ```
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録し、MockBrokerClient を使用します。
  - 停止方法: デプロイ環境では data/stop_requested.flag を作成すると起動中のスレッドが停止プロセスに入ります。Kill Switch は data/kill.flag を作成します（監視が検出して書き込む）。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視スクリプトは Settings に設定された sqlite_path（監視 DB）を使い、duckdb へも接続します
  - 終了: data/stop_requested.flag の作成または Ctrl+C

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定（引数で渡すことも可能）
  - DuckDB に raw_news, news_symbols, ai_scores, market_regime 等のテーブルが存在すること
  - 例:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上の重要ポイント
--------------------

- Kill Switch / Stop フラグ:
  - 停止用フラグ: data/stop_requested.flag（run_execution / run_monitoring が参照）
  - Kill Switch が書き込むフラグ: data/kill.flag（ExecutionEngine に停止シグナルを送るために監視が書き込む）
  - Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に kill.flag を自動で消去する（本番では 0 推奨）

- データ鮮度と監視:
  - SystemMonitor は DuckDB の get_last_price_date 等からデータ鮮度をチェックします（FRESHNESS_DAYS=3 など）
  - RiskMonitor は dashboard のハイウォーターマークを追跡しドローダウン/ポジション上限を監視します

- ログと優先度:
  - 全起動スクリプトは setup_logging() を呼び出します（logs/<app_name>.log）
  - 起動直後に set_process_priority("high") が呼ばれるため、psutil が必要です（権限によっては設定に失敗して警告となる）

ディレクトリ構成（主要ファイル）
-------------------------------

以下は src/kabusys 以下の主要モジュール構成（抜粋）:

- kabusys/
  - __init__.py
  - config.py             — 環境変数読み込み / Settings
  - config_setup.py       — .env 対話式ウィザード
  - validate_config.py    — 設定検証 CLI
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py    — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - execution/            — Execution エンジン関連（broker_factory, engine, order_manager, risk_manager, reconciler, order_repository 等）
  - monitoring/
    - monitoring_db.py    — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py   — システム監視ロジック
    - trade_monitor.py    — 注文・約定監視（省略ファイル）
    - risk_monitor.py     — リスク監視（ドローダウン・ポジション上限）
    - kill_switch.py      — Kill Switch の管理
    - monitoring_engine.py— 複数 Monitor を束ねるエンジン
    - alert_manager.py    — アラート送信（LINE 等）（省略ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 発注株数計算
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py   — momentum/value/volatility ファクター計算
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py          — ニュース NLP / OpenAI 呼び出しと ai_scores 書込
    - regime_detector.py   — マクロ + MA200 からレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

補足（開発者向け）
-----------------

- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml が存在するパス）を基に .env/.env.local を自動で読み込みます。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env パース:
  - シンプルなシンタックス対応（export キー、シングル/ダブルクォート、コメント処理）
- テスト・モック:
  - AI 呼び出し関数（_openai_周り）は _call_openai_api を patch することでテストしやすく設計されています。
- マイグレーション:
  - init_monitoring_db は既存 DB に対して列追加（peak_value, latency_ms）などの簡易マイグレーション処理を行います（冪等）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（開発初期段階想定）

最後に
------
本 README はソースコード内の docstring や設計コメントに基づいてまとめています。実運用前に必ず python -m kabusys.validate_config で設定を検証し、必要な API キーや DB テーブルが揃っていることを確認してください。必要であれば README に追加したい補足（例: デプロイ手順、systemd / docker のユニット例、DB スキーマサンプルなど）を教えてください。