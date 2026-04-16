KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。本リポジトリは以下の主要機能を提供します。

- 注文作成・発注・再突合（ExecutionEngine / OrderManager / Reconciler）
- 実取引と Paper Trading の分離運用（paper_trading 環境）
- 監視（System / Trade / Risk）とアラート（LINE Push）
- 監視ダッシュボード（Streamlit）
- Paper Trading の検証レポート生成ツール
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ）
- ファクター計算・リサーチユーティリティ（DuckDB 経由）
- ニュースの NLP 評価・市場レジーム判定（OpenAI を利用）

設計方針のポイント
- DB: SQLite（監視用 / Paper Trading 用）と DuckDB（時系列・ファクタ計算用）を併用
- 本番と Paper Trading を明確に分離（KABUSYS_ENV による挙動切替）
- LLM 呼び出しはフェイルセーフ（API 失敗時は代替値で継続）
- 自動ロードされる .env（プロジェクトルートに .env / .env.local があれば読み込む。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

主な機能一覧
----------------
- 実行系
  - run_execution.py: ExecutionEngine を起動して発注ループを実行（paper_trading 環境では MockBrokerClient を利用）
  - Broker クライアントの切り替え（本番 / モック）
  - Reconciler による起動時の自動復旧・状態同期

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒）
  - MonitoringEngine: System / Trade / Risk 各 Monitor を束ねる
  - SystemMonitor: CPU / メモリ / ディスク / PID ファイル / データ鮮度 の監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション数上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）

- ダッシュボード / レポート
  - streamlit_dashboard.py: Streamlit を使った監視ダッシュボード（read-only）
  - tools/paper_verification_report.py: Paper Trading の運用検証レポート生成（稼働率、注文成功率、レイテンシ等）

- リサーチ / AI
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - research.feature_exploration: 将来リターン計算・IC（Information Coefficient）等
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に格納
  - ai.regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを組み合わせて市場レジーム判定

セットアップ手順
----------------
1. Python 環境（推奨: 3.9+）を用意し、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なライブラリをインストールします（プロジェクトに requirements.txt が無い場合は手動で）。
   - 主な依存例:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

3. ソースを Python のパスに通す
   - 開発時はリポジトリルートで以下のようにして実行できます:
     - export PYTHONPATH=./src  (Windows: set PYTHONPATH=.\src)
   - あるいはパッケージとしてインストール（setup 配備があれば）:
     - pip install -e .

4. 環境変数の準備 (.env)
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は .env を上書き）。
   - 必須変数（利用する機能により異なります）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合)
   - 設定例（.env）:
     - KABUSYS_ENV=development
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...

5. データディレクトリ
   - デフォルトの DB /フラグ 等は data/ 以下を想定しています。必要に応じて作成してください。
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - data/execution.pid, data/kill.flag, data/stop_requested.flag は実行時に作成/削除されます。

使い方（主要コマンド）
---------------------

1) 監視ループを起動
- デフォルトポーリング間隔は 60 秒。環境変数で上書き可能:
  - export MONITOR_POLL_INTERVAL=30
- モジュール実行例（開発環境）:
  - PYTHONPATH=./src python -m kabusys.run_monitoring
- 注意:
  - run_monitoring は KABUSYS_ENV にかかわらず monitoring 用の sqlite_path（settings.sqlite_path）を使用します。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

2) ExecutionEngine を起動（発注ループ）
- 実行:
  - PYTHONPATH=./src python -m kabusys.run_execution
- Paper Trading:
  - KABUSYS_ENV=paper_trading に設定すると、MockBrokerClient を使い data/paper_trading.db に記録され、本番データベースとは分離されます。
  - PAPER_FILL_MODE（instant | partial | never | reject）で約定挙動を変更できます（デフォルト: instant）。
- 停止:
  - data/stop_requested.flag を作成すると Engine に停止シグナルが渡されます。
  - KillSwitch がトリガーすると data/kill.flag に理由を書き込みます（ExecutionEngine 起動時にクリア動作を設定可能）。

3) Streamlit ダッシュボード（監視）
- 起動コマンド例（読み取り専用モード）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは monitoring DB を read-only で参照し、ポートフォリオダッシュ、ポジション、最近の注文、システム状態、リスクログなどを表示します。

4) Paper Trading 検証レポート生成
- 単発実行:
  - PYTHONPATH=./src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- デフォルト DB は data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH を使って変更可能。
- 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定。

5) AI 関連
- ニュースの NLP スコア算出（ai.news_nlp.score_news）や市場レジーム判定（ai.regime_detector.score_regime）は OpenAI API を利用します。
- 必須: OPENAI_API_KEY を設定（関数呼び出し時に引数で渡すことも可能）。
- モデル: gpt-4o-mini を想定（設定はモジュール内定義）。

設定（主要な Settings）
---------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQL/DB:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- Process / PID:
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag を削除
- Paper Trading:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- 監視パラメータ（例）:
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- ログレベル:
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py                 — パッケージ定義・バージョン
  - config.py                   — Settings / .env 自動ロードロジック
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py          — SQLite のテーブル初期化と永続化 API
    - system_monitor.py         — システム・データ鮮度監視
    - trade_monitor.py          — 注文滞留・約定異常監視
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — data/kill.flag 操作ユーティリティ
    - monitoring_engine.py      — 各モニタを束ねるエンジン
    - alert_manager.py          — LINE プッシュ通知
    - streamlit_dashboard.py    — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py          — 注文フローの外向き API
    - reconciler.py             — 起動時リコンシリエーション
    - ...                       — Broker / OrderRepository 等（未列挙のファイルあり）
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定・スケールダウンロジック
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — ファクター計算（DuckDB）
    - feature_exploration.py    — 将来リターン・IC 等
  - ai/
    - news_nlp.py               — ニュースを LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py        — 市場レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (運用時に生成される）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag

開発上の注意 / トラブルシューティング
------------------------------------
- .env 自動読み込み:
  - config._find_project_root() は __file__ を基準に親ディレクトリを探索してプロジェクトルートを決定します。CWD に依存せずパッケージ配布後も動作するよう設計されています。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブル/インデックスを作成し、一部のカラム追加 (例: latency_ms, peak_value) を既存 DB に対して行います。

- AI 呼び出し:
  - OpenAI API のエラー（429, タイムアウト, 5xx）はエクスポネンシャルバックオフでリトライします。その他の失敗はフェイルセーフ（スコア=0 など）で継続します。

- 実行優先度:
  - run_* スクリプト起動時に set_process_priority("high") を呼び出しています。実行環境によっては権限不足で失敗することがありますが、その場合は警告ログを出してスキップします。

ライセンス / 貢献
-----------------
本 README はソースコードのドキュメントから生成した概要です。実際のライセンスや貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING 等のファイルを参照してください（存在する場合）。

お問い合わせ
------------
実行時や設定に関する質問があれば、実行ログと使用した環境変数（機密情報は伏せる）を添えて問い合わせてください。