KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買システムのコアライブラリ群です。本リポジトリに含まれるモジュールは以下のカテゴリに分かれ、ロジックは主にローカル DB（SQLite / DuckDB）を使って完結する設計になっています。

- 実行（Execution）: ブローカー連携・注文管理・リコンシリエーション
- 監視（Monitoring）: システム状態・注文異常・リスク監視・アラート
- ポートフォリオ構築（Portfolio）: 候補選定・配分・ポジションサイジング・リスク調整
- 研究（Research）: ファクター計算・特徴量解析
- AI 支援（AI）: ニュース NLP によるセンチメント集計・市場レジーム判定（OpenAI を利用）
- ツール（Tools）: Paper Trading の検証レポート等
- ユーティリティ（Utils）: 環境設定読み込み・プロセス優先度設定 等

主な特徴
-------
- DuckDB / SQLite を用いたオンプレミス指向のデータ処理（外部 API へは最小限に抑制）
- Paper Trading モード（本番 DB とは完全に分離）をサポート
- 監視エンジン（MonitoringEngine）でプロセス・データ鮮度・注文滞留・ドローダウン等を連続監視
- LINE Push によるアラート送信（AlertManager）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント評価と市場レジーム判定（AI モジュール）
- Streamlit による監視ダッシュボード（読み取り専用で監視 DB を可視化）
- 設定は .env / 環境変数から読み込み（自動ロード機構あり）

動作前提（推奨）
----------------
- Python 3.10+
- 必要パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ）を利用します
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY の設定が必要

インストール（例）
-----------------
仮想環境作成・有効化後に必要パッケージをインストールします:

- 仮想環境作成（例）
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate

- 必要パッケージをインストール（最低限）
  pip install duckdb psutil requests openai

- Streamlit ダッシュボードを使う場合：
  pip install streamlit

設定（環境変数 / .env）
---------------------
環境変数は .env / .env.local / OS 環境変数から読み込まれます（プロジェクトルートに .git または pyproject.toml があることが条件）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定時は送信をスキップ）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- KABUSYS_ENV — 実行環境（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、デフォルト: 60）

簡単な .env 例
--------------
以下は最低限のサンプル（実運用では秘密情報は安全に管理してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxx
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

セットアップ手順
---------------
1. リポジトリをクローンして仮想環境を作成・有効化する
2. 必要パッケージをインストール（上記参照）
3. data ディレクトリを作成する（必要に応じて）:
   mkdir -p data
4. .env を作成して環境変数を設定する
5. DuckDB / SQLite ファイルは最初の起動時に自動作成／テーブル初期化されます（init_monitoring_db を利用）

使い方（主要スクリプト）
-----------------------

- 監視ループ（SystemMonitor 単体起動）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は本番の sqlite_path を使用（KABUSYS_ENV に依らず）

- 実行エンジン（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と分離）
  - 実行時にプロセス優先度を high に設定しようとします（psutil による権限依存）

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD    レポート開始日
    --to   YYYY-MM-DD    レポート終了日
    --db PATH            SQLite DB パス（指定なければ PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで監視 DB（monitoring.db）を可視化します

主要モジュールと簡単な説明
-------------------------
- kabusys.config
  - .env の自動読み込み、Settings クラスによる設定取得ロジック

- kabusys.monitoring
  - monitoring_db.py: SQLite による監視テーブルの初期化・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU / メモリ / ディスク / プロセス PID / データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常価格検出
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: 条件に応じて kill.flag を書き込み ExecutionEngine を停止させる
  - alert_manager.py: LINE Push による通知（クールダウン制御付き）
  - monitoring_engine.py: 各 Monitor を束ねるポーリング実行ロジック
  - streamlit_dashboard.py: Streamlit でのダッシュボード

- kabusys.execution
  - order_manager.py, reconciler.py, order_repository 等（注文ライフサイクル、再同期処理）
  - run_execution.py: 実行エンジン起動スクリプト（paper_trading 判定で MockBroker を使用）

- kabusys.portfolio
  - portfolio_builder.py: 候補選定（スコア順）・等重/スコア重み計算
  - position_sizing.py: 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py: セクターキャップ適用、レジーム乗数計算

- kabusys.research
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン計算、IC 計算、統計サマリ

- kabusys.ai
  - news_nlp.py: raw_news から銘柄ごとのニュースをまとめて OpenAI に投げ、ai_scores テーブルへ保存
  - regime_detector.py: ETF の MA200 とマクロニュースの LLM 評価を合成して market_regime テーブルへ書き込む

- kabusys.utils
  - process_priority.py: psutil を使ったプロセス優先度・CPU アフィニティ設定ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py
- tools/
  - __init__.py
  - paper_verification_report.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（order_repository / broker_factory 等、リポジトリに依存）
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
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- utils/
  - process_priority.py
  - __init__.py
- tools/
  - paper_verification_report.py

運用上の注意 / トラブルシューティング
-----------------------------------
- psutil による優先度設定・CPU affinity は OS と権限に依存します。AccessDenied が出る場合は権限を上げるかログに注意してください。
- OpenAI API 呼び出しはネットワーク・レート制限・API 制約により失敗することがあります。AI 関連処理はリトライ／フォールバック実装を含みますが、API キーの未設定は即座にエラーになります。
- Paper Trading モードは本番 DB と完全に分離する設計です。KABUSYS_ENV=paper_trading を指定することで PAPER_TRADING_SQLITE_PATH を使います。
- monitoring_db.init_monitoring_db() は冪等にテーブルを作成・簡単なマイグレーション（カラム追加等）を行います。既存 DB に対する変更は注意して行ってください。
- Streamlit ダッシュボードは読み取り専用で DB を開きます（URI に mode=ro を付与）。MonitoringEngine を停止せずダッシュボードを起動しても読み取りは可能ですが、同時に DB を書き込むプロセスがある場合は SQLite のロックに注意してください。

ライセンス・貢献
----------------
（本リポジトリ特有のライセンス情報や貢献方法があればここに記載してください）

最後に
------
この README はコードベース（src/kabusys 以下）を参照して作成しています。実行前に .env を正しく設定し、必要なパッケージをインストールしてください。追加のセットアップ手順（外部データの投入や stocks マスター作成など）は別ドキュメントにまとめることを推奨します。