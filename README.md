# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買・リサーチ基盤ライブラリです。本リポジトリには以下の主要機能を備えています。
- ExecutionEngine による発注フロー（ブローカー抽象化、オーダーマネージャ、リスク管理、リコンシリエーション）
- Monitoring（システム/注文/リスク監視、LINE 通知、kill flag による停止）
- ポートフォリオ構築（銘柄選定、重み計算、ポジション決定、セクター制限）
- リサーチ（ファクター計算、特徴量探索、将来リターン・IC 計算）
- AI モジュール（OpenAI を使ったニュース NLP、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）
- 設定管理（.env 自動読み込み、Settings クラス）

主な特徴
---
- 環境分離：paper_trading モードでは本番 DB と完全に分離された paper_trading.db を使用します。
- DuckDB を使った高速な時系列ファクター計算（prices_daily / raw_financials を参照）
- OpenAI を用いたニュースセンチメント評価（AI モジュールは冪等性・リトライ・検証を考慮）
- 監視機能：CPU/メモリ/ディスク、データ鮮度、滞留注文、約定異常、ドローダウン、ポジション上限
- アラート：LINE Messaging API による push 通知（クールダウン管理あり）
- 運用用フラグファイル（data/kill.flag、data/stop_requested.flag）による安全停止
- 実行プロセス優先度設定（Windows/Linux/macOS 対応、psutil 使用）

セットアップ手順
---
前提
- Python 3.9+（ソースの型注釈に合わせてください）
- SQLite（標準ライブラリで利用）
- 必要な外部ライブラリ（以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
  
例（pip）
  pip install duckdb psutil openai requests streamlit

環境変数・.env
- プロジェクトルートに .env / .env.local を置くことで自動的に読み込まれます（CWD ではなくソース位置からプロジェクトルートを探索）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（抜粋）
- KABUSYS_ENV: deployment 環境。valid: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行用ファイルパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

サンプル .env
  KABUSYS_ENV=paper_trading
  JQUANTS_REFRESH_TOKEN=xxxxxxxx
  KABU_API_PASSWORD=yyyyyyyy
  OPENAI_API_KEY=sk-...
  LINE_CHANNEL_ACCESS_TOKEN=
  LINE_USER_ID=
  PAPER_FILL_MODE=instant
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  SQLITE_PATH=data/monitoring.db
  DUCKDB_PATH=data/kabusys.duckdb
  LOG_LEVEL=INFO

初期 DB 準備
- monitoring 用 DB（SQLite）は起動時に必要なテーブルを自動作成します。特別なマイグレーションは不要です。
- DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを投入して利用します（データ取り込みは別実装を想定）。

使い方
---
実行エンジン（ExecutionEngine）
- Paper Trading（本番と分離）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Live / development:
  KABUSYS_ENV=live python -m kabusys.run_execution
  （Settings に応じて使用 DB が切り替わります）

監視プロセス（Monitoring）
- 定期的にシステム・注文・リスクをチェックして monitoring DB に書き込みます:
  python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は Settings.sqlite_path（monitoring DB）を常に使用します（KABUSYS_ENV に依存しません）。

停止・強制停止
- 停止リクエスト（run_execution / run_monitoring のループ共通）:
  data/stop_requested.flag（存在するとループが検知して終了）
- ExecutionEngine 側の致命的条件（ドローダウン等）から停止シグナルを送る:
  data/kill.flag（KillSwitch が書き込み、run_execution が検出して停止）
- 起動時に kill flag を自動でクリアしたい場合は Settings.kill_flag_clear_on_start を設定可能（環境変数で 1 に設定）。

Streamlit ダッシュボード
- 監視 DB の内容を可視化する簡易ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- 過去期間の Paper Trading のパフォーマンスと安定性を表示:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。--db オプションで上書き可。

AI（ニュース NLP / レジーム判定）
- OpenAI API キー (OPENAI_API_KEY) が必要です。
- プログラム的に呼び出す例（Python 内で）:
  from kabusys.ai import score_news
  # duckdb_conn は DuckDB 接続オブジェクト、target_date は datetime.date
  score_news(duckdb_conn, target_date, api_key="sk-...")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="sk-...")

内部運用の注意点
- run_monitoring は監視用 DB（Settings.sqlite_path）に常に書き込みます。実運用で Monitoring を開発モード・テストモードと分離したい場合は sqlite_path を変更してください。
- run_execution は paper_trading モード時に paper 用 DB を使うため、本番 DB へ誤って書き込むリスクは低く設計されています。
- process priority（優先度設定）には psutil を使用します。権限がない場合は警告が出ますが起動は続行します。
- .env の自動読み込みは .env → .env.local の順で行われ、OS 環境変数を保護します。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成 (主要ファイル)
---
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理、.env 読み込み
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート CLI
- execution/
  - execution_engine.py      — ExecutionEngine（メイン実行ロジック） (参照)
  - order_manager.py         — OrderManager（発注ロジック）
  - order_repository.py      — DB 操作（OrdersDB など）
  - reconciler.py            — 再起動リコンシリエーション
  - broker_factory.py        — Broker クライアント生成（紙/本番切替）
  - ...                     — ブローカー API 抽象など
- monitoring/
  - monitoring_db.py         — monitoring DB スキーマ＋読み書きユーティリティ
  - system_monitor.py        — システム状態・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常監視
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 書き込みユーティリティ
  - alert_manager.py         — LINE 通知ユーティリティ
  - monitoring_engine.py     — 各モニタ束ねる実行器
  - streamlit_dashboard.py   — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py     — 候補選定・重み付け
  - position_sizing.py       — 株数算定・スケーリング・単元丸め
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
- research/
  - factor_research.py       — Momentum/Value/Volatility 計算（DuckDB）
  - feature_exploration.py   — 将来リターン / IC / 統計ユーティリティ
- ai/
  - news_nlp.py              — ニュース NLP スコア生成（OpenAI）
  - regime_detector.py       — レジーム判定（MA + マクロ NLP）
- utils/
  - process_priority.py      — プロセス優先度・CPU affinity ユーティリティ
- data/                      — 運用用ファイル置き場（データベース等。gitignore 想定）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

ライセンス・貢献
---
本 README はコードベースの説明と運用上の注意をまとめたものです。実際の運用ではブローカー API の権限管理やキー管理、テスト環境・リハーサル運用を十分に行ってください。Pull request や issue は歓迎します。

補足（よくある質問）
- Q: Paper Trading と Live を切り替えるには？
  A: KABUSYS_ENV=paper_trading を設定して run_execution を起動してください。paper_trading の DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

- Q: 監視のポーリング間隔を変えたい
  A: MONITOR_POLL_INTERVAL 環境変数を秒数で設定してください（1 以上）。不正な値はデフォルト 60 秒にフォールバックします。

- Q: AI 機能をオフにしたい
  A: OPENAI_API_KEY を設定しなければ score_news / score_regime は例外を送出します。呼び出し側でキーの有無を管理してください。

以上。必要であれば、README に含めるサンプルコマンドや環境変数の詳細をさらに追記します。希望があれば教えてください。