# KabuSys

日本株自動売買システムのコアライブラリ群（ライブラリ兼ローカル実行用コード）。  
この README はリポジトリの主要機能、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

注意: ソース内の docstring に従い環境変数や DB のパス、フラグファイルでプロセス制御を行います。実運用では十分な権限管理・API キー管理を行ってください。

---

## プロジェクト概要

KabuSys は以下の機能群を持つ自動売買／リサーチ基盤のコアモジュール群です。

- 注文管理と ExecutionEngine（ブローカー抽象化、リスク管理、再同期）
- 監視サブシステム（System / Trade / Risk モニタ、アラート送信、KillSwitch）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ決定、セクター制限）
- リサーチ（ファクター計算、将来リターン計算、IC 等）
- AI連携（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

基本方針として、本番注文処理とリサーチ／AI 等の機能は分離され、DB（SQLite / DuckDB）を通してやり取りします。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker 抽象化、OrderManager、Reconciler（再同期）、RiskManager
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBroker を用い、paper DB を使用

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（定期ポーリング）
  - MonitoringDB（SQLite に監視ログ永続化）
  - KillSwitch（フラグファイルで Execution 停止）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視データの可視化）
  - run_monitoring.py（監視ポーリングループ起動）

- Portfolio（純粋関数）
  - 銘柄候補選定、等金額 / スコア加重の重み計算
  - ポジションサイズ算出（リスクベース、単元考慮、aggregate cap）
  - セクター上限制御、レジーム乗数

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC、統計サマリ（外部依存を極力避け DuckDB ベース）

- AI
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント算出と ai_scores 書き込み
  - regime_detector: ETF とマクロニュースを使った日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成（コマンドライン）
  - Streamlit ダッシュボード起動スクリプト（monitoring/streamlit_dashboard.py）

---

## 必要条件（概略）

- Python 3.10 以上（コードは 3.10 の型ヒント・構文を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ）
- ネットワーク接続（ブローカー API / OpenAI / LINE を使う場合）

プロジェクトに requirements.txt が無い場合は手動でインストールしてください。例:

pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（使う機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（リサーチ等）
- KABU_API_PASSWORD — kabuステーション API 用（Execution）
- OPENAI_API_KEY — OpenAI (news_nlp / regime_detector) を使う場合

主要なオプション:
- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading の場合は MockBroker を使い DB は `data/paper_trading.db` を使用
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の約定振る舞い（instant/partial/never/reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の送信に使用（空なら送信は行わない）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

その他監視閾値など:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- PID_FILE_PATH, KILL_FLAG_PATH 等

例（.env）:
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

---

## セットアップ手順（ローカル開発向け・最小）

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトで requirements.txt を用意している場合はそれを使用してください）
4. 環境変数設定
   - プロジェクトルートに `.env` を作成して必要なキーを設定してください（上記参照）
   - または OS 環境変数として設定
5. データディレクトリを作成
   - mkdir -p data

注意: run_execution/run_monitoring は起動時に process priority の設定（psutil 経由）を試みます。権限が無い・プラットフォーム非対応の場合は警告が出てスキップされます。

---

## 使い方（主要コマンド）

- 監視ループの起動（常時監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して paper DB に書き込みます

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード（監視状況の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI スコア（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して日付指定で実行すると ai_scores を書き込みます

- レジーム判定（プログラムから呼び出す）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

テスト用: MonitoringEngine は MonitoringEngine.run_once() を呼ぶことで各モニタを 1 回だけ実行できます。ユニットテストでは外部 API 呼び出しをモックして使います。

---

## 停止・制御

- run_monitoring / run_execution はプロジェクトの data ディレクトリ内のフラグファイルで停止シグナルを扱います:
  - data/stop_requested.flag — スクリプトのループを検知して安全終了
  - data/kill.flag — KillSwitch が書き込み、ExecutionEngine に停止を促す（手動トリガーや KillSwitch ロジック）
- ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を使ってプロセスの存否を監視します。PID ファイルが stale （存在するがプロセス無し）なら削除して警告を記録します。

---

## 主要モジュールの簡易リファレンス

- kabusys.config.Settings および settings — 環境変数のラッパ。自動的に .env をロード。
- kabusys.monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, MonitoringDB, AlertManager, KillSwitch
- kabusys.execution
  - ExecutionEngine（run_session メソッドで実行）、OrderManager、OrderRepository、Reconciler、RiskManager
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai
  - score_news (news_nlp)、score_regime (regime_detector)

各関数・クラスはソースの docstring に詳細が記載されています。内部 API を呼ぶ際は docstring を参照してください。

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- run_monitoring.py — 監視ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py (一部実装あり)
  - reconciler.py
  - execution_engine.py (起動処理など)
  - broker_factory.py, broker_api.py（ブローカー抽象）
  - order_record.py
  - その他発注周り
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py
- data/（実行時に使用するファイル置き場。プロジェクトルートに配置）
  - monitoring DB / duckdb / pid / flag 等

プロジェクトルート:
- .env, .env.local (オプション)
- data/ (実行時作成)
  - monitoring.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - paper_trading.db (Paper Trading 用、KABUSYS_ENV=paper_trading)
  - execution.pid, stop_requested.flag, kill.flag

（上記はコードの docstring / ファイル中のデフォルトパスに基づく）

---

## 運用上の注意点

- 実環境では API キーやパスワードを Git に含めないこと。`.env.local` を .gitignore に入れる運用を推奨。
- Paper Trading と Live は DB を明確に分離する設計（paper_trading は別 SQLite）です。運用ミスで本番 DB を上書きしないよう注意してください。
- OpenAI / ブローカー API 呼び出し部分はレート制限・一時エラーに対するリトライが実装されていますが、実運用では追加の監視やバックオフ戦略の調整を検討してください。
- process priority / cpu affinity の設定はプラットフォーム依存です。権限不足で失敗する可能性があります（警告を出してスキップされます）。

---

## よくある操作例

- 監視をデーモン化して実行（簡易例）
  - nohup env MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

- Execution を Paper Trading で起動
  - env KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 強制停止（Execution に停止シグナル）
  - echo "manual stop" > data/kill.flag
  - または touch data/stop_requested.flag（run_monitoring/run_execution が検出して終了）

---

README は以上です。より詳しい API や設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）はソース内参照コメントや別途用意されている設計書を参照してください。必要であれば README に追加したいコマンド例や運用手順（systemd ユニット、Docker 化の手順等）を教えてください。