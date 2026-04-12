KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。本リポジトリは以下の主要領域を含みます。

- 実取引（Execution）エンジン（ブローカー抽象化、オーダー管理、リコンシリエーション）
- 監視（Monitoring）：システム状態、注文滞留、リスク監視、LINE 通知、ダッシュボード
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、ポジションサイジング、セクター制限
- リサーチ（Research）：ファクター計算・特徴量探索
- AI 補助（AI）：ニュース NLP によるセンチメント評価・市場レジーム判定
- ツール：Paper Trading の検証レポート生成 等

現状バージョン: 0.1.0

主な機能
--------
- ExecutionEngine 起動スクリプト（本番 / ペーパートレーディング分離）
  - KABUSYS_ENV により環境切替（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を利用し、data/paper_trading.db に記録
- Monitoring（監視）
  - システムリソース（CPU/MEM/DISK）と Execution プロセスの生存確認
  - 注文滞留（stale order）・約定価格異常の検出
  - ドローダウン・ポジション上限の監視と kill.flag による停止シグナル
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用）
- ポートフォリオ構築ライブラリ
  - 候補選定、等重／スコア重み付け、リスクベースのポジションサイジング
  - セクター集中制限とレジーム乗数
- リサーチ用モジュール
  - Momentum / Volatility / Value ファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Information Coefficient）等
- AI モジュール
  - raw_news から OpenAI（gpt-4o-mini）で銘柄別センチメント算出（ai_scores へ書込）
  - マクロニュース + ETF ma200 を用いた market_regime 判定と永続化
  - 失敗時のフェイルセーフ（API 失敗はスコア 0.0 等で継続）
- ユーティリティ
  - .env ファイル自動読み込み（プロジェクトルート検出）、環境保護設定
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

セットアップ
------------
前提:
- Python 3.10+
- pip

推奨インストール例:
1. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  (Linux/macOS)
   .venv\Scripts\activate     (Windows)

2. 依存ライブラリをインストール
   pip install duckdb psutil requests openai streamlit

（必要に応じて他ライブラリを追加してください）

環境変数 / .env
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env を自動で読み込みます。
  - OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（抜粋）:
  - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード (instant|partial|never|reject)（デフォルト: instant）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等（実運用に必要）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）※ run_monitoring 用

サンプル .env（最小）
    KABUSYS_ENV=development
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    OPENAI_API_KEY=sk-...

使い方（代表的なコマンド）
------------------------
- 実行エンジン（ExecutionEngine）を起動
  - 本番モード:
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
  - ペーパートレード（DB を分離）:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
  実行開始時にプロセス優先度を "high" に設定します。paper_trading 時は paper_trading.db に書き込みます。

- 監視ループを起動（SystemMonitor）
  - デフォルト 60 秒間隔でポーリング:
    python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
  監視は常に production の sqlite_path（Settings.sqlite_path）を参照して監視ログを保存します。

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  （監視 DB を読み取り専用で表示します）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  期間絞り込み:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  デフォルト DB パスは data/paper_trading.db。--db で上書き可能。

- AI モジュール（ニューススコア／レジーム判定）
  - OpenAI API キーの設定が必要: OPENAI_API_KEY を指定
  - コードから呼び出す例:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="sk-...")
  - 外部 API 呼び出しに対するリトライ・フェイルセーフが実装されていますが、API 使用料とレート制限に注意してください。

重要な設計注意点
- paper_trading は本番 DB と物理的に分離（PAPER_TRADING_SQLITE_PATH）されます。ペーパートレードの結果が本番 DB に混入しないよう設計されています。
- .env の自動ローディングでは OS 環境変数が保護されます（.env による上書きは行われません、ただし .env.local は override=True で上書きし得ます）。
- OpenAI 呼び出しのレスポンスは厳密な JSON を期待しますが、実装は一部ヘルパーで前処理（{...} 抽出）を行いフォールバックします。
- Monitoring の kill.flag（Settings.kill_flag_path）により ExecutionEngine に停止シグナルを与えます。KillSwitch はドローダウンやポジション上限等の条件でフラグを書き込むロジックを持ちます。
- プロセス優先度設定は psutil を使用しており、プラットフォーム差（Windows / POSIX）を吸収します。権限不足時は警告を出してスキップされます。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py                  — パッケージ初期化（__version__）
- config.py                    — Settings / .env ロード
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor 起動スクリプト

サブパッケージ / ファイル（抜粋）
- kabusys/execution/
  - order_manager.py
  - reconciler.py
  - ...（ブローカー抽象やリポジトリ等）

- kabusys/monitoring/
  - monitoring_db.py            — SQLite スキーマ初期化 / 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
  - __init__.py

- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- kabusys/ai/
  - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          — マクロ + ma200 によるレジーム判定
  - __init__.py

- kabusys/tools/
  - paper_verification_report.py

- kabusys/utils/
  - process_priority.py         — プロセス優先度 / CPU affinity

DB スキーマ（監視用） — 主要テーブル（init_monitoring_db による自動作成）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PK, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 固定 行: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

運用にあたっての補足
--------------------
- OpenAI を用いる機能は API キー・課金に注意してください。API 回数が多いとコストが発生します。
- DuckDB / SQLite のファイルパスは Settings で容易に変更できます。バックアップやファイルの配置に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒、1 以上）でポーリング間隔を変更可能。0 以下または無効な値はデフォルト 60 秒にフォールバックします。
- kill.flag のクリアは ExecutionEngine 起動時に行う設定（Settings.kill_flag_clear_on_start）で制御できます。
- 本リポジトリはコンポーネントごとに冪等性（init / upsert 等）を意識して設計されていますが、本番運用前に十分なテストを行ってください。

ライセンス・貢献
----------------
- （この README はコードベース説明用です。実運用や配布の際は適切なライセンス表記を追加してください。）

問い合わせ
----------
不明点や実装に関する質問があれば、該当のモジュール名（例: kabusys.monitoring.system_monitor）を添えて問い合わせてください。