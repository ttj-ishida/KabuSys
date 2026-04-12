KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システムのライブラリ／小規模アプリ群です。
主要な機能は「発注実行（ExecutionEngine）」「監視（MonitoringEngine）」「リサーチ／ファクター計算」「ポートフォリオ構築」「AI を使ったニュースセンチメント評価」などです。本 README はソースコード（src/kabusys 以下）を基に、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

前提
----
- Python 3.10 以上（PEP 604 の表記（X | Y）を使用しているため）
- SQLite（標準ライブラリ sqlite3 を使用）
- DuckDB（duckdb パッケージ）
- ネットワーク接続（LINE / OpenAI など外部 API を使う場合）

主な依存パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit（ダッシュボードを使う場合）

requirements.txt がない場合は上記をインストールしてください:
pip install duckdb psutil openai requests streamlit

プロジェクト概要
--------------
KabuSys は次の領域をカバーします。

- Execution（発注/注文管理）
  - BrokerClient を通じた発注処理、OrderManager によるステートマシン、起動時のリコンシリエーション（Reconciler）。
  - Paper trading（模擬発注）用に本番 DB と分離した paper_trading モードを提供。

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine。
  - 監視ログは SQLite に永続化（monitoring_db.init_monitoring_db によるスキーマ初期化）。
  - Streamlit ダッシュボードで監視状況表示。
  - LINE プッシュ通知用 AlertManager、kill.flag による ExecutionEngine 停止機構（KillSwitch）。

- Research / Portfolio
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）。
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターの統計サマリー。
  - ポートフォリオ構築（候補選定、等配分/スコア加重）、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算（単元丸め、aggregate cap）。

- AI（OpenAI を利用）
  - news_nlp: ニュース記事をまとめて LLM に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ保存。
  - regime_detector: ETF（1321）のMA乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull/neutral/bear）を市場レジームテーブルへ書き込み。

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成する CLI ツール。
  - Streamlit ベースの監視ダッシュボード。

主な機能一覧
--------------
- 環境設定の自動読み込み（.env / .env.local、ただし OS 環境変数を保護）
- ExecutionEngine 起動スクリプト（本番／paper_trading を選択）
- MonitoringEngine 起動スクリプト（ポーリングループ、MONITOR_POLL_INTERVAL で間隔調整）
- 監視ログ保存用 SQLite スキーマ（system_status, trade_logs, positions, risk_logs, dashboard）
- Streamlit ダッシュボード（監視状況の可視化）
- Paper Trading の検証レポート生成（期間指定可）
- DuckDB を使ったファクター計算・リサーチ機能
- OpenAI を使ったニュースセンチメント評価（バッチ、リトライ、レスポンス検証）
- プロセス優先度・CPU アフィニティ設定ユーティリティ（psutil 経由、Windows / POSIX 対応）
- KillSwitch による外部フラグでの ExecutionEngine 強制停止（data/kill.flag）

セットアップ手順
----------------

1. リポジトリをクローン／チェックアウト

2. Python 仮想環境を作成して有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   pip install duckdb psutil openai requests streamlit

   （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）

4. データディレクトリを作成
   mkdir -p data

5. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（既存の OS 環境変数は上書きされません）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須の場面あり）
   - KABU_API_PASSWORD — kabuステーション API（必須の場面あり）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
   - PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject（デフォルト: instant）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH — kill.flag パス（デフォルト: data/kill.flag）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

   例 .env（最小）
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   KABUSYS_ENV=development

6. DB の初期化
   - 監視用 SQLite: run_monitoring / run_execution 起動時に init_monitoring_db() により必要テーブルが作成されます。
   - DuckDB: prices_daily 等のテーブルはリサーチ機能で参照されます。外部データロードは別途実装してください。

使い方
------

- Monitoring（監視ポーリング）
  Monitoring は本番 sqlite_path を使用します（KABUSYS_ENV に依存しません）。
  簡単な起動例:
  python -m kabusys.run_monitoring

  - ポーリング間隔を環境変数で変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ※ 1 秒以上の正の整数を指定してください。無効値はデフォルト 60 秒にフォールバックします。

