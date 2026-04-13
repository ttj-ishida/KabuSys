KabuSys
=======

KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。
本リポジトリには次の機能群が含まれます: 注文実行エンジンの起動・復旧ロジック、監視エンジン、ポートフォリオ構築・ポジション計算、ファクター計算、ニュースの LLM ベースセンチメント評価（OpenAI）、および運用・検証用のユーティリティ類。

バージョン: 0.1.0

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading / live / development を切り替え可能
  - Paper Trading 時は MockBroker を使い、data/paper_trading.db に完全分離して記録
  - 起動時にプロセス優先度を High に設定
  - 再起動後のリコンシリエーション（Reconciler）で未同期注文やポジション差分を検出・同期
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）の定期ポーリングとログ永続化（SQLite）
  - 注文滞留・約定異常・ドローダウン監視、kill.flag による ExecutionEngine 停止シグナル発行
  - LINE push を使ったアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボードを提供
- Portfolio モジュール
  - 候補選択、等配分・スコア配分、リスク調整（セクターキャップ／レジーム乗数）
  - ポジションサイズ決定（単元丸め・利用可能現金でのスケーリング等）
- Research モジュール
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI 関連
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ
-----------
1. Python と依存ライブラリ
   - Python 3.9+ を推奨（duckdb や openai ライブラリ等が必要）
   - 必要パッケージ（例）:
     pip install duckdb psutil openai requests streamlit

   - sqlite3 は標準ライブラリに含まれます。

2. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定挙動、デフォルト "instant"）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
     - PID_FILE_PATH（デフォルト data/execution.pid）
     - KILL_FLAG_PATH（デフォルト data/kill.flag）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
     - LOG_LEVEL（"DEBUG","INFO",...）

   - .env のフォーマットは shell 形式（export KEY=val も可）です。config._load_env_file により .env, .env.local を読み込みます。

使い方（運用向け）
-----------------

1) 監視ループを起動する
   - 簡易実行:
     python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書きできます（例: 30秒）:
     export MONITOR_POLL_INTERVAL=30
   - run_monitoring は Settings を参照し、monitoring 用 DB（sqlite_path）は常に本番設定を使います。

2) ExecutionEngine（取引実行）を起動する
   - 開発/本番/ペーパーを切り替え:
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
   - paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と完全分離します。
   - 起動時に PID ファイルを書き、プロセス優先度を High に設定します。kill.flag による停止機構に対応しています。

3) Streamlit 監視ダッシュボード
   - 起動方法（例）:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
   - 単発実行:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定できます（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH → data/paper_trading.db）。

5) AI 系バッチ（ニュース・レジーム）
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受け取り、OpenAI API キーを必要とします（引数または OPENAI_API_KEY 環境変数）。
   - 実運用では定期バッチ（cron や Airflow）から呼び出す想定です。

運用上の注意
-------------
- run_monitoring と run_execution は起動時に init_monitoring_db() を呼んで必要テーブルを冪等的に作成します。
- MONITORING は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使います。
- pid ファイルと kill.flag により ExecutionEngine の存在確認/強制停止を行います。必要に応じて KILL_FLAG_CLEAR_ON_START 環境変数を設定して起動時にフラグをクリアできます。
- OpenAI API 呼び出しはレート制限や一時的な失敗を考慮してリトライやフェイルセーフ（失敗時はデフォルト値で継続）を実装していますが、API キーやコスト管理は運用側で十分に注意してください。
- DuckDB / SQLite のファイルパスは Settings で柔軟に上書き可能です。バックアップやローテーションを検討してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                   — 環境変数 / 設定ロード
- run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート
- monitoring/
  - __init__.py
  - monitoring_db.py           — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py          — システム状態 / データ鮮度チェック
  - trade_monitor.py           — 注文滞留・約定異常監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag 管理
  - alert_manager.py           — LINE 通知
  - monitoring_engine.py       — 複数 Monitor の統合ループ
  - streamlit_dashboard.py     — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - ... (OrderRepository / Engine 等、実行関連コンポーネント)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - __init__.py
  - news_nlp.py                — ニュース NLP + OpenAI 呼び出し
  - regime_detector.py         — 市場レジーム判定（MA200 + macro sentiment）
- utils/
  - __init__.py
  - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
- data/ (想定。実リポジトリでは含まれない可能性あり)
  - kabusys.duckdb (default)
  - monitoring.db (default)
  - paper_trading.db (paper mode)

例: .env.template（抜粋）
-----------------------
# KabuSys example .env
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

開発者向けメモ
---------------
- .env 自動ロードは config._find_project_root() によりプロジェクトルート（.git もしくは pyproject.toml）から行われます。配布後の挙動を想定し、CWD に依存しない実装になっています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
- OpenAI やネットワーク依存の箇所は内部関数を patch してユニットテスト可能（コード内に patch 用のコメントあり）。

ライセンス / 貢献
-----------------
本 README はコードベースから自動生成されたドキュメント草案です。実際のライセンスや Contributing ガイドはリポジトリのルートにある LICENSE / CONTRIBUTING.md を参照してください。

お問い合わせ
------------
不明点や運用上の質問があれば、プロジェクトの Issue またはチーム内のドキュメントに記載してください。