# KabuSys

KabuSys は日本株自動売買のための軽量なオープンソース基盤ライブラリです。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視サブシステム（Monitoring）、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）などが含まれます。

以下はこのコードベースの README（日本語）です。

目次
- プロジェクト概要
- 主な機能
- 前提 / 依存関係
- セットアップ手順
- 環境変数（主要）
- 使い方（コマンド例）
- ファイル・ディレクトリ構成
- 運用上の注意点

プロジェクト概要
- 日本株の自動売買インフラ向けモジュール群。
- 実行エンジン（発注・注文管理・リスク制御）、監視（プロセス・注文・リスク）、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ニュース NLP / レジーム判定（OpenAI 利用）を提供。
- 実運用を想定した設計（PID ファイル / フラグファイルによる停止、監視 DB、LINE 通知、Paper Trading の分離など）。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントは本番 / paper_trading に応じて切替可能（paper_trading は MockBrokerClient を使用し、DB を分離）。
  - リコンシリエーション（Reconciler）による再起動後の同期処理。
  - リスク管理・オーダーマネージャ、注文リポジトリを組み合わせた発注フロー。
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU / メモリ / ディスク / プロセス）、データ鮮度、注文滞留、約定異常、ドローダウン等を定期チェック。
  - 監視結果は SQLite（monitoring.db）に永続化。
  - KillSwitch による停止フラグ（data/kill.flag）生成と ExecutionEngine 停止の仕組み。
  - LINE によるアラート送信（AlertManager）。
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）。
- Portfolio（銘柄選定・重み付け・株数決定）
  - 候補選定、等重率・スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ算出（単元株丸め・aggregate cap）。
- Research（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL ベース）。
  - 将来リターン計算、IC（情報係数）、統計サマリ。
- AI（ニュース NLU）
  - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ保存（score_news）。
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（score_regime）。
- 各種ユーティリティ
  - 環境設定管理（kabusys.config）：.env 自動読み込み（.env.local 上書き）、必須キー検証、Paper Trading 向けオプション等。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 利用）。

前提 / 依存関係
- Python 3.9+（typing の利用があるため 3.9 以上を想定）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを利用する場合）
  - その他（標準ライブラリ: sqlite3 等）
- SQLite（標準 Python に同梱）
- OpenAI API キー（AI 機能を使用する場合）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   - （実運用では requirements.txt を用意して pip install -r requirements.txt を推奨）

4. 環境変数の準備 (.env)
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要なキー（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

5. データディレクトリ
   - デフォルトでは data/ 配下に SQLite ファイルや PID / flag ファイルが作られます。必要に応じて data/ を作成してください（コード側で mkdir する箇所もありますが事前作成を推奨）。

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は ExecutionEngine が Mock ブローカーを使い、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用トークン・パスワード
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

使い方（実行例）
- ExecutionEngine 起動
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 説明:
    - 起動時に PID ファイル（data/execution.pid）を作成し、停止は data/stop_requested.flag（停止フラグ）か kill.flag により行われます。
    - paper_trading 環境ではデータ・発注は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

- Monitoring 起動
  - 実行:
    - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 説明:
    - 監視は常に（KABUSYS_ENV に関係なく）本番の sqlite_path を参照して監視ログを残します。
    - MONITOR_POLL_INTERVAL によりポーリング間隔を秒で指定可能（1 秒以上推奨）。不正値はデフォルト（60）にフォールバック。

- Streamlit ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 読み取り専用で monitoring.db を開いてダッシュボードを表示します。MonitoringEngine がデータを書き込んでいることが前提です。

- Paper Trading 検証レポート生成
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション --db で DB パスを指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db）
  - 概要:
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を表示します。

- AI/レジーム関連（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols から記事を集約して OpenAI に送り、ai_scores に書き込みます。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF (1321) の MA200 とマクロニュースを合成して market_regime テーブルへ書き込みます。
  - 注意: どちらも OpenAI API キーを必要とし、DuckDB 接続を受け取ります。

運用上のフラグ / PID
- data/execution.pid: ExecutionEngine の PID ファイル（起動時に作成）
- data/stop_requested.flag: 外部からの「停止要求」フラグ（run_execution / run_monitoring が検知）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に対して停止シグナルを送るための永続フラグ）
- Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag をクリアするオプションあり

ディレクトリ構成（主要ファイルのみ）
- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数・.env 読み込みと Settings 定義
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - ai/
      - news_nlp.py                 — ニュースセンチメント算出（OpenAI）
      - regime_detector.py          — 市場レジーム判定（MA200 + マクロセンチメント）
    - monitoring/
      - monitoring_db.py            — SQLite 監視 DB の初期化／読み書き層
      - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度/プロセス監視
      - trade_monitor.py            — 注文滞留・約定異常検出
      - risk_monitor.py             — ドローダウン・ポジション上限監視
      - kill_switch.py              — kill.flag 書き込みロジック
      - alert_manager.py            — LINE 通知ユーティリティ
      - monitoring_engine.py        — 各 Monitor を束ねるエンジン
      - streamlit_dashboard.py      — Streamlit ダッシュボード
    - execution/
      - reconciler.py               — 起動時の自動復旧・突合せ
      - order_manager.py            — 発注ステートマシンの外向け API
      - order_repository.py         — Orders DB アクセス（別ファイル想定）
      - ...                         — ブローカー・注文関連実装
    - portfolio/
      - portfolio_builder.py        — 候補選定・重み付け
      - position_sizing.py          — 株数決定・スケーリング
      - risk_adjustment.py          — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py          — Momentum/Value/Volatility 等の計算（DuckDB）
      - feature_exploration.py      — 将来リターン・IC・統計サマリ
    - utils/
      - process_priority.py         — プロセス優先度 / CPU affinity 設定
    - data/                          — 実行時に生成されるデータ（DB / pid / flag 等）

開発上の注意点 / FAQ
- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local（上書き） > .env（未設定キーのみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとこの自動読み込みを無効化できます（テスト等で便利）。
- Paper Trading と本番の DB は分離:
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path が使用され、本番の監視 DB（sqlite_path）とは別に運用できます。
- OpenAI 利用:
  - AI 関連処理は API 呼び出し時に一部リトライ・バックオフやレスポンス検証を実装していますが、API キーの管理・利用量には注意してください。
- 権限関連:
  - psutil による nice や cpu_affinity の設定は権限不足で失敗することがあります（警告ログでスキップ）。

以上がこのコードベースの簡易 README です。  
追加で欲しい情報（例: requirements.txt の候補、サンプル .env.example、各コンポーネントの起動シーケンス図など）があればお知らせください。