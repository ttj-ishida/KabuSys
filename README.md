KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・モニタリング基盤の一部実装です。本リポジトリは以下の主要コンポーネントを含みます。

- 実行エンジン（ExecutionEngine）: ブローカーとの発注・リスク管理・注文管理を行う
- 監視（Monitoring）: システム状態・注文監視・リスク監視・アラート送信・Kill Switch
- ポートフォリオ構築ロジック: 候補選定、重み付け、ポジションサイズ算出、セクター制限等
- リサーチ用機能: ファクター計算、前方リターン計算、IC 等の統計ユーティリティ
- AI モジュール: ニュースのセンチメント集約（OpenAI）と市場レジーム判定
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード

主な機能一覧
-------------
- 実行系
  - 注文作成・送信・同期（OrderManager / Reconciler）
  - リスク制御・サーキットブレーカー設定（RiskManager 等）
  - Paper Trading モード（環境変数 KABUSYS_ENV=paper_trading）でブローカーをモック化して専用 DB に記録
- 監視系
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス存在確認、株価データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、kill.flag の書き込み
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分／スコア加重配分、リスクベースの株数算出
  - セクター上限制御、レジームに応じた乗数適用
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI（OpenAI）
  - ニュース記事を集約して銘柄別のセンチメントスコアを算出して ai_scores テーブルへ格納
  - マクロニュースと ETF の MA200 乖離を合成して市場レジーム（bull/neutral/bear）を判定

セットアップ手順
----------------

前提
- Python 3.8+（できれば 3.10 以上推奨）
- SQLite（標準で同梱）
- DuckDB（Python パッケージを使用）
- ネットワークアクセス（実行時に外部 API を使う場合）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

インストール例
1. 仮想環境作成（例）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な環境変数（デフォルト値 / 説明）:

  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
  - KABU_API_PASSWORD: 必須（kabuステーション API 用）
  - KABU_API_BASE_URL: kabusapi ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、default: instant）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（default: data/kill.flag）
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（default: 60）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

データベース初期化
- 実行スクリプト起動時に monitoring 用の SQLite テーブルは自動で作成します（init_monitoring_db）。
- DuckDB 用の prices_daily / raw_financials 等のテーブルは外部で用意する必要があります（データ投入は別途）。

使い方（起動・実行例）
---------------------

1) ExecutionEngine（本番 / ペーパートレード）
- 本番（デフォルト KABUSYS_ENV=development / live）
  python -m kabusys.run_execution

- Paper Trading（ブローカーをモック化し、data/paper_trading.db を使用）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

- 実行前に .env に必要な環境変数（KABU_API_PASSWORD など）を設定してください。

2) Monitoring（ポーリングループ）
- デフォルト 60 秒間隔で監視を行います。間隔は環境変数で上書き可能です。
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring

- run_monitoring は監視用 SQLite（settings.sqlite_path）と DuckDB を開き、SystemMonitor のチェックループを回します。

3) Streamlit ダッシュボード（監視 UI）
- 起動例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  --db オプションで既存の monitoring DB を指定できます（read-only URI を用いた接続を行います）。

4) Paper Trading 検証レポート
- usage:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

5) AI モジュール（ニューススコア / レジーム判定）
- 例（Python REPL やスクリプト内）:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")

- OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている場合、api_key 引数は省略可能です。

プロセス優先度
- run_* スクリプトは起動時に set_process_priority("high") を呼びます（psutil を使用）。権限不足や未対応 OS の場合は警告を出してスキップします。

設定の自動読み込み
- config モジュールはプロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数が優先、.env.local は上書き）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要なファイルと簡単な説明です。

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は Paper Trading 用 DB と Mock ブローカーを使用。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。

- config.py
  - 環境変数・設定の管理。自動 .env ロード、Settings クラスを提供。

- __init__.py
  - パッケージ定義とバージョン。

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成。

- portfolio/
  - portfolio_builder.py: 候補選定、等重・スコア重み計算
  - position_sizing.py: 株数算出、集約上限調整
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- monitoring/
  - monitoring_db.py: SQLite のスキーマ初期化 / DB 操作ラッパー（MonitoringDB）
  - system_monitor.py: CPU/メモリ/Disk・プロセス・データ鮮度チェック
  - trade_monitor.py: 滞留注文・約定価格異常チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の生成・確認・削除
  - alert_manager.py: LINE への通知（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねて定期実行
  - streamlit_dashboard.py: Streamlit を使った監視画面

- execution/
  - order_manager.py, reconciler.py, 等: 注文管理・復旧ロジック（Reconciler は再起動時の同期）

- research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー

- ai/
  - news_nlp.py: ニュース集約 → OpenAI に投げて銘柄別スコアを ai_scores に書込
  - regime_detector.py: ETF MA200 乖離 と マクロニュースセンチメントでレジーム判定

- utils/
  - process_priority.py: psutil を使ったプロセス優先度・CPU affinity 設定ユーティリティ

運用上の注意
-------------
- Paper Trading は本番 DB と分離されます。KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用するため誤って本番データを上書きするリスクは低くなっていますが、設定は必ず確認してください。
- AI（OpenAI）呼び出しは API レート制限・料金が発生します。API キーの管理に注意してください。
- monitoring の kill.flag は ExecutionEngine の停止を外部からトリガーします。KillSwitch の動作ログとフラグファイルの存在に注意してください。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）は別途データ投入が必要です。リサーチ・AI 機能は該当テーブルが整備されていることが前提です。

貢献・拡張
-----------
- テストカバレッジの追加（ユニットテスト / モック）
- stocks マスターから lot_size を取得するなどのポジション算出改善
- AlertManager の通知チャネル追加（メール / Slack 等）
- DuckDB スキーマ用の初期化スクリプトやデータロードツールの追加

ライセンス
----------
- 本リポジトリに関するライセンス表記はプロジェクトのルートに従ってください（ここには含まれていません）。

お問い合わせ
------------
実装や使い方に関する質問があれば、プロジェクトの issue または担当者にお問い合わせください。

以上。