KabuSys
======

日本株向けの自動売買システム（ライブラリ／実行コンポーネント群）の一部です。  
このリポジトリには実行エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

以下はこのコードベースをローカルで立ち上げたり、開発／検証するための README です。

概要
----
KabuSys は日本株自動売買に関する以下の責務を持つモジュール群を提供します。

- Execution Engine：ブローカーとやり取りして発注・状態管理を行う（run_execution.py）。
- Monitoring：システム状態、注文・約定の監視、リスク監視、アラート送信（run_monitoring.py、MonitoringEngine 等）。
- Portfolio Construction：候補選定、重み計算、ポジションサイズ計算（kabusys.portfolio）。
- Research：ファクター計算・特徴量評価（kabusys.research）。
- AI：ニュース記事の NLP スコアリング、マクロ判定による市場レジーム判定（kabusys.ai）。
- ツール：paper trading の検証レポート生成など（kabusys.tools）。

主な機能
--------
- 実行環境の切り替え（KABUSYS_ENV = development | paper_trading | live）
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と完全分離（data/paper_trading.db）。
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）
  - CPU/メモリ/Disk の監視、Execution プロセス存否の検出、データ鮮度確認。
  - 滞留注文（stale order）や約定価格の異常を検出し risk_logs に記録。
  - Kill Switch（条件到達時に data/kill.flag を生成）で ExecutionEngine を安全に停止可能。
- LINE によるアラート送信（AlertManager、クールダウン管理あり）
- ニュース記事の LLM ベースのセンチメントスコアリング（OpenAI を用いる）
  - スコアは ai_scores テーブルへ書き込み、部分失敗時のデータ保護を考慮した実装。
- ポートフォリオ生成ロジック（候補選定・重み計算・リスク調整・ポジションサイズ計算）
- DuckDB / SQLite を利用したデータ処理・ログ永続化
- Streamlit ベースの監視ダッシュボード（読み取り専用で実行可）

前提 / 依存
------------
- Python 3.10+
- 主な依存ライブラリ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- （実際のプロジェクトでは requirements.txt を用意してください）

セットアップ手順
----------------
1. リポジトリをクローン／取得し、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

2. 必要なパッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数（.env）を用意
   - プロジェクトルートに .env を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットできます。
   - 代表的な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (paper_trading 用, instant|partial|never|reject — デフォルト: instant)
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - DUCKDB_PATH（時系列価格等の分析 DB, デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

5. .env の記載方法
   - export KEY=VALUE / KEY="value" / KEY='value' などに対応。詳細は kabusys.config のパーサを参照してください。

使い方（実行例）
----------------

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依らず）。

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH に記録されます。
  - 起動時に data/execution.pid を書き、停止は data/stop_requested.flag や data/kill.flag 経由で行えます。

- Streamlit ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only モードで開き、ポートフォリオやリスクログ、最新システム状況を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

- AI 系処理（プログラム API）
  - ニュース NLP のスコア付け: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と日付を受け取り DB を更新します。OpenAI API キーが必要です（引数でも環境変数でも指定可能）。

プロセス制御 / フラグ
--------------------
- stop_requested.flag: run_monitoring.py / run_execution.py で監視される停止フラグ（data/stop_requested.flag 相当）。
  - このファイルが存在するとループは正常終了します（Graceful shutdown）。
- kill.flag: KillSwitch が書き込む停止フラグ（Settings.kill_flag_path、デフォルト data/kill.flag）。
  - KillSwitch はリスク条件（例: ドローダウン超過、ポジション数上限）を満たすとファイルを作成します。
- PID ファイル:
  - ExecutionEngine は data/execution.pid（Settings.pid_file_path）に PID を書きます。
  - SystemMonitor はこの PID を見てプロセス生存をチェックし、stale PID を検出したらファイルを削除しアラートを記録します。

設定（Settings）
----------------
- 自動 .env 読み込み:
  - プロジェクトルート（.git か pyproject.toml を基準）から .env を自動ロードします。
  - OS 環境変数が優先され、.env.local は .env を上書きします（ただし既存 OS 環境変数は保護される）。
