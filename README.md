KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
戦略のためのファクター計算・ポートフォリオ構築・ポジションサイジング、実際の発注を担う実行エンジン、実行状況・リスクを監視する Monitoring コンポーネント、LLM を使ったニュースセンチメントやレジーム判定などの機能を備えます。

主な設計方針
- DuckDB / SQLite を使ったデータ処理・永続化（外部 DB は不要）。
- Paper Trading と Live を環境で分離（paper_trading は MockBroker を使用し専用 SQLite を利用）。
- 自動ロードされる .env / .env.local による環境設定（必要に応じて無効化可）。
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定をサポート（API キー必須）。

機能一覧
--------
- ExecutionEngine（発注・注文管理・リコンシリエーション）
  - Broker 抽象化により実際のブローカーまたは MockBroker を利用可能
  - リスク管理、オーダー管理、再起動時の同期（Reconciler）
- Monitoring（システム監視・注文監視・リスク監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数上限の監視とアラート記録
  - KillSwitch: 条件達成時にデータ/kill.flag を書き ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（オプション）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio Construction
  - 候補選定・重み付け・等分/スコア配分
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め・集約キャップ）
- Research / Factor Modules
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で完結）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄ごとの ai_score を生成
  - regime_detector: ETF（1321）の MA とマクロニュースを合成して市場レジーム判定
- CLI ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.9+（ソースは型ヒントで modern Python を想定）
- git

依存パッケージ（主なもの）
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- （標準ライブラリに sqlite3 等含む）

例: 仮想環境の作成と依存インストール
- git clone ...
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- pip install -U pip
- pip install duckdb psutil requests openai streamlit

環境変数
- 自動読み込み: プロジェクトルートにある .env（および .env.local）を自動で読み込みます。
  - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject、デフォルト instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 環境の SQLite パス（デフォルト data/paper_trading.db）
  - SQLITE_PATH — 監視用（production 想定）SQLite パス（デフォルト data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

初期 DB 作成
- Monitoring は起動時に必要なテーブルを作成します（init_monitoring_db）。手動で準備する必要は通常ありません。

使い方
------

実行エンジン起動（本番 / paper_trading 判定あり）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に書き込まれます。
  - 起動時に data/execution.pid が作成されます（PID 管理）。
  - 停止は data/stop_requested.flag を作成するか、kill.flag により外部から停止可能。

監視ループ起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（監視 DB）を使います。
  - 停止は data/stop_requested.flag を作成することでループを抜けます。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定

Streamlit ダッシュボード
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

AI 関連（プログラムから呼ぶ）
- kabusys.ai.score_news(conn, target_date, api_key=...)
  - DuckDB 接続を渡し、raw_news から銘柄ごとのスコアを ai_scores テーブルへ書込み。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - market_regime テーブルに書き込む。

停止・Kill Switch
- KillSwitch はリスク閾値を満たすと data/kill.flag を書き込み、ExecutionEngine の停止トリガーになります。
- 手動で停止したい場合は data/stop_requested.flag を作成します（run_* スクリプトが検知して停止）。

その他運用ポイント
- Monitoring の system モジュールは PID ファイルの stale 判定やデータ鮮度チェック（get_last_price_date）を行います。
- paper_trading 環境は本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- 環境変数の自動ロード順序: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- MONITOR_POLL_INTERVAL に 0 以下の値を与えると警告が出てデフォルトにフォールバックします。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py (バージョン)
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）→ ai_scores 書込み
  - regime_detector.py — レジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各監視ロジック
  - monitoring_engine.py — 全 Monitor を束ねるループ
  - kill_switch.py — 停止フラグ書込みユーティリティ
  - alert_manager.py — LINE 通知
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory など（発注／同期ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・解析
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading レポート生成ツール

付録：よくある質問（FAQ）
------------------------
Q: Paper Trading と本番 DB は混ざりますか？
A: いいえ。KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使います。Monitoring は常に sqlite_path（監視 DB）を使用します。

Q: OpenAI API が無いとどうなりますか？
A: AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY が必須です。未設定だと例外（ValueError）を投げますが、システム本体（発注・監視）は API なしでも動作します。

Q: .env の自動読み込みを無効にできますか？
A: はい。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします（テスト用途などに便利です）。

貢献・注意事項
--------------
- 本リポジトリは金融取引に関わるロジックを含むため、本番運用前に十分なレビュー・テストを行ってください。
- MockBroker を用いた動作確認・回帰テストを推奨します。
- ライセンス・利用条件は本リポジトリに従ってください（ここでは明示していません）。

必要であれば .env.example のサンプルや systemd / supervisor 向けの起動ユニット例、Dockerfile、requirements.txt のテンプレートも作成します。希望があれば教えてください。