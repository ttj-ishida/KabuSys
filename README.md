README — KabuSys
================================================================================

概要
----
KabuSys は日本株向けの自動売買 / モニタリング基盤のプロジェクトです。
主要コンポーネントは以下の通りです。

- ExecutionEngine: シグナルに基づく発注・注文状態管理・リスク制御
- MonitoringEngine: システム状態・注文滞留・リスク監視・アラート送信
- Portfolio モジュール: 候補選定・重み付け・ポジションサイズ算出
- Research モジュール: ファクター計算・特徴量探索・IC 計算
- AI モジュール: ニュースを用いたセンチメント評価、レジーム判定（OpenAI を利用）
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボード等

この README はソースツリー（src/kabusys 配下）に基づいて使い方やセットアップ手順をまとめたものです。

機能一覧
--------
大まかな機能（抜粋）:

- 実行系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの切替（本番 / paper_trading）
  - リコンシリエーション（再起動時の注文・ポジション突合せ）
  - リスク管理（ポジション上限、ドローダウン等）

- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine
  - 監視結果を SQLite に永続化（monitoring_db）
  - LINE によるプッシュ通知（AlertManager）
  - kill.flag による ExecutionEngine の強制停止機構（KillSwitch）
  - streamlit ベースの監視ダッシュボード

- ポートフォリオ構築（純粋関数）
  - 候補選定（スコア／ランク）
  - 等ウェイト / スコア重み / リスクベース 配分
  - セクター上限適用、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily, raw_financials を使用）
  - 将来リターン計算、IC（Spearman）や統計サマリー

- AI（OpenAI）
  - ニュースを LLM でスコア化して ai_scores に書込
  - マクロニュース + MA200 で市場レジーム判定（score_regime）

- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: 監視 DB を可視化

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境の作成:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 依存パッケージをインストール
   pip install -r requirements.txt
   ※ requirements.txt が無い場合は最低限以下が必要になります:
     - duckdb
     - psutil
     - requests
     - streamlit (ダッシュボード利用時)
     - openai (AI 機能利用時)

3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 主要な環境変数（一部、デフォルト値も記載）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（設定必須な場合あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード（設定必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定でも動作するが通知はスキップされる）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定モード、デフォルト instant）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings で扱われます）

   例 (.env):
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

4. データディレクトリ
   - data/ 以下に sqlite / duckdb 等の DB ファイルや pid/flag ファイルが作られます。
   - 事前に data/ を作成しておくと権限周りで安全です:
     mkdir -p data

5. DB 初期化
   - 監視テーブルは起動時に自動で作成されます（init_monitoring_db）。
   - DuckDB のスキーマ（prices_daily, raw_financials など）は別途データ投入が必要です（本 repository には価格データロード担当の pipeline が含まれている想定）。

使い方
------
1. ExecutionEngine の起動
   - 実行スクリプト: src/kabusys/run_execution.py
   - 実行例:
     KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
     または
     python src/kabusys/run_execution.py  # KABUSYS_ENV が .env で設定されていればそれを使う

   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB と切り離されます。
     - 起動時に data/execution.pid に PID が書かれます。
     - data/stop_requested.flag が存在する場合は起動しません。起動中にフラグが作成されると安全停止します。

2. MonitoringEngine の起動
   - 実行スクリプト: src/kabusys/run_monitoring.py
   - 実行例:
     MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py

   - 補足:
     - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
     - 監視は Settings.env に関係なく本番の sqlite_path を使って監視ログを保存します（監視は本番 DB を参照する運用を意図）。
     - 停止フラグ data/stop_requested.flag を検知するとループを終了します。

3. Streamlit ダッシュボード
   - 起動スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
   - 実行例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

   - 補足:
     - 読み取り専用で監視 DB を開きます（?mode=ro）。MonitoringEngine が書き込み中でも問題なく表示できるように設計されています。

4. Paper Trading 検証レポート
   - スクリプト: src/kabusys/tools/paper_verification_report.py
   - 実行例:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

   - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などを標準出力に印字します。

