README
======

本ドキュメントは、KabuSys コードベース（自動売買・監視・リサーチツール群）の概要と使い方を日本語でまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムおよびその周辺ツール群です。主な機能は以下の通りです。

- ExecutionEngine：ブローカー経由の発注・注文管理（本番 / ペーパートレード対応）
- Monitoring：システム状態・データ鮮度・注文滞留・リスク監視、LINE 通知、kill flag によるエンジン停止
- Portfolio construction：候補選定、ウェイト計算、ポジションサイズ計算、セクター制約
- Research：DuckDB 上でのファクター計算（Momentum / Volatility / Value）や特徴量解析
- AI モジュール：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボードなど
- DB：監視ログ・トレードログ等は SQLite（monitoring DB）、時系列解析は DuckDB を利用

主な設計方針
- 本プロジェクト内の多くのモジュールは外部 API に直接影響を与えない（研究・検証コードは副作用なし）。
- Paper Trading は本番データベースと完全分離（data/paper_trading.db を使用）。
- OpenAI 呼び出し等はリトライ・フォールバックを備えフェイルセーフに動作。

機能一覧
--------
- 実行系
  - ExecutionEngine の起動 / 停止（run_execution.py）
  - ブローカー抽象化（実ブローカー / MockBroker）
  - リコンシリエーション（再起動後の注文・ポジション照合）
- 監視系
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs への記録
  - MonitoringEngine：各監視を束ねてポーリング、KillSwitch 評価、AlertManager 通知
  - AlertManager：LINE による一方向通知（クールダウン管理）
  - streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等重・スコア重み化（calc_equal_weights / calc_score_weights）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュースセンチメントスコアリング（OpenAI API 経由、ai_scores に格納）
  - マクロニュースと ETF MA による市場レジーム判定（score_regime）
- ツール
  - paper_verification_report.py：Paper Trading DB から検証レポートを生成
  - 各種 DB 初期化（monitoring_db.init_monitoring_db）

セットアップ手順
----------------

前提
- Python 3.9+（コードは typing | union 型等を使用）
- DuckDB、psutil、requests、streamlit、openai など外部パッケージが必要

1. レポジトリを取得
   - git clone ...（省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt があればそれを使用してください）

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数設定（.env）
   - プロジェクトルートの .env または .env.local に環境変数を記述できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

重要な環境変数（主要）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト development
  - paper_trading の場合、run_execution は paper_trading 用 DB と MockBroker を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須となる箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使用する機能用 API キー
- PAPER_FILL_MODE: paper trading の約定挙動（instant | partial | never | reject） デフォルト "instant"
- PAPER_TRADING_SQLITE_PATH: paper trading DB パス（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: 実行エンジン PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 (.env)
- KABUSYS_ENV=paper_trading
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- JQUANTS_REFRESH_TOKEN=...
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- MONITOR_POLL_INTERVAL=60
- LOG_LEVEL=INFO

使い方（コマンド例）
-------------------

1) 監視ループ（SystemMonitor 単体）
- モジュール経由で実行：
  - python -m kabusys.run_monitoring
- 補足:
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します
  - 停止は Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成

2) 実行エンジン（ExecutionEngine）
- 本番 / ペーパートレード共通起動:
  - python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading DB に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に data/stop_requested.flag が作成されると安全に停止を試みます
  - ExecutionEngine の PID は data/execution.pid に書き込まれます

3) Streamlit 監視ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 補足:
  - DB は読み取り専用で開かれる（URI に ?mode=ro を付与）
  - MonitoringEngine が書き込んでいる監視 DB を可視化します

4) Paper Trading 検証レポート
- 単体実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH   （省略時: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

5) AI / レジーム判定（プログラムから利用）
- ニューススコアリング:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

注意事項
- OpenAI API を使用する機能は API キーが必須。未設定の場合は ValueError を送出する箇所があります。
- psutil を用いたプロセス優先度設定は管理者権限が必要な場合があります。失敗時はログ出力でスキップされます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 停止・強制停止用フラグファイル:
  - data/stop_requested.flag : run_monitoring / run_execution が確認する「即座に終了する」フラグ
  - data/kill.flag : KillSwitch（リスク閾値超過時）による ExecutionEngine 強制停止指示

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要なモジュール構成（抜粋）です：

- kabusys/
  - __init__.py
  - config.py                      # 環境変数読み込み / Settings
  - run_monitoring.py              # SystemMonitor ポーリング起動スクリプト
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  # Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py             # monitoring DB (SQLite) 初期化 / API
    - system_monitor.py            # CPU/メモリ/ディスク/プロセス/データ鮮度
    - trade_monitor.py             # 注文滞留 / 約定異常監視
    - risk_monitor.py              # ドローダウン / ポジション上限監視
    - kill_switch.py               # kill.flag 書き込みユーティリティ
    - alert_manager.py             # LINE push 通知
    - monitoring_engine.py         # 監視を束ねるエンジン
    - streamlit_dashboard.py       # Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py          # （実装ファイルは一部省略）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
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
    - news_nlp.py                  # ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py           # マクロ + MA によるレジーム判定
  - data/                           # 実行時に使用する DB / flag / pid 等（プロジェクトルート）
    - monitoring.db (default)
    - paper_trading.db (paper mode)
    - kabusys.duckdb (default)
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - utils/
    - process_priority.py          # プロセス優先度 / CPU affinity 設定
  - research/                       # ファクター計算 / 統計ユーティリティ

開発・運用上のヒント
-------------------
- DB スキーマ変更は monitoring_db.init_monitoring_db が冪等に実行されるよう設計されています。run_execution / run_monitoring 起動時に自動でテーブル作成・マイグレーションを行います。
- Paper Trading 検証は tools/paper_verification_report.py を使うと簡単に主要指標（稼働率、成功率、レイテンシ等）を算出できます。
- AlertManager は LINE API の Channel Access Token と User ID を設定していない場合は送信をスキップします。ローカル開発ではテスト用にトークンを空にしておくとよいです。
- KillSwitch は RiskMonitor の結果に基づいて kill.flag を生成します。ExecutionEngine はこのファイルを検知して安全停止します。

トラブルシューティング
----------------------
- OpenAI 関連: API キー未設定の場合はエラーになります。テスト時はモック（unittest.mock.patch）で API 呼び出し部分を置き換え可能です。
- psutil の優先度設定に関する AccessDenied は権限の問題です（Linux では root、Windows では管理者権限が必要）。
- Streamlit で DB を読み込めない場合: monitoring DB が存在しない・パーミッション不足。まず run_monitoring を起動して DB が生成されているか確認してください。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

以上。必要に応じて README を拡張しますので、追加で記載してほしい情報（依存パッケージ一覧、具体的な起動スクリプトの引数、運用手順など）があれば教えてください。