- Execution（発注実行）
  ExecutionEngine を起動（paper_trading モードでは MockBroker を使用し、paper DB に記録されます）:
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用の DB を使用します:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  - 起動時に PID ファイルを書き、指定パス（Settings.pid_file_path）に保存します。kill.flag により外部から停止指示が可能です。

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  もしくは:
  streamlit run -m kabusys.monitoring.streamlit_dashboard -- --db data/monitoring.db

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  期間を指定する例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB を明示する例:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定し、kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime を呼び出すことで処理できます。
  - これらは DuckDB の raw_news / news_symbols / ai_scores / prices_daily 等のテーブルを参照・更新します。
  - 外部 API のエラー時はフェイルセーフでスコアをスキップまたはデフォルト値にフォールバックします。

設定（Settings）について
-------------------------
設定は kabusys.config.Settings 経由で取得されます。特徴:

- .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数は保護） — 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- KABUSYS_ENV の有効値: development | paper_trading | live
- PAPER_FILL_MODE の有効値: instant | partial | never | reject
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

重要な実装上の注意
-----------------
- run_monitoring.py は KABUSYS_ENV にかかわらず“本番”の sqlite_path（Settings.sqlite_path）を使用します。
- run_execution.py は KABUSYS_ENV=paper_trading の場合 paper_trading 用 SQLite（Settings.paper_sqlite_path）を使用し、本番 DB と分離します。
- OpenAI API 呼び出しはリトライ処理やレスポンス検証を行いますが、API キー未設定時は例外を投げます（明示的に捕捉して呼び出し側でハンドリングしてください）。
- Process priority（優先度）設定: 起動時に set_process_priority("high") を呼び出しています。psutil のアクセス権限やプラットフォームにより設定に失敗する場合があります（ログに警告）。

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込み
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — Paper Trading 検証レポート CLI
- monitoring/
  - __init__.py
  - monitoring_db.py       — SQLite スキーマ初期化と永続化 API
  - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
  - system_monitor.py      — CPU/mem/disk/process/data freshness 監視
  - trade_monitor.py       — 注文滞留・約定異常監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - alert_manager.py       — LINE Push 通知
  - kill_switch.py         — kill.flag 管理
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py    (一部参照)
  - reconciler.py
  - execution_engine.py    (参照)
  - broker_factory.py      (参照)
  - ...                   (実装に応じた追加ファイル)
- ai/
  - __init__.py
  - news_nlp.py            — ニュース NLU / スコアリング
  - regime_detector.py     — 市場レジーム判定
- research/
  - __init__.py
  - factor_research.py     — momentum/volatility/value ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- utils/
  - __init__.py
  - process_priority.py    — プロセス優先度・CPU affinity

監視 DB スキーマ（主なテーブル）
--------------------------------
- system_status(recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs(logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions(code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs(logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard(id=1 の1行保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

追加の注意点 / ベストプラクティス
--------------------------------
- 本番運用時はログレベルや環境変数（KABUSYS_ENV=live）を適切に設定してください。
- Paper Trading は本番 DB と分離するため、KABUSYS_ENV=paper_trading を使って安全に検証できます。
- OpenAI を呼び出す機能は API コストが発生するため、キーや呼び出し頻度に注意してください。
- monitoring の間隔やリスク閾値（Settings の CPU/MEM/DISK%、RiskMonitor の閾値など）は運用に合わせて調整してください。

貢献・拡張案
-------------
- BrokerClient（実際のブローカー接続）実装の追加／拡張
- stocks マスタを持たせ lot_size を銘柄別対応
- Streamlit ダッシュボードのグラフや履歴表示の強化
- テスト（ユニット／統合）・CI の整備
- DuckDB テーブルの初期データロード／ETL パイプライン

お問い合わせ
-------------
ソースを読んで疑問点があれば、実装箇所（上記ファイル）を参照してください。README にない実行方法や CI / デプロイ手順はプロジェクト固有の運用ドキュメントを参照してください。

以上。