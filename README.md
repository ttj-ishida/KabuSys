# KabuSys

KabuSys は日本株の自動売買プラットフォーム用のコンポーネント群です。戦略のポートフォリオ構築、ポジションサイズ計算、発注エンジンの補助、監視（モニタリング）や運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）、およびニュース NLP / レジーム判定などの機能を含みます。

このリポジトリはライブラリ的にモジュールを提供しつつ、コマンドライン/デーモン的に起動するスクリプト群（監視ループ、ExecutionEngine 起動など）を備えています。

主な特徴
- ポートフォリオ構築（候補選定、等配分／スコア加重、リスク調整、ポジションサイズ計算）
- 発注管理（OrderManager、Reconciler：再起動時の同期処理）
- 監視（System / Trade / Risk Monitor）、アラート送信（LINE）
- Kill Switch：閾値超過時に ExecutionEngine 停止フラグを生成
- Paper Trading モード（本番 DB と分離された専用 SQLite）
- AI モジュール：ニュースを LLM（OpenAI）でスコアリング、マクロセンチメントから市場レジーム判定
- 運用支援ツール：Paper Trading 検証レポート、Streamlit ダッシュボード
- DuckDB を用いたリサーチ（各種ファクター、将来リターン、IC 計算）

サポート Python バージョン
- Python 3.10 以上（PEP 604 の型記法などを使用）

必要な外部ライブラリ（最小限）
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボード利用時)
- その他標準ライブラリ（sqlite3 等）

pip 例:
pip install duckdb psutil openai requests streamlit

--- 

目次
- 機能一覧
- セットアップ
- 実行方法（使い方）
- 環境変数 / 設定
- ディレクトリ構成（主要ファイルの説明）
- 運用ノート / 注意点

機能一覧
- portfolio: 銘柄選定、等配分/スコア配分、リスク調整（セクターキャップ、レジーム乗数）、株数計算（lot 単位丸め、集約キャップ）
- execution: OrderManager、OrderRepository、Reconciler（再起動時の同期）、ExecutionEngine（エンジン本体は別モジュール）
- monitoring:
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス生存、株価データ鮮度の監視
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - AlertManager: LINE push 通知 (クールダウン管理)
  - KillSwitch: フラグファイルにより ExecutionEngine 停止シグナル発行
  - MonitoringDB: SQLite ベースの監視ログ永続化とマイグレーション処理
  - Streamlit ダッシュボード（監視情報確認）
- ai:
  - news_nlp: raw_news を LLM （OpenAI）に投げて銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - regime_detector: ma200 乖離 + マクロニュース LLM を合成して市場レジームを daily で判定し market_regime に書き込み
- research: DuckDB を用いたファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリ
- tools:
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順（ローカル開発 / 運用向け）
1. リポジトリをクローンして Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. .env ファイルを用意（プロジェクトルートに配置）
   - このライブラリは起動時に自動で .env / .env.local を読み込みます（OS 環境 > .env.local > .env の優先順位）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 例: .env（必要な主なキー）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

4. データディレクトリの準備
   - data/ フォルダを作成（PID やフラグファイル、DB をここに置く想定）
     - mkdir -p data
   - 初期 DB はスクリプト起動時に作成されます（monitoring の初期化でテーブル作成・マイグレーションを行います）。

基本的な使い方（実行例）

1) 監視ループを起動（run_monitoring.py）
- 目的: SystemMonitor を定期ポーリングして monitoring DB を更新
- 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - KABUSYS_ENV は監視側は環境に関わらず本番 sqlite_path を利用する仕様
- 起動:
  - python -m kabusys.run_monitoring
  - または python src/kabusys/run_monitoring.py
- 停止:
  - data/stop_requested.flag を作成するとループは検知して終了します（または Ctrl+C）

2) ExecutionEngine を起動（run_execution.py）
- 目的: 発注エンジンの起動（紙取引モードあり）
- KABUSYS_ENV による挙動:
  - paper_trading の場合は MockBrokerClient を使用し、データは settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録される（本番 DB と完全分離）
- 起動:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると実行中のエンジンに停止シグナルを送り安全に停止します
- PID / Stop flag:
  - 実行中は data/execution.pid にプロセス PID を書き込む (PID ファイルは SystemMonitor が stale を検知して削除します)

