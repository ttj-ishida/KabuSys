README
======

注意: 本ドキュメントはこのリポジトリ内の Python モジュール群（kabusys）に基づく簡易 README です。実行前に必ず .env（または環境変数）で必要な設定を行ってください。

プロジェクト概要
---------------
KabuSys は日本株の自動売買システム向けユーティリティとコアロジック群の集合です。  
主な目的は以下のとおりです:

- 注文発行・状態管理・再同期を行う ExecutionEngine（実行エンジン）
- システム稼働状況／注文／リスクを監視する Monitoring コンポーネント群
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- リサーチ用のファクター計算・特徴量解析
- ニュースを LLM（OpenAI）でスコアリングして運用に活用する AI モジュール
- Paper Trading（模擬発注）を分離して実行できる仕組み
- Streamlit ベースの監視ダッシュボードや検証レポート生成ツール

機能一覧
---------
- Execution
  - 注文作成、送信、同期、再帰的リコンシリエーション（reconciler）
  - Paper Trading モード（本番 DB と分離して data/paper_trading.db を使用）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション上限監視・アラート記録
  - KillSwitch: フラグファイル（data/kill.flag）書き込みによる ExecutionEngine 停止シグナル
  - AlertManager: LINE に対する一方向プッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio construction
  - 候補選定、等重／スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出
- Research
  - Factor 計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー等
- AI
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを ai_scores に書き込み
  - レジーム判定（ETF ma200 とマクロニュースの LLM センチメントを合成）
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

事前準備 / 必要なライブラリ
---------------------------
最低限必要な外部依存（代表例）:
- Python 3.8+
- duckdb
- psutil
- requests
- streamlit (ダッシュボードを使う場合)
- openai (AI 機能を使う場合)

（実際の requirements.txt が無い場合は上記を pip でインストールしてください）
例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil requests streamlit openai

セットアップ手順
----------------
1. リポジトリをクローン:
    git clone <repo-url>
    cd <repo-root>

2. 仮想環境作成・有効化（推奨）:
    python -m venv .venv
    source .venv/bin/activate

3. 依存インストール:
    pip install duckdb psutil requests streamlit openai

4. データディレクトリの作成（デフォルトパスを使う場合）:
    mkdir -p data

5. 環境変数設定:
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書きあり）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要エントリポイント）
------------------------------

- 監視ループを起動（Monitoring の最小単位: SystemMonitor 単独実行スクリプトも同梱）:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視 DB を初期化します

- 実行エンジン（ExecutionEngine）を起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、Mock ブローカーを使用し data/paper_trading.db に記録（本番 DB とは完全分離）
  - 実行時にプロセス優先度を "high" に設定する処理が行われます（set_process_priority）

- Streamlit ダッシュボード起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - --db で監視 DB パスを指定可能（デフォルト data/monitoring.db）。読み取り専用で開きます。

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report
  - オプション:
      --from YYYY-MM-DD
      --to   YYYY-MM-DD
      --db   PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 関連（プログラムから利用）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを参照して OpenAI に問い合わせ、ai_scores を更新します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（コード 1321）の MA200 とマクロニュースを LLM で評価し market_regime テーブルに書き込みます。
  - これらは OpenAI API キー（OPENAI_API_KEY 環境変数または引数）を必要とします。

設定（環境変数）
----------------
主な環境変数（コード中で参照されているもの）:

- 基本 / 認証
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須) — kabuステーション API 用
  - OPENAI_API_KEY （AI 機能が必要な場合）
  - LINE_CHANNEL_ACCESS_TOKEN（アラート送信に使用、未設定なら送信はスキップ）
  - LINE_USER_ID（アラート送信先）

- 動作モード / ログ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine 用 pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch 用フラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag を自動クリア

- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- Monitoring 周り
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60。0 以下はデフォルトにフォールバック）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（閾値を設定、デフォルトはコード内の値）

挙動メモ
--------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で読み込みます（OS 環境変数は上書きされません）。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- DB 初期化:
  - init_monitoring_db() を呼ぶと監視用のテーブル群が冪等に作成されます（マイグレーション処理も一部含む）。

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path を使用して本番監視 DB と分離します。

- Kill Switch:
  - KillSwitch は条件を満たすと KILL_FLAG_PATH に理由を書き込みます。既にフラグが存在する場合は書き込みをスキップします。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースを OpenAI でスコアリング
  - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — monitoring 用 SQLite の永続化層
  - system_monitor.py      — システム状態・データ鮮度チェック
  - trade_monitor.py       — 注文滞留・約定異常監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 管理
  - alert_manager.py       — LINE 通知送信
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - reconciler.py          — 起動時の注文/ポジション再同期
  - order_manager.py       — 注文状態遷移と Broker 呼び出しラッパー
  - ほか (broker_factory 等、ブローカー連携関連は同ディレクトリに存在)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py     — Momentum / Volatility / Value のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - __init__.py
- tools/
  - paper_verification_report.py — Paper Trading DB から検証レポートを生成するスクリプト
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意 / ベストプラクティス
----------------------------------
- 本番稼働時は KABUSYS_ENV=live を設定し、適切な DB / API キーを使ってください。
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB に完全分離されます。
- OpenAI を使う機能は API コスト・レート制限に注意してください（実装はリトライ・バックオフを含みますが、運用上の監視が必要です）。
- kill.flag や PID ファイルの管理が停止制御に使われます。これらのファイルの配置パスは Settings で指定可能です。
- streamlit ダッシュボードは監視 DB を読み取り専用で開くため、運用中に安全に可視化できます。

ライセンス / 貢献
-----------------
（このリポジトリのライセンス・貢献ルールはここに記載してください。リポジトリに LICENSE があればそちらを参照してください。）

補足
----
この README はコードベースの主要点をまとめたものです。詳細な使い方やパラメータ調整（リスク閾値、ポートフォリオ戦略など）は各モジュールの docstring を参照してください。質問や補足したい箇所があればお知らせください。