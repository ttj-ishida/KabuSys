# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、戦略の研究・ポートフォリオ構築・発注エンジン・監視・AI（ニュース NLP / レジーム判定）などを含む自動売買基盤の一部実装です。設計上、本番（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて動作します。

---

## 概要

- DuckDB を用いたファクター計算・リサーチ機能
- SQLite による監視ログ保存・注文履歴（monitoring.db / paper_trading.db）
- ExecutionEngine による発注処理（paper_trading モードでは MockBroker を使用）
- MonitoringEngine によるシステム／注文／リスク監視と Kill Switch（フラグファイル）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価・レジーム判定（APIキー必須）
- 設定ウィザード（.env 作成）と設定検証 CLI を提供

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて挙動切替）
  - run_monitoring.py: SystemMonitor をポーリング実行
- 設定管理
  - config_setup.py: 対話式で .env を作成・更新
  - validate_config.py: .env と config/*.yaml の検証（--strict オプション）
- モニタリング
  - monitoring/monitoring_db.py: SQLite スキーマ初期化と永続化 API
  - monitoring/system_monitor.py: CPU / メモリ / ディスク / データ鮮度監視
  - monitoring/trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py（各種監視・アラート・Kill Switch）
- 発注・リスク管理（execution/*）
  - BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注処理チェーン）
- ポートフォリオ構築（portfolio/*）
  - 銘柄選定、重み算出、リスク調整、ポジションサイズ計算（純粋関数群）
- 研究（research/*）
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリー
- AI（ai/*）
  - news_nlp.py: ニュース記事を集約して OpenAI に送信、ai_scores テーブルに書き込み
  - regime_detector.py: MA とマクロニュースを合成して日次レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

## セットアップ手順 (開発環境)

1. Python 環境を準備（推奨: v3.9+）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証を行う場合）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 初期設定 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（下記サンプル参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もFAIL扱いにする場合:
     - python -m kabusys.validate_config --strict

注意: 環境変数の自動ロードは、プロジェクトルートに `.git` または `pyproject.toml` がある場合に .env / .env.local を自動で読み込みます。環境変数の自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数（代表）

- 必須（起動前に必ず設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live

- データベース / ファイル
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 sqlite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジン pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）

- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動（instant | partial | never | reject）

- その他
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1"/"0"、デフォルト 0）

サンプル .env（最低限）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

（.env は絶対に Git にコミットしないでください）

---

## 使い方（起動・実行）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告含め失敗）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパートレードの切替）
  - 本番（例）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（DB は data/paper_trading.db に分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  備考:
  - 起動時にプロセス優先度を高に設定します（プラットフォーム依存で失敗することがありますが警告で継続します）。
  - data/stop_requested.flag が存在すると起動を中止または実行中に停止します（起動前に存在する場合、Engine は起動しません）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は本番 sqlite_path を使用して監視 DB を初期化します（環境に依らず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Kill Switch / 停止
  - KillSwitch は監視結果に基づき `data/kill.flag` を書き込み、ExecutionEngine 側がこれを検出して安全に停止します。
  - 手動で停止したい場合は `data/stop_requested.flag` を作成すると run_monitoring / run_execution のループが終了します。

---

## ログ

- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- 標準出力にも同じログを出します（StreamHandler）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。

---

## データベースとスキーマ

- monitoring_db.init_monitoring_db() により以下のテーブルを作成します（冪等）:
  - system_status: CPU/メモリ/ディスク/プロセスの状態ログ
  - trade_logs: 発注イベントログ（latency_ms 等のカラムを含む）
  - positions: 保有ポジション
  - risk_logs: リスク関連のイベントログ
  - dashboard: 集計情報（id=1 の単一行）

- run_execution は paper_trading モード時に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。

- DuckDB は分析用の prices_daily / raw_financials / raw_news 等テーブルを想定しており、research / ai モジュールは DuckDB 接続を受け取って SQL ベースで計算します。

---

## 主要モジュール（用途 / API 抜粋）

- kabusys.config.Settings
  - 各種設定値をプロパティで取得（env, sqlite_path, duckdb_path, paper_sqlite_path, paper_fill_mode 等）

- kabusys.portfolio
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)  # OpenAI API キー必須（引数または env）
  - regime_detector.score_regime(conn, target_date, api_key=None)

- kabusys.monitoring.MonitoringDB
  - init_monitoring_db(conn)
  - log_system_status / log_trade_event / upsert_dashboard / log_risk_event / get_dashboard

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, RiskManager, Reconciler 等 — 起動スクリプトから組み立てられる)

その他:
- data/  : デフォルトの DB / flag / pid ファイルが置かれることを想定
- logs/  : ログ出力先（デフォルト）

---

## 運用上の注意・よくある質問

- ペーパートレードは本番 DB と完全分離するよう設計されています。KABUSYS_ENV=paper_trading を使用してください。
- OpenAI の利用は API キーが必要です。rate limit（429）やネットワーク障害に対しては実装側でリトライを行いますが、コストやレイテンシを考慮して運用してください。
- kill.flag / stop_requested.flag はファイルベースの制御のため、運用上はアクセス権や自動クリア設定（KILL_FLAG_CLEAR_ON_START）に注意してください。特に本番では自動クリアを無効にすることを推奨します。
- logging_setup はログディレクトリが作成できない場合でもコンソールログのみで動作するようフォールバックします。
- Windows / POSIX のプロセス優先度設定はプラットフォーム差分に対応しますが、権限不足で失敗するケースがあります（警告で継続）。

---

## トラブルシューティング

- .env の自動読み込みが動作しない
  - プロジェクトルートが特定できない可能性があります（.git / pyproject.toml を基準に探索）。その場合手動で環境変数を設定するか `KABUSYS_DISABLE_AUTO_ENV_LOAD` を操作してください。

- DuckDB / SQLite の接続エラー
  - パスの親ディレクトリが存在しないと警告が出ます。必要に応じてディレクトリを作成してください。monitoring 起動時にテーブルは自動作成されます。

- OpenAI API のエラー
  - API キーが設定されているか、ネットワーク接続、レート制限を確認してください。news_nlp と regime_detector はリトライを実装していますが、失敗した場合はフェイルセーフで進めます（例: macro_sentiment=0.0）。

---

この README はコードベースの主要部分（設定、起動スクリプト、モジュールの役割、運用注意）をまとめたものです。より詳細な実装ドキュメント（設計仕様書や各モジュールの詳細）は別途参照してください。必要であれば各モジュールの API 使用例や設計ドキュメントの草案を追加で作成します。