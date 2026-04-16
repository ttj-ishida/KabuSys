KabuSys — README
===============

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視ユーティリティ群をまとめた小規模なプロジェクトです。本コードベースは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）の起動支援・リコンシリエーション
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 向けの検証レポート生成ツール
- ファクター計算・特徴量探索（DuckDB を用いる研究用モジュール）
- ニュース NLP（OpenAI）を使った銘柄別センチメントスコア生成
- ポートフォリオ構築（候補抽出、重み算出、ポジションサイジング 等）
- Streamlit による監視ダッシュボード

主な設計方針として、実運用（live）・Paper Trading（paper_trading）を分離し、DuckDB/SQLite を使ったローカルデータ管理、外部 API 呼び出し（OpenAI、kabuステーション 等）は設定に応じて有効化／無効化します。

特徴一覧
--------
- Execution / Monitoring の独立した起動スクリプト（run_execution.py, run_monitoring.py）
  - run_execution は KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による安全停止
- 監視用 DB の自動初期化・マイグレーション（monitoring_db.init_monitoring_db）
- LINE による一方向アラート送信（AlertManager）
- Streamlit ダッシュボード（read-only 接続を想定）
- Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）
- OpenAI を使ったニュースセンチメント（ai.news_nlp.score_news）と市場レジーム判定（ai.regime_detector.score_regime）
- ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群（kabusys.portfolio）

セットアップ手順
----------------
1. リポジトリをクローンし、プロジェクトルートへ移動します。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なライブラリをインストール（代表的な依存）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
     pip install duckdb psutil requests openai streamlit

   ※ 実際のプロジェクトでは requirements.txt を用意している想定ですが、無ければ上記をインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須となる機能がある場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定でも動作するが通知は行われません）
     - PAPER_FILL_MODE: paper_trading の fill 動作（instant|partial|never|reject。デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視ログ用 DB、デフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用データベース）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（必要に応じて上書き可能）

   サンプル .env（プロジェクトルート）:
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     JQUANTS_REFRESH_TOKEN=...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     PAPER_FILL_MODE=instant

5. data ディレクトリ（DB・フラグファイル等）の作成（必要に応じて）
   - 多くのスクリプトはデフォルトで data/*.db を参照します。自動的にファイルが作られることもありますが、権限等に注意してください。

使い方（コマンド例）
-------------------

1) 監視ループを起動（Monitoring）
   - デフォルトは monitoring DB（settings.sqlite_path）を参照してログを記録します。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
   実行例:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   停止方法:
     - data/stop_requested.flag ファイルを作成するとループは検出して終了します。
     - または Ctrl+C（KeyboardInterrupt）で停止します。

2) 実行エンジン（ExecutionEngine）を起動
   - paper_trading モードにするとブローカーはモックになり、paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
   実行例（本番モード）:
     python -m kabusys.run_execution
   実行例（Paper Trading）:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   停止方法:
     - data/stop_requested.flag を作成するとエンジンへ停止指示を送れます。
     - 実行中は data/execution.pid に PID が書かれます（PID ファイルの stale 検出機構あり）。

3) Streamlit 監視ダッシュボード
   - 起動例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視エンジンが作成した monitoring DB を読み込み、概要・ポジション・注文・システム状態を表示します（read-only を想定）。

4) Paper Trading 検証レポート生成
   - コマンド:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。
   - 出力は標準出力へ。稼働率・注文成功率・レイテンシなどの指標を照会して PASS/FAIL を判定します。

5) ニュース NLP / レジームスコア（プログラムから呼び出す）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）。失敗時はフェイルセーフ（多くの場合 0.0 フォールバックやスキップ）します。

設定・挙動の注意点
-----------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動で読み込みます。OS 環境変数は上書きされません（.env.local は上書き可能）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、run_execution は production DB とは別の paper_trading 用 SQLite を使用します（PAPER_TRADING_SQLITE_PATH）。
  - PAPER_FILL_MODE によってモック約定の挙動を制御できます（instant, partial, never, reject）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を試みます。psutil の権限不足により設定できない場合は警告が出ますが続行します。
- Kill Switch / Stop Flag:
  - KillSwitch はリスク条件により data/kill.flag を書き込んで ExecutionEngine を停止させます（Execution 側は kill.flag を見て停止処理を行います）。
  - run_* スクリプトは data/stop_requested.flag を用いて手動停止を検出します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対して必要なカラム追加（簡易マイグレーション）を行います。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の解決、.env 自動ロードを含む
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）

サブパッケージ:
- ai/
  - news_nlp.py         — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py  — ETF MA とマクロニュースでレジーム判定して market_regime に書き込む
- monitoring/
  - monitoring_db.py     — SQLite テーブル定義・MonitoringDB ラッパー
  - system_monitor.py    — システム状態・データ鮮度監視
  - trade_monitor.py     — 注文滞留・約定異常監視
  - risk_monitor.py      — ドローダウン・ポジション上限監視
  - kill_switch.py       — kill.flag 書き込み処理
  - alert_manager.py     — LINE 通知クライアント
  - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - …（Engine / Broker 関連の実装が想定される）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — psutil を用いた優先度/affinity ユーティリティ

data/
- monitoring.db (デフォルト)
- paper_trading.db (paper_trading 用)
- kabusys.duckdb (DuckDB のデフォルトパス)
- execution.pid, kill.flag, stop_requested.flag などのフラグ/制御ファイル

開発・運用上の補足
------------------
- DuckDB 接続は分析向け（prices_daily, raw_financials など）に使われます。分析関数は DuckDB 接続を受け取り SQL + Python で完結する設計です。
- OpenAI を利用する機能（ニューススコア、レジーム判定）は API 呼び出しの失敗に対してリトライやフォールバックを実装していますが、API キーの漏洩・料金管理には注意してください。
- psutil によるプロセス制御や CPU affinity は OS に依存します。権限不足や非対応 OS の場合はログ警告が出て処理はスキップされます。
- 本リポジトリのファイルは設計ドキュメント（README 内コメント / docstrings）を豊富に含んでおり、各関数はユニットテストを作成しやすい純粋関数設計を心がけています。

問い合わせ・貢献
----------------
- バグ報告・機能改善は issue を立ててください。Pull Request は小さな単位で分けていただくとレビューしやすくなります。

以上が本プロジェクトの README 相当の概要です。必要であれば「環境変数の詳細一覧」「実行時のログ例」「開発時のユニットテストの書き方」などを追記できます。どの部分を詳しく書き足しましょうか？