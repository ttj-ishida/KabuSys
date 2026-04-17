KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買（リサーチ → ポートフォリオ構築 → 発注）と運用監視のための小規模フレームワークです。本リポジトリには以下の主要機能をもつモジュール群が含まれます。

- システム監視（CPU/メモリ/ディスク、データ鮮度、滞留注文・約定異常検知）
- ExecutionEngine（ブローカーへの発注管理、リスク制御、再起動時リコンシリエーション）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、特徴量解析、IC計算）
- AI 支援（ニュースセンチメント評価、レジーム判定。OpenAI を利用）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な機能一覧
-------------
- monitoring
  - SystemMonitor: プロセス・システムリソース・データ鮮度のポーリングとログ化
  - TradeMonitor: 滞留注文や約定異常の検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視、risk_logs への永続化
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みと LINE 通知（任意）
  - MonitoringEngine: 上記を束ねて定期実行
  - Streamlit ダッシュボードで現状可視化
- execution
  - ExecutionEngine（起動スクリプト run_execution.py）
  - OrderManager / OrderRepository / Reconciler（再起動時の自動復旧）
  - BrokerFactory: 環境に応じて実ブローカー or MockBroker を選択（paper_trading 用）
- portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクター上限・レジーム乗数）、株数決定（単元丸め）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- ai
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores への書込み
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成してレジーム判定
- tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10+（注: typing の一部機能を使用）
- SQLite は標準で利用可能
- 以下の Python パッケージが必要（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
インストール例:
- pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数（Settings で参照されるもの）
  - KABUSYS_ENV: environment（development / paper_trading / live）デフォルト: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

データベース初期化
- 監視用 SQLite は run_monitoring/run_execution 実行時に必要なテーブルを作成します（init_monitoring_db を通じて冪等に作成）。
- DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを持つことを想定します（データ投入は別途スクリプトや ETL による）。

使い方（実行例）
-----------------
- 監視ループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（デフォルト 60）
  - 例: KABUSYS_ENV=development python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）
- ExecutionEngine 起動
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と完全に分離）
  - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止は data/stop_requested.flag を作成すると安全に停止されます
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも設定可）
- AI モジュール（Python API）
  - ニューススコア付与（例）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, date(2026,4,1), api_key="...")  # OPENAI_API_KEY で代替可
  - レジーム判定（例）:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, date(2026,4,1), api_key="...")

重要な挙動メモ
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（production 相当の monitoring.db）を使用して監視ログを書きます。
- run_execution は KABUSYS_ENV が paper_trading のとき paper_sqlite_path（通常 data/paper_trading.db）を使用します。
- MONITOR_POLL_INTERVAL は 1 以上の整数で指定してください。0 以下や不正値はデフォルト 60 秒にフォールバックします。
- kill.switch 用フラグ: Settings.kill_flag_path（デフォルト data/kill.flag）。KillSwitch は条件を満たすとこのファイルを書き、ExecutionEngine 側で検出して停止します。
- プロセス優先度設定: 起動時に set_process_priority("high") を呼びます。psutil の権限や OS により設定できない場合は警告が出力されます。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py               — パッケージ初期化、バージョン
- config.py                 — 環境変数/設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py         — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト

サブパッケージ（代表）
- ai/
  - news_nlp.py             — ニュースセンチメント評価（OpenAI）
  - regime_detector.py      — 市場レジーム判定（ma200 + LLM 合成）
- monitoring/
  - monitoring_db.py        — SQLite 用永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py       — システム・データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書込みロジック
  - alert_manager.py        — LINE 通知クライアント
  - monitoring_engine.py    — 複数 Monitor を束ねる（単発/ループ）
  - streamlit_dashboard.py  — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py        — 発注・状態遷移の外向き API
  - reconciler.py           — 起動時のリコンシリエーション/ポジション差分照合
  - ... (broker_factory, execution_engine, order_repository 等)
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py      — セクター制限・レジーム乗数
- research/
  - factor_research.py      — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py  — 将来リターン計算、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py     — psutil を使った優先度 / CPU affinity ユーティリティ

運用上の注意
------------
- API キーやパスワードは .env に保存する際は慎重に（リポジトリにコミットしない）。
- OpenAI を使う機能は API キーが必要でコストが発生します。バッチサイズやリトライ設定はコード中の定数で調整できます。
- Paper Trading は本番 DB と完全に分離される設計ですが、設定ミスで接続先を間違えないよう注意してください（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV）。
- psutil によるプロセス/CPU 操作は権限のあるユーザーで実行してください。root 権限が必要な操作もあります（nice の低減など）。

ライセンス / 貢献
-----------------
- このリポジトリに含まれるコードのライセンスと貢献ルールは別途 LICENSE / CONTRIBUTING ファイルを参照してください（存在しない場合はリポジトリ管理者に問い合わせてください）。

補足
----
- ここに記載したコマンド例はプロジェクトルート（src が存在するルート）で実行してください。
- DuckDB / SQLite のスキーマや ETL の手順はデータ入手元（価格データ、財務データ、ニュース）に依存します。研究用や本番運用のデータ準備は別途スクリプトや運用手順書に従ってください。

必要であれば、README に .env.example のテンプレートやよく使う CLI コマンド一覧、systemd / supervisor 用のサービスユニット例、ローカルでの開発向けセットアップ（venv、pytest 設定）を追加で用意します。どの内容を優先して追加しますか？