5. AI 機能（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（raw_news, news_symbols, ai_scores テーブル）を渡して指定日分のニュースをスコアリングし ai_scores を更新します。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - prices_daily と raw_news を使って市場レジームを判定し market_regime テーブルに保存します。
   - 注意: OpenAI API を利用するため、OPENAI_API_KEY が必要です（引数で渡すことも可能）。

6. kill.flag / stop フラグ
   - ExecutionEngine を停止させたいときは data/kill.flag を書き込む（KillSwitch 経由の自動生成や手動作成で停止シグナルを送る）。
   - Monitoring / Execution は stop_requested.flag（data/stop_requested.flag）や execution.pid などで起動・停止・状態検査を行います。

主要設定（Settings）
-------------------
src/kabusys/config.py の Settings クラスで扱われる主な設定:

- jquants_refresh_token: J-Quants API
- kabu_api_password / kabu_api_base_url: kabuステーション API
- line_channel_access_token / line_user_id: LINE 通知
- duckdb_path（デフォルト data/kabusys.duckdb）
- sqlite_path（デフォルト data/monitoring.db）
- paper_sqlite_path（デフォルト data/paper_trading.db）
- paper_fill_mode（instant|partial|never|reject）
- pid_file_path / kill_flag_path / KILL_FLAG_CLEAR_ON_START
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- env / is_live / is_paper / is_dev

ディレクトリ構成
----------------
主要ファイル・パッケージ（抜粋）:

- src/kabusys/
  - __init__.py                 — パッケージ定義（バージョン等）
  - config.py                   — 環境変数 / Settings
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - execution/
    - execution_engine.py       — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py          — Order 管理の外向き API
    - order_repository.py       — Orders DB アクセス層（SQLite）
    - reconciler.py             — 起動時の自動リコンシリエーション
    - broker_factory.py / broker_api.py — ブローカ API 抽象と実装
  - monitoring/
    - monitoring_db.py          — 監視用 SQLite テーブル定義 + DB 操作ラッパ
    - system_monitor.py         — システム・データ鮮度監視
    - trade_monitor.py          — 注文滞留・約定異常検知
    - risk_monitor.py           — ドローダウン・ポジション上限検知
    - kill_switch.py            — kill.flag 管理
    - alert_manager.py          — LINE 通知
    - monitoring_engine.py      — 3 つの Monitor をまとめるループ
    - streamlit_dashboard.py    — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定・制約処理
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — Momentum/Volatility/Value ファクター
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — マクロ + MA200 でレジーム判定
  - utils/
    - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
------------
- Monitoring は監視データを永続化します。データファイル（data/*.db）はバックアップや保護を考慮してください。
- OpenAI 呼び出しは課金発生・レート制限の影響を受けます。API キーは安全に管理してください。
- psutil を用いたプロセス優先度の設定は権限に依存します（設定に失敗した場合は警告ログでスキップします）。
- Paper Trading を利用する際は PAPER_TRADING_SQLITE_PATH を確認してください（本番 DB と分離してください）。
- .env の自動ロード順は OS 環境 > .env.local > .env（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

よくある操作コマンド例
--------------------
- Monitoring をバックグラウンドで起動（UNIX 例）:
  MONITOR_POLL_INTERVAL=60 nohup python src/kabusys/run_monitoring.py > logs/monitor.log 2>&1 &

- ExecutionEngine を paper_trading で実行:
  KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py

- Paper 検証レポート（期間指定）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

サポート / 貢献
---------------
- バグ報告や改善提案は Issues を立ててください。
- 大きな機能追加は事前に Issue で相談してください。

ライセンス
----------
- このリポジトリにライセンス表記がある場合はそれに従ってください（ここでは省略）。

以上。プロジェクト内の各モジュールには docstring とコメントが豊富に書かれているため、実装の詳細や API の使い方は該当ファイルを参照してください。必要であれば README を拡張して具体的なデプロイ/運用手順や CI 設定、DB スキーマ定義を追加できます。