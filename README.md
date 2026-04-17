KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視用ライブラリ群です。本リポジトリは
- 注文実行エンジン（ExecutionEngine）とその周辺（ブローカー抽象、オーダー管理、リコンシリエーション）
- 監視コンポーネント（System / Trade / Risk モニタ、アラート、Kill-Switch、監視DB）
- ポートフォリオ構成・ポジションサイズ計算（等配分・スコア加重・リスクベース）
- リサーチ用ファクター計算および特徴量探索（DuckDB を用いたファクター計算）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード など）

設計方針の要点:
- DuckDB / SQLite を用いたローカルデータ処理
- 環境変数（.env）での設定管理（Settings クラス）
- 本番 / paper_trading 環境の分離（paper_trading は専用 SQLite DB）
- API 呼び出しはフェイルセーフ設計（リトライやフォールバック）

主な機能一覧
--------------
- Execution:
  - 注文作成・送信・状態同期（OrderManager, ExecutionEngine）
  - 再起動時のリコンシリエーション（Reconciler）
  - RiskManager による発注制限（rate limit / max position など）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク・プロセス監視・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視およびダッシュボード更新
  - KillSwitch: しきい値を超えた場合の停止フラグ出力
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio:
  - 候補選択、重み計算（等分・スコア重み）
  - セクターキャップ、レジーム乗数、ポジションサイズ計算（単元株丸め・aggregate cap）
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI:
  - ニュースの LLM によるセンチメントスコアリング（ai_scores への書き込み）
  - 市場レジーム判定（ma200 + マクロニュースセンチメントの合成）
- ツール:
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ベースの監視ダッシュボード

セットアップ手順
----------------

1. Python 環境の準備
   - Python 3.9+ を推奨（使用しているライブラリに依存します）
   - 仮想環境を作成・有効化する:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存例（手動でインストールする場合）:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートの .env を準備
   - プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 代表的な環境変数（デフォルトを併記）:
     - KABUSYS_ENV=development|paper_trading|live (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時に必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信時)
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject (デフォルト: instant)
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  (SystemMonitor などポーリング間隔を上書き)
   - 簡易例 (.env):
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_password
     - JQUANTS_REFRESH_TOKEN=your_token

4. データディレクトリ
   - デフォルトで data/ 以下に SQLite / DuckDB / 各種フラグ・pid が作られます。適宜ディレクトリを作成してください:
     - mkdir -p data

使い方
------

起動スクリプト
- 監視ループを起動（SystemMonitor をポーリングして monitoring DB を更新）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 停止はプロジェクトルートの data/stop_requested.flag を作成すると次回ポーリング時に検知して終了します

- ExecutionEngine（注文送信・実行エンジン）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って paper_trading 用 DB に記録（data/paper_trading.db）
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します
  - 実行プロセスは data/execution.pid に pid を書きます。stale な pid を検出すると SystemMonitor が削除します

監視・ダッシュボード
- Streamlit ダッシュボード（監視データ可視化）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで DB を開きます（MonitoringEngine が稼働していることを想定）

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能（デフォルト: data/paper_trading.db）

AI 機能
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止 / 緊急停止
- KillSwitch（自動的に評価される条件を満たすと）:
  - data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを出します
  - kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch を手動でクリアするにはファイルを削除してください（KillSwitch.clear() が提供されます）
- 手動で監視ループやエンジンを止めるには data/stop_requested.flag を作成してください（run_* スクリプトで検知して安全終了します）

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主なモジュールを抜粋）

- __init__.py
  - パッケージメタ情報（__version__）

- config.py
  - 環境変数の読み込みと Settings クラス（.env 自動読み込み、各種デフォルト・検証）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 用分離含む）

- monitoring/
  - monitoring_db.py — SQLite を使った永続層（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py — CPU/MEM/DISK、プロセスファイル、データ鮮度チェック
  - trade_monitor.py — 注文滞留、約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の書き込み / 管理
  - alert_manager.py — LINE 通知用（Push）
  - monitoring_engine.py — 各 Monitor をまとめる実行エンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py — 注文作成・送信・同期ロジック
  - reconciler.py — 再起動時の照合処理
  - その他ブローカー抽象・リポジトリ等（オーダー永続化・API 抽象）

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・aggregate cap 処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py — ニュースの LLM スコアリング（OpenAI 利用）
  - regime_detector.py — ma200 + マクロセンチメントの合成で市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 使用）

運用上の注意 / トラブルシューティング
------------------------------------
- Settings.require の未設定（必須環境変数未設定）は ValueError を送出します。.env.example を参考に .env を作成してください。
- OpenAI を使う機能は OPENAI_API_KEY が必須です。未設定だと score_news / score_regime は ValueError を発生させます。
- psutil による優先度設定は権限が必要な場合があり、AccessDenied の場合は警告を出してスキップします。
- DuckDB/SQLite のファイルパスは Settings で指定可能です。paper_trading 環境では paper_trading 用の SQLite を使用して本番 DB と分離します。
- monitoring DB（SQLite）はマイグレーション処理を内蔵しており、起動時に必要なカラムを追加します。

拡張・開発メモ
----------------
- ファクター計算・リサーチ処理は DuckDB 上で完結する設計（外部 API に依存しない）。
- 将来的な拡張ポイント:
  - 銘柄ごとの lot_size マスタ対応（position_sizing の TODO）
  - Paper Trading のより詳細なシミュレーション（部分約定ロジックなど）
  - より詳細な監視ルールの追加（例: latency 分布監視）

ライセンス・連絡
----------------
- この README にはライセンス情報は含まれていません。ライセンス情報が別ファイルにある場合はそちらを参照してください。

以上が主要な使い方と構成の概要です。環境固有の設定や運用ポリシーに応じて .env を編集し、data/ 配下のファイル権限などを適切に管理して運用してください。必要であれば README をプロジェクト固有の手順に合わせて追記いたします。