3) Streamlit ダッシュボード（監視情報の可視化）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- オプション:
  - --db で監視 DB のパス指定（デフォルト data/monitoring.db）
- 読み取り専用で DB を開きます（存在しない場合は MonitoringEngine を先に起動する必要があります）

4) Paper Trading 検証レポート生成ツール
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD : レポート開始日
    - --to YYYY-MM-DD   : レポート終了日
    - --db PATH         : SQLite DB ファイルパス（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）
- 出力: 標準出力に検証レポート（稼働率、注文成功率、レイテンシ等）を表示

5) AI モジュール利用（ニューススコアリング / レジーム判定）
- 両モジュールは OpenAI API キーを要求します（引数に渡すか環境変数 OPENAI_API_KEY を設定）
- 例（インタプリタ内）:
  - from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect(...)
  - from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

設定関連（Settings）
- Settings クラスがアプリ設定をラップしています。主なプロパティ:
  - env: KABUSYS_ENV (development, paper_trading, live)
  - duckdb_path: DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - sqlite_path: SQLITE_PATH (default data/monitoring.db)
  - paper_sqlite_path: PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - paper_fill_mode: PAPER_FILL_MODE (instant|partial|never|reject)
  - pid_file_path, kill_flag_path 等
  - CPU/MEM/DISK 閾値など（監視用）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env と .env.local を読み込みます
- OS 環境変数が優先され、.env.local は .env を上書きします（ただし OS 環境変数保護あり）
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

監視 / Kill Switch / フラグ
- stop_requested.flag: run_monitoring.py / run_execution.py が外部停止要求を検知するためのファイル（data/stop_requested.flag）
- kill.flag: KillSwitch が作成するフラグ（ExecutionEngine に停止指示を出すための仕組み）。KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を使用
- PID ファイル: data/execution.pid（ExecutionEngine の PID。SystemMonitor が stale を検出して削除する場合があります）

データベースとマイグレーション
- monitoring_db.init_monitoring_db(conn) によりテーブルとインデックスを冪等に作成します
- 既存 DB に対する簡単なマイグレーション（dashboard.peak_value 列や trade_logs.latency_ms 列の追加）を行います

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py               — パッケージ定義（バージョン等）
  - config.py                 — 環境変数 / Settings
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 層（テーブル作成・MonitoringDB クラス）
    - system_monitor.py       — CPU/メモリ/ディスク・プロセス・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - monitoring_engine.py    — 監視モジュールの統合とポーリングループ
    - alert_manager.py        — LINE 通知
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — 発注ロジック（OrderManager）
    - reconciler.py           — リコンシリエーション（再起動時の同期）
    - ... (その他発注関連モジュール)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・集約キャップ処理
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Value / Volatility 等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py      — マクロ + ma200 を使い日次レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI

運用ノート / 注意点
- Paper Trading: KABUSYS_ENV=paper_trading 時は本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH を使用します。Paper Trading 用の挙動（fill_mode 等）は Settings.paper_fill_mode で制御します。
- OpenAI API: API キーが必要です。失敗時は適宜フェイルセーフ（ゼロスコア等）で継続する実装が多いですが、API キー未設定時は例外を投げる関数もあります。
- プロセス優先度: run_* スクリプトは起動時にプロセス優先度を "high" にセットしようとします（psutil を使用）。権限や OS により失敗する可能性があり、その場合はログに警告が出ます。
- 自動 .env ロードはプロジェクトルートが特定できる場合のみ行われます（.git または pyproject.toml を探索）。
- DuckDB / sqlite 接続はファイルパスを Settings で指定できます。運用時は適切な永続場所（例: /var/lib/kabusys/data）へ配置してください。
- ログレベルは LOG_LEVEL 環境変数で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

サンプル起動例（まとめ）
- 監視をデフォルト間隔で起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ExecutionEngine を paper_trading モードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボードを起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
- この README はコードベースの説明を目的としています。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

問い合わせ
- 問題報告や改善提案は GitHub の Issue をご利用ください。ソースコード内の docstring やログは設計上の意図や注意点を多く含んでいますので、実装を変更する際はそちらも参照してください。

以上。必要であれば、利用例や more detailed な開発者向けドキュメント（API レベルの使用例、テストの書き方、データベーススキーマの詳細など）も追記します。どの部分を詳しく書くか指示してください。