- 主なプロパティ（Settings クラス）:
  - env / is_live / is_paper / is_dev
  - sqlite_path / paper_sqlite_path / duckdb_path
  - pid_file_path / kill_flag_path / kill_flag_clear_on_start
  - paper_fill_mode（instant|partial|never|reject）
  - cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- 必須項目は _require() により未設定時に例外を投げます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

注意事項 / 実装上のポイント
---------------------------
- paper_trading モードは本番 DB を触らないように設計されています。実運用で本番 DB を誤って上書きしないよう注意してください。
- Monitoring の初期化は init_monitoring_db() が DB スキーマ作成とマイグレーションを行います（冪等）。
- AI 呼び出し周りは retry/backoff、レスポンス検証、部分書き込みによる耐障害性を備えています。OpenAI API の使用には制限・課金が伴います。
- process_priority（utils/process_priority.py）でプロセス優先度を設定しますが、権限不足や OS 非対応時は警告を出してスキップします。
- DuckDB は時系列・分析用の DB として使用します。prices_daily / raw_financials / raw_news 等のテーブルを前提とした処理が多くあります。

ディレクトリ構成
----------------
主要ファイル／モジュールの概観（src/kabusys を起点）:

- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py  — ExecutionEngine 起動スクリプト（paper_trading は MockBroker 使用）
- config.py         — 環境変数・設定読み込みロジック（.env パーサ含む）
- __init__.py       — パッケージ定義、バージョン

- ai/
  - news_nlp.py        — raw_news を LLM でセンチメント評価し ai_scores へ書き込み
  - regime_detector.py — マクロ + MA200 で市場レジーム判定

- monitoring/
  - monitoring_db.py   — SQLite 用永続化層（system_status/trade_logs/positions/risk_logs/dashboard）
  - system_monitor.py  — CPU/メモリ/Disk / 実プロセス / データ鮮度監視
  - trade_monitor.py   — 注文滞留・約定異常監視
  - risk_monitor.py    — ドローダウン・ポジション上限監視
  - kill_switch.py     — kill.flag 管理
  - alert_manager.py   — LINE 通知（プッシュ）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- execution/
  - reconciler.py       — 起動時の注文照合・ポジション照合
  - order_manager.py    — 発注 API のラッパ（状態遷移管理）
  - order_repository.py — (実コードの一部が省略されているが) SQLite 上の注文永続化
  - （その他：broker_factory 等）

- portfolio/
  - portfolio_builder.py  — 候補選定・等配分・スコア配分
  - position_sizing.py    — 株数計算・単元丸め・資金スケーリング
  - risk_adjustment.py    — セクターキャップ、レジーム乗数

- research/
  - factor_research.py    — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC 計算、統計サマリー

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- utils/
  - process_priority.py — プロセス優先度・CPU affinity 管理ユーティリティ

- data/ （実行時に作られる想定ディレクトリ）
  - monitoring.db (SQLite の監視 DB のデフォルト)
  - paper_trading.db (paper_trading 用 DB のデフォルト)
  - kabusys.duckdb (分析用 DuckDB のデフォルト)
  - execution.pid, kill.flag, stop_requested.flag など

追加情報 / トラブルシュート
---------------------------
- .env の読み込みが動作しない／テストで自動ロードを避けたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- Monitoring が DB にアクセスできない場合は streamlit ダッシュボードが起動できません。MonitoringEngine を先に起動して DB を作成してください。
- OpenAI 呼び出しで 429 や一時的なネットワークエラーが発生しても内部でリトライを行うため、スクリプトが即死しない設計です。APIキーの設定漏れは ValueError を発生させます。

ライセンス・貢献
----------------
- この README ではライセンス情報を含めていません。実際のリポジトリでは LICENSE ファイルや CONTRIBUTING を用意してください。

----

何か特定の実行方法（例: Docker 化、systemd サービス化、CI テストの書き方）や、各モジュールの API ドキュメント（関数仕様・引数例・戻り値）を README に追加したい場合は、用途に合わせて追記できます。どの内容を追加したいか教えてください。