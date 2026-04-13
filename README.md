KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム「KabuSys」のコアライブラリ群です。
戦略のポートフォリオ構築、ポジションサイジング、実行エンジン（発注／リコンシリエーション）、
監視（モニタリング）、リサーチ（ファクター計算）および AI（ニュース NLP / レジーム判定）
周りの実装を含みます。

主な特徴
--------
- ポートフォリオ構築
  - シグナルの上位選定、等金額・スコア加重配分、リスクベース配分
- ポジションサイジング
  - 単元（lot）丸め、投下資金スケール、コストバッファ/集約キャップ
- リスク調整
  - セクター集中上限、マーケットレジームに応じた乗数
- 実行関連
  - OrderManager / OrderRepository / Reconciler による起動時リコンシリエーション
  - Broker クライアント抽象化（paper_trading 環境に Mock を使用）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - SQLite に監視ログを永続化（monitoring_db）
  - Streamlit ベースの簡易ダッシュボード
- リサーチ
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC・統計サマリ
- AI 機能
  - OpenAI を使ったニュースセンチメント（ai_scores）および市場レジーム判定

セットアップ（開発用）
--------------------
1. Python 3.10+ を推奨（typing の union 表記などを使用）。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）:
   - pip install duckdb psutil openai requests streamlit
   - 追加でユーティリティやテストに必要なパッケージがあれば適宜インストールしてください。

環境変数（Settings で読み取る主な項目）
---------------------------------------
設定は .env / .env.local または OS 環境変数で指定できます。自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（使用する機能に応じて）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須の場合あり）
- KABU_API_PASSWORD — kabuステーション API 用（実行エンジンで必須）

任意（デフォルトがある）
- KABUSYS_ENV — 環境: development (default) / paper_trading / live
  - paper_trading のときは MockBrokerClient を使い、DB は data/paper_trading.db を使用します。
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）
- OPENAI_API_KEY — OpenAI を使う機能 (news_nlp, regime_detector) を利用する際に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE通知）で使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant/partial/never/reject。デフォルト instant）
- PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH — Kill switch 用フラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

クイックスタート（主要スクリプト）
------------------------------

1) 監視ポーリングループを起動（Monitoring 用）
- 説明: SystemMonitor を定期実行し、system_status / trade_logs / risk_logs / dashboard を更新します。
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
- 注意:
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path を使用して監視 DB を操作します。

2) 実行エンジンを起動（ExecutionEngine）
- 説明: Broker クライアントを作成し、リスク管理・オーダー管理・リコンシリエーションを行ってトレードセッションを実行します。
- 実行:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。

3) Streamlit ダッシュボード（監視用）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB が存在しない場合はエラー表示（MonitoringEngine をまず起動してください）。

4) Paper Trading 検証レポート生成
- スクリプト:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

AI 関連（ニュースセンチメント / レジーム判定）
---------------------------------------------
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続、日付、OpenAI APIキーを与えると ai_scores テーブルへ書き込む。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB の prices_daily/raw_news を参照して market_regime テーブルへ書き込み。
- 実行には OPENAI_API_KEY が必要（引数または環境変数）。

監視に関する注意点
-----------------
- KillSwitch は RiskMonitor の通知に応じて kill.flag を作成し、ExecutionEngine 起動中のプロセスに停止シグナルを送る仕組みです。flag ファイルが存在すると ExecutionEngine 側で検出して安全停止する想定です。
- SystemMonitor は PID ファイル（PID_FILE_PATH）を参照して実行中の ExecutionEngine を検出します。スタレ PID を検出した場合は削除してリスクログに記録します。
- MonitoringDB の初期化（init_monitoring_db）は冪等でテーブル・カラムのマイグレーションを行います。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                 — パッケージ定義
- config.py                   — 環境変数 / 設定読み込みロジック（.env サポート）
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト

packages / サブモジュール
- ai/
  - news_nlp.py               — ニュース NLP（OpenAI）による銘柄スコアリング
  - regime_detector.py       — マーケットレジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py         — SQLite ベースの監視 DB レイヤ
  - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py         — 注文滞留 / 約定異常監視
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 管理
  - alert_manager.py         — LINE Push 通知
  - monitoring_engine.py     — 各 monitor を束ねるループ
  - streamlit_dashboard.py   — Streamlit ダッシュボード
- execution/
  - reconciler.py            — 起動時リコンシリエーション
  - order_manager.py         — Order state machine の外向き API
  - （その他: broker_factory, execution_engine, order_repository 等）
- portfolio/
  - portfolio_builder.py     — 候補選定、重み計算
  - position_sizing.py       — 株数決定・集約キャップ処理
  - risk_adjustment.py       — セクターキャップ、レジーム乗数
- research/
  - factor_research.py       — Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py   — 将来リターン・IC・統計サマリ
- data/
  - pipeline.py (参照されるユーティリティ等)
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
- utils/
  - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上のヒント
---------------
- 環境区分:
  - development: デフォルト（ローカル開発）
  - paper_trading: Mock ブローカーを使用し execution と監視の DB を分離（data/paper_trading.db）
  - live: 本番モード（実際のブローカーを使用）
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で環境変数から変更できます（秒）。
- ExecutionEngine 起動時に PID ファイルを書き、SystemMonitor はその PID を確認します。PID 管理により多重起動やスタレ PID の検出が可能です。
- Streamlit ダッシュボードは読み取り専用モードで起動できます（URI に ?mode=ro を付けて SQLite を開く実装あり）。

ライセンス・注意事項
-------------------
- 本コードは教育的／開発的な目的のサンプル実装です。実運用・本番資金での使用にあたっては十分なテストと法令遵守を行ってください。
- ブローカー API の扱い、注文ロジック、リスク管理は責任を持って実装・検証してください。

追加の情報・貢献
----------------
バグ報告や改善提案、ドキュメント追記は Pull Request または Issue で歓迎します。README の改善点やサンプル設定 (.env.example) の追加なども貢献いただけると助かります。

以上。必要であれば、.env.example のテンプレートや運用手順の詳細（サービス化 / systemd / Docker 化）を追記します。どの情報が欲しいか教えてください。