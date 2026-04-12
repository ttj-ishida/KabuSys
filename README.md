# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のモジュール群（監視、発注実行、ポートフォリオ構築、リサーチ、AI支援など）を含みます。本 README はコードベースに基づき、プロジェクト概要・主要機能・セットアップ・実行方法・ディレクトリ構成を日本語でまとめたものです。

要点
- 本プロジェクトは SQLite / DuckDB をデータ層として利用します。
- Paper Trading（模擬売買）モードをサポートし、本番 DB と分離されます。
- 監視コンポーネントは別プロセスでポーリングし、監視ログを SQLite に永続化します。
- ニュースセンチメントやマクロ判定には OpenAI API を利用する実装があります（API キー必須）。
- 自動で .env / .env.local を読み込む仕組みを持ちます（必要に応じて無効化可能）。

プロジェクト概要
- 監視（monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine を提供。
  - system_status、trade_logs、risk_logs、positions、dashboard といったテーブルへ記録。
  - LINE による通知（AlertManager）、kill.flag による ExecutionEngine 停止シグナル機能あり。
  - Streamlit ベースの監視ダッシュボードを提供。
- 実行（execution）:
  - ExecutionEngine（起動スクリプト: run_execution）によりブローカーとの接続、リスク管理、注文管理、リコンシリエーションを実施。
  - Paper Trading 環境では MockBrokerClient を用い、専用の paper_trading DB に記録する設計。
- ポートフォリオ（portfolio）:
  - 候補選定・重み付け（等分配・スコア加重）やポジションサイズ計算、セクターキャップ / レジーム乗数などの純粋関数群を提供。
- リサーチ（research）:
  - DuckDB の prices_daily / raw_financials を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン、IC 計算や統計要約を提供。
- AI（ai）:
  - news_nlp: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に書き込む機能（score_news）。
  - regime_detector: ETF の MA とマクロニュースの LLM 結果を合成して market_regime を算出・永続化（score_regime）。
- ユーティリティ:
  - 環境設定管理（kabusys.config.Settings）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）

主な機能一覧（抜粋）
- run_monitoring.py: SystemMonitor をポーリングで継続実行（MONITOR_POLL_INTERVAL で間隔上書き可）。
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は paper_trading DB を使用）。
- monitoring_db.init_monitoring_db: 監視用 SQLite DB の初期化（テーブル作成・簡易マイグレーション対応）。
- MonitoringEngine.run: 複数 Monitor を束ねて定期実行。AlertManager 経由で LINE 通知。
- streamlit_dashboard.py: Streamlit による監視ダッシュボード（read-only モードで DB を開く推奨）。
- tools.paper_verification_report: Paper Trading DB を集計して検証レポートを CLI 出力。
- ai.score_news / ai.regime_detector.score_regime: OpenAI を用いたニューススコアリング・レジーム判定。

セットアップ手順（概要）
1. Python 環境
   - Python 3.9+ を推奨（実装は typing の modern 機能や pathlib を使用）。
2. 依存パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit（ダッシュボード用）
   - （必要に応じて）その他パッケージ
   例: pip install duckdb psutil requests openai streamlit
3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（主なもの）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須 API トークン（J-Quants）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: AI 機能利用時に必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用（未設定時は通知せずログのみ）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject。デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH: 実行プロセス制御用ファイルパス
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）
     - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
4. データディレクトリ作成
   - sqlite/duckdb のデフォルトパスは data/ 以下。必要に応じてディレクトリを作成してください。
   - 例: mkdir -p data

使い方（実行例）
- 監視ループ起動（プロダクションで常時実行するプロセス）
  - 環境変数を設定してから:
    - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 説明:
    - プロセス優先度を high に設定し、監視 DB に system_status 等を追記します。
    - MONITOR_POLL_INTERVAL が正の整数でない場合はデフォルト 60 秒にフォールバックします。

- ExecutionEngine 起動（発注エンジン）
  - KABUSYS_ENV を指定:
    - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
    - Paper Trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 説明:
    - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB とは分離されます。
    - 起動時にリコンシリエーション（Reconciler）を行い、未確定注文やポジション差分を確認します。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 出力:
    - 稼働率、注文成功率、送信率、レイテンシ統計、Pass/Fail 判定を標準出力に表示します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 読み取り専用で監視 DB を表示（存在しない場合はエラーメッセージ）。
    - ポートフォリオダッシュボード、ポジション、直近注文、システム指標を表示します。

- AI モジュール（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（DuckDBPyConnection）
    - api_key: OpenAI API キー（None の場合は環境変数 OPENAI_API_KEY を参照）
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API 利用には課金・API キーが必要。API 呼び出しはリトライ・フォールバックロジックを含みますが、キー未設定時は例外が発生します。

設定と挙動のポイント
- .env パース:
  - プロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動で読み込み。
  - export KEY=... 形式、クォートやコメント処理に対応。
  - 上書きルール: OS 環境 > .env.local（override）> .env（非 override）。
- MONITORING DB 初期化:
  - init_monitoring_db は冪等。既存 DB に対する簡易マイグレーション（列追加）も行います（例: latenc y_ms, peak_value）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_trading 用 SQLite を使用。PAPER_FILL_MODE により模擬約定挙動を設定可能。
- プロセス優先度 / CPU affinity:
  - set_process_priority("high"|"normal"|"low") を使用。Windows と POSIX を吸収。
  - 許可エラー（AccessDenied 等）はログ出力してスキップします。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine 停止を誘導します（冪等動作）。

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / Settings
  - run_monitoring.py     — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py         — monitoring DB 初期化 / MonitoringDB クラス
    - system_monitor.py        — システム・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン/ポジション上限監視
    - kill_switch.py           — kill.flag 制御
    - alert_manager.py         — LINE 通知
    - monitoring_engine.py     — 各 Monitor の統合・ポーリング
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine 等の実装群)
    - order_manager.py
    - reconciler.py
    - ...（他の execution 関連ファイル）
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定 / 重み計算
    - position_sizing.py       — 株数決定・スケーリング
    - risk_adjustment.py       — セクター上限 / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLU / OpenAI 連携
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント）
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity

監視 DB スキーマ（主要テーブル）
- system_status:
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs:
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions:
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs:
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard:
  - id (固定1), updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

注意事項 / ベストプラクティス
- OpenAI を利用する機能は外部 API 呼び出しが発生するため、APIキーの管理・呼出しのコストに注意してください。
- Paper Trading を活用して本番への影響を避けつつ挙動確認を行ってください。
- MONITOR_POLL_INTERVAL は短くしすぎないでください（デフォルト 60 秒）。0 または負の値はデフォルトにフォールバックします。
- .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有効）。
- Streamlit ダッシュボードは監視 DB へ読み取り専用で接続することを推奨します（起動時に read-only URI を使用）。

開発者向けメモ
- config.Settings は利用時にプロパティで値を解決します。未設定の必須キーは _require() により ValueError を投げます。
- DuckDB 接続は research / ai モジュールで SQL と Python の組合せで高速集計を行います。
- monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（列追加）を行うため、初回起動時の安全性を高めています。

以上がこのコードベースの主要な説明です。実行や環境設定で不明点があれば、どの機能／ファイルについて詳細を知りたいかを教えてください。必要に応じてサンプル .env.example や起動スクリプトのサンプルコマンドを追記します。