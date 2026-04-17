KabuSys — 日本株自動売買システム
============================

概要
----
KabuSys は日本株向けの自動売買エンジン（ExecutionEngine）とそれを支える監視/解析ツール群を含む Python プロジェクトです。本リポジトリは以下の主要コンポーネントを提供します。

- 実行エンジン起動スクリプト（run_execution）
- 監視ポーリング/ログ用コンポーネント（monitoring）
- ポートフォリオ構築・サイズ計算ロジック（portfolio）
- 研究用ファクター・特徴量モジュール（research）
- ニュースの NLP スコアリング / レジーム判定（ai）
- Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard）

主な特徴
--------
- ExecutionEngine と Monitoring の明確な分離（監視は本番監視DBを使用し、paper_trading 環境でも同じ監視DBを参照）
- Paper Trading モード（KABUSYS_ENV=paper_trading）では発注をモック化し、専用 SQLite（data/paper_trading.db）に分離
- DuckDB を用いた時系列・ファクター計算（prices_daily / raw_financials 参照）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価とレジーム判定（API 呼び出しはフェイルセーフ実装）
- 監視（System/Trade/Risk）と Kill Switch、LINE 通知（AlertManager）によるアラート送信
- Streamlit ダッシュボードで監視データを可視化
- DB スキーマの冪等初期化・簡易マイグレーション（monitoring_db.init_monitoring_db）

前提 / 必要環境
---------------
- Python 3.9+
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (ai モジュール利用時)
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI API / LINE API を使う場合）

インストール（開発環境例）
-------------------------
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトの requirements.txt が無い場合は個別に）:
   - pip install duckdb psutil requests streamlit openai

3. ソースコードがあるディレクトリ直下で実行する前提です（.env 自動読み込み機能あり、プロジェクトルートは .git または pyproject.toml を基準に探索します）。

環境変数（主なもの）
-------------------
プロジェクトは .env / .env.local（OS 環境 > .env.local > .env の優先順）を自動で読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD     — kabuステーション API 用パスワード

主な任意設定（デフォルト値を併記）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使い data/paper_trading.db を使用
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.score_news / regime 判定で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（監視・停止制御）

セットアップ手順（簡易）
---------------------
1. 仮想環境作成・依存ライブラリをインストール（上記参照）。
2. 必須環境変数を .env に記載（.env.example を参考に作成）。
3. data ディレクトリを作成（必要に応じて）:
   - mkdir -p data
4. 初回はモジュールを直接呼んで監視 DB を作成できます（run_monitoring run の開始時に自動で init_monitoring_db が呼ばれます）。

使い方
------

ExecutionEngine 起動（実運用 / Paper Trading）
- 本番または開発で実際に注文を行うエンジンを起動します。
- コマンド:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、settings.is_paper が True となり paper_sqlite_path（デフォルト data/paper_trading.db）を使用しブローカーは MockBrokerClient になります。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動をスキップします。
  - 実行中に data/stop_requested.flag が作られると安全に停止します（外部ツールや管理スクリプトでフラグ作成可）。

Monitoring（監視ループ）起動
- コマンド:
  - python -m kabusys.run_monitoring
- 動作:
  - MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once() を繰り返します（デフォルト 60 秒）。
  - 監視は Settings.env に関わらず本番 sqlite_path（data/monitoring.db）を参照してログ保存します。
  - data/stop_requested.flag を作成すると監視ループを終了します。

監視ダッシュボード（Streamlit）
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

Paper Trading 検証レポート生成
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 出力:
  - 稼働率、注文成功率（Fill）、送信率（Sent）、レイテンシ（平均/最大/P95）などのサマリと PASS/FAIL 判定

AI（ニュース NLP / レジーム検出）プログラム的使用
- 関数:
  - kabusys.ai.score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str|None)
  - kabusys.ai.regime_detector.score_regime(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str|None)
- 注意:
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
  - 大量 API 呼び出しはレート制限によりリトライ・バックオフ処理が行われます（失敗時は安全側でスキップし続行）。

停止・強制停止
- ExecutionEngine 停止（推奨安全操作）:
  - data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送る KillSwitch が発動します（設定により kill.flag パスを変更可能）。
  - KillSwitch は drawdown やポジション上限超過で自動的に書き込まれることがあります。
- 監視・実行スクリプトの即時停止:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
  - 実行中は data/execution.pid（デフォルト）に PID を書き、PID ファイルの stale 検出等を行います。

データベース（ファイル・マイグレーション）
- 監視 DB（SQLite）初期化:
  - init_monitoring_db(conn) がテーブル作成と簡易マイグレーション（列追加）を冪等に実行します。
- デフォルトパス:
  - monitoring DB: data/monitoring.db
  - duckdb: data/kabusys.duckdb
  - paper trading DB: data/paper_trading.db

ディレクトリ構成（主要ファイル）
----------------------------
リポジトリの主要なモジュール構成（src/kabusys 以下）：

- __init__.py
  - パッケージメタ情報（__version__ など）

- config.py
  - Settings クラス: 環境変数読み込み・バリデーション・デフォルト管理
  - .env 自動読み込み機能

- run_execution.py
  - ExecutionEngine を組み立てて起動するスクリプト（スレッド実行 / stop flag を監視）

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト

- ai/
  - news_nlp.py: raw_news を LLM でスコアリングして ai_scores に書き込むロジック
  - regime_detector.py: マクロセンチメントとETF MA を合成して market_regime を決定

- monitoring/
  - monitoring_db.py: SQLite 用永続化層（テーブル作成 / MonitoringDB クラス）
  - system_monitor.py: CPU/MEM/DISK・データ鮮度・PID チェック
  - trade_monitor.py: 滞留注文・約定異常価格検出
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag の生成/判定
  - alert_manager.py: LINE 通知プッシュ（クールダウン機能）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ダッシュボード

- execution/
  - order_manager.py, order_repository.py, reconciler.py, 等: ブローカー連携と注文管理の実装（Engine 組み立てで使用）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定、重み・株数計算、セクター/レジーム調整

- research/
  - factor_research.py, feature_exploration.py: DuckDB を用いたファクター計算、将来リターン・IC・統計サマリ

- tools/
  - paper_verification_report.py: Paper Trading 用検証レポート生成 CLI

- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

開発上の注意・トラブルシューティング
------------------------------------
- psutil によるプロセス優先度設定は権限依存です。AccessDenied が出た場合は警告ログに留まり実行は継続します。
- OpenAI 呼び出しはネットワーク/キー依存。API エラーはリトライやフェイルセーフによりシステムを壊さないよう実装されていますが、API キー未設定は例外となる関数があります（明示的にチェックしてください）。
- monitoring は常に sqlite_path（data/monitoring.db）を使用します。paper_trading モードでも監視は本番監視 DB に記録されます（監視側と実行側 DB を分離する設計です）。
- .env のパースは POSIX シェル風に動作しますが完全な互換を保証するものではありません。特殊な値はクォートして保存してください。
- DuckDB 操作はテーブルが存在しないと OperationalError を出します。レポート/AI 処理はテーブルの存在を前提に呼び出してください（ツール側は例外をキャッチして N/A を出力する場合があります）。

ライセンス / 貢献
-----------------
（ライセンス情報はここに追記してください。プロジェクトに合わせて MIT / Apache 2.0 などを設定してください。）

最後に
------
この README はコードベースの主要部分を簡潔にまとめたものです。実運用環境へのデプロイやブローカー接続設定、バックアップ・監視・権限の細かい運用ルールは別途運用ドキュメントを整備してください。追加で「実行エンジンの設定ファイル例」や「.env.example」のテンプレートを作成することを推奨します。