KabuSys — 日本株自動売買システム
=================================

このリポジトリは、KabuSys（日本株向けの自動売買および監視コンポーネント）の一部実装です。  
主に Execution（発注エンジン）、Monitoring（監視）、Research（ファクター計算）、Portfolio（銘柄選定・資金配分）、AI（ニュース NLP / レジーム判定）などのモジュールで構成されています。

主な特徴
--------
- 実運用を意識した設計
  - 実行エンジン（ExecutionEngine）と監視プロセスを分離
  - 停止フラグ / kill スイッチによる安全停止
  - PID / フラグファイルによるプロセス監視
- Paper Trading（模擬取引）の分離
  - KABUSYS_ENV=paper_trading 設定で本番 DB と分離（data/paper_trading.db 等）
- 監視機能
  - システム状態（CPU/メモリ/ディスク）・プロセス存在チェック
  - 注文の滞留・約定異常検出
  - ドローダウン / ポジション上限監視と KillSwitch
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用）
- 研究・因子計算
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB）
  - 特徴量探索（IC、将来リターン等）
- AI モジュール
  - ニュースを OpenAI API でセンチメント評価し ai_scores に保存
  - マクロニュース + ETF MA200 による市場レジーム判定
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、リスク調整、ポジションサイズ計算（単元丸め等）

セットアップ手順
----------------

前提
- Python 3.10+（型ヒントで union 表記などを利用）
- DuckDB、psutil、requests、openai、streamlit 等のライブラリ

推奨手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）
   - pip install duckdb psutil requests openai streamlit

3. 環境変数・.env
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（実行に必要なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルト値があるもの）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/... （デフォルト: INFO）
     - SQLITE_PATH: data/monitoring.db
     - DUCKDB_PATH: data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）

例 .env（参考）
    KABUSYS_ENV=development
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    OPENAI_API_KEY=sk-...

初期データディレクトリ
- data/ 以下に DB ファイルやフラグファイル（execution.pid, stop_requested.flag, kill.flag 等）を配置することが多いです。実行時に自動生成されますが、適切な権限を確認してください。

使い方
------

各種スクリプト / 起動方法の説明。

1) Execution Engine を起動する
- run_execution.py を実行して ExecutionEngine を起動します。
- 実行例:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され paper_trading 用 SQLite に記録されます（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。
  - Execution 用 PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
  - 優先度設定: 実行開始時に set_process_priority("high") を呼びます（権限に依存）。

2) Monitoring を起動する
- run_monitoring.py を実行して SystemMonitor のポーリングループを開始します。
- 実行例:
  - python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 以上の整数で指定。
- 挙動:
  - 監視は常に本番 sqlite_path を使用して監視テーブルを更新します（Settings.sqlite_path）。
  - data/stop_requested.flag を検知するとループを終了します。

3) Streamlit ダッシュボード（監視用）
- Streamlit 経由で監視ダッシュボードを参照できます（読み取り専用）。
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
- ツールスクリプト: kabusys.tools.paper_verification_report
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パス指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- 出力: 稼働率、注文成功率、レイテンシ指標、Pass/Fail 判定などを標準出力に表示します。

5) AI モジュールの利用（ニュース NLP / レジーム判定）
- 必須: OPENAI_API_KEY を環境変数または関数引数で渡す必要があります。
- 主要関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを読み書きしてニュースごとの ai_scores を生成します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成し market_regime テーブルを書き込みます。
- 実行例（Python REPL 等）:
    from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.ai.news_nlp import score_news
    score_news(conn, date(2026,4,1), api_key="sk-...")

注意点 / 運用メモ
- Monitoring のデータベース初期化は init_monitoring_db() で行われ、起動スクリプトが呼びます。手動で初期化する場合は同関数を利用してください。
- kill.flag と stop_requested.flag:
  - KillSwitch は通常の運用リスク（ドローダウン超過やポジション上限超過）を検知した際に Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine に停止シグナルを送ります。
  - stop_requested.flag（data/stop_requested.flag）は運用者が監視・実行プロセスの停止を要求するために用います。run_monitoring / run_execution はこれを検知して終了します。
- process priority / cpu affinity の設定は psutil の権限に依存します。失敗すると警告ログが出力されますが処理は継続します。
- DuckDB を利用したリサーチ系は大量データを効率的に処理する想定です。prices_daily / raw_financials 等のテーブルが必要です。
- Logging はシンプルに logging.basicConfig(level=INFO) が使われています。必要に応じて LOG_LEVEL を設定してください。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定読み込みロジック
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

modules:
- ai/
  - news_nlp.py                   — ニュース NLP（OpenAI 連携）
  - regime_detector.py            — レジーム判定（MA200 + LLM）
- monitoring/
  - monitoring_db.py              — SQLite ベースの永続化層 + MonitoringDB クラス
  - system_monitor.py             — システム監視（CPU/メモリ/ディスク/データ鮮度）
  - trade_monitor.py              — 注文滞留 / 約定異常監視
  - risk_monitor.py               — ドローダウン / ポジション上限監視
  - kill_switch.py                — kill.flag 管理
  - alert_manager.py              — LINE 通知
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py        — Streamlit ダッシュボード
- execution/
  - reconciler.py                 — 起動時の自動復旧 / リコンシリエーション
  - order_manager.py              — 発注ステートマシンの外向き API
  - (その他：broker_factory 等を含むがここに全ては列挙していません)
- portfolio/
  - portfolio_builder.py          — 候補選定 / 等重・スコア重み
  - position_sizing.py            — 株数計算・単元丸め・制限適用
  - risk_adjustment.py            — セクター制限・レジーム乗数
- research/
  - factor_research.py            — モメンタム / ボラ / バリュー等ファクター計算（DuckDB）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
- utils/
  - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
- data/                           — 実行時に利用する（DB, PID, フラグ等。リポジトリに含まれない場合あり）

API / 主要クラス（抜粋）
-----------------------
- Settings (kabusys.config)
  - env, is_live, is_paper, pid_file_path, kill_flag_path, sqlite_path, duckdb_path, paper_sqlite_path, paper_fill_mode 等
- MonitoringDB (kabusys.monitoring.monitoring_db)
  - log_system_status, log_trade_event, upsert_position, log_risk_event, upsert_dashboard, get_dashboard
- SystemMonitor / TradeMonitor / RiskMonitor
  - check_once() が監視処理の単位（MonitoringEngine から呼ばれる）
- AlertManager
  - notify(message, level="INFO", category="") — LINE へのプッシュ通知（トークン未設定時はログのみ）
- OrderManager / Reconciler
  - 発注・状態同期・再起動後の復旧を担当

ライセンス・貢献
---------------
- 本 README はコードベースの説明を目的とした補助ドキュメントです。実運用前に必ずコードと設定を精査し、十分なテストを実施してください。
- 貢献やバグ報告は Pull Request / Issue を通じてお願いします。

付録：よく使うコマンド例
-----------------------
- Execution 起動（本番 or 開発設定は KABUSYS_ENV で切替）
  - KABUSYS_ENV=development python -m kabusys.run_execution
- Monitoring 起動（デフォルト 60 秒間隔、変更する場合は環境変数）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問題・質問があればコードの該当モジュール（例: monitoring/system_monitor.py、ai/news_nlp.py）を参照してください。README に記載の動作はコード内の docstring とコメントを元にまとめています。