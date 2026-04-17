KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコードベースです。売買実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）、ツール群を含みます。README はプロジェクトの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
--------------
KabuSys は以下の主要機能を持つモジュール化された自動売買基盤です。

- Execution Engine：ブローカー経由での注文送信・管理、リコンシリエーション（再起動後の同期）を行う。
- Monitoring：システム稼働状態、注文滞留、ドローダウンなどを定期チェックしログ/アラート出力、必要なら Execution を停止する（Kill Switch）。
- Portfolio Construction：シグナル選定、重み計算、ポジションサイズ算出、セクター上限やレジーム乗数の適用。
- Research：DuckDB 上の時系列データからファクター（モメンタム、ボラティリティ、バリュー）を計算、特徴量探索用ユーティリティ。
- AI：ニュースの NLP（OpenAI を利用した銘柄ごとのセンチメントスコア）や市場レジーム判定（MA + マクロセンチメント）。
- Tools：Paper Trading の検証レポート作成等のユーティリティスクリプト。
- ユーティリティ：プロセス優先度設定、環境変数読み込みなど。

主な機能一覧
-------------
- 環境依存設定（Settings）と .env 自動読み込み（.env, .env.local）  
- 本番 / Paper Trading の DB 分離（paper_trading 環境では data/paper_trading.db を使用）  
- ExecutionEngine の起動・停止制御（PID ファイル / stop フラグファイル / kill.flag）  
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE Push）  
- Streamlit による監視ダッシュボード（読み取り専用）  
- DuckDB を使ったリサーチ・ファクター算出（prices_daily / raw_financials 参照）  
- OpenAI を利用したニューススコアリング & レジーム判定（gpt-4o-mini 想定）  
- Paper Trading 向け検証レポート（期間指定で各種指標を出力）  
- ポートフォリオ構築（候補選定、等配分・スコア加重、リスクベース、セクターキャップ、ポジション決定と単元丸め）

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の | 型ヒントを使用）
- SQLite は標準ライブラリで利用可能
- システムにより追加ライブラリが必要（下記参照）

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（venv 推奨）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートに .env（と任意で .env.local）を置くと自動読み込みされます（CWD に依存せず、パッケージ配置後も探索されます）。
- 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数とデフォルト：
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: （必須）
  - KABU_API_PASSWORD: （必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
  - SQLITE_PATH: data/monitoring.db（Monitoring 用 SQLite、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の DB）
  - DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル）
  - PID_FILE_PATH, KILL_FLAG_PATH, など（Settings クラス参照）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定動作）
- .env.example がある場合はそれをコピーして必要な値を埋めてください。

初期データ / ディレクトリ
- data ディレクトリ（DB、PID、フラグファイルを格納）を作成しておくと便利:
  - mkdir -p data

使い方
------
1) 実行エンジン（ExecutionEngine）起動
- 本番（または環境に応じた設定）でエンジンを起動:
  - python -m kabusys.run_execution
- Paper Trading モードで起動するには環境変数を設定:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - Paper Trading の場合、専用の SQLite（PAPER_TRADING_SQLITE_PATH）に取引ログが記録され、本番 DB と分離されます。

起動時の挙動:
- プロセス優先度を high に設定し、PID ファイル（data/execution.pid 等）を使用。
- 起動前に data/stop_requested.flag が存在すると起動をスキップします。
- 実行中に stop フラグ（data/stop_requested.flag）を置くと安全に停止します。
- Risk Manager の監視結果に応じて KillSwitch が data/kill.flag を書き込むと ExecutionEngine 側で停止を検出できます。

2) 監視（Monitoring）起動
- 監視ループを起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
  - export MONITOR_POLL_INTERVAL=30  # 秒
- run_monitoring は環境にかかわらず production（本番）用の sqlite_path を使用して monitoring DB（data/monitoring.db）へ書き込みます。
- 監視ループは data/stop_requested.flag の検出で終了します。

3) Streamlit ダッシュボード（監視画面）
- 起動方法（プロジェクトルートから）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で監視 DB を参照し、ダッシュボード・ポジション・注文・最新システムステータス・リスクログを表示します。

4) Paper Trading 検証レポート
- 単発レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを直接指定する場合:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI 機能
- ニュース NLP（銘柄スコア）/ レジーム判定は OpenAI API を使用します。OPENAI_API_KEY を設定してください。
- 関数 API からは kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime を呼ぶことで処理・DB 書き込みが行われます。

運用・停止関連
- stop（安全停止）: data/stop_requested.flag を作成すると run_execution/run_monitoring のループは検出して終了します。
- KillSwitch（自動停止）: RiskMonitor が基準を満たすと KillSwitch が data/kill.flag を書き込む → 手動で確認・解除してください。KillSwitch.clear() を呼ぶかファイルを削除することで解除できます。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に kill.flag を自動クリアできます（Settings.kill_flag_clear_on_start）。

ディレクトリ構成
----------------
（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード、Settings）
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - execution_engine.py   — 実行エンジン（起動・セッション管理）（別ファイル群あり）
    - broker_factory.py     — ブローカークライアントの生成
    - order_manager.py      — 注文状態遷移・送信の上位 API
    - order_repository.py   — Orders DB 操作
    - reconciler.py         — 再起動時のリコンシリエーション
    - risk_manager.py       — 注文送信制限等のリスク管理（設定参照）
    - ...（その他実装ファイル）
  - monitoring/
    - monitoring_db.py      — SQLite 監視 DB スキーマ & 永続化クラス
    - system_monitor.py     — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py      — 注文滞留・約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - alert_manager.py      — LINE 通知送信（クールダウン管理含む）
    - monitoring_engine.py  — 各 monitor を束ねる実行ループ
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数算出・単元丸め・資金スケーリング
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — モメンタム / ボラ / バリュー の計算（DuckDB）
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py    — ETF(1321) MA200 とマクロセンチメントを合成してレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

開発者向けメモ / 注意点
---------------------
- Settings クラスは多くのデフォルトと検証ロジックを持っています。環境変数の値が不正な場合は ValueError を投げます。KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかにしてください。
- .env のパーサはシンプルながらクォートやエスケープ、インラインコメント対応等が組み込まれています。OS の環境変数は優先され、.env.local は .env を上書きできます。
- DuckDB を利用しているため、prices_daily / raw_financials / raw_news 等のテーブルを事前に用意しておく必要があります（リサーチ・AI 機能を使う場合）。
- OpenAI API 呼び出しはリトライ・バックオフを備えていますが、API 利用料やレート制限に注意してください。
- MonitoringDB は schema migration を軽微にサポートします（列追加等の簡単なマイグレーション処理を含む）。
- テスト時は外部 API 呼び出し関数（OpenAI など）をモックすることを推奨します（コード内にテスト向け差し替えポイントあり）。

よく使うコマンド（まとめ）
------------------------
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- 環境変数を一時設定して起動例（UNIX 系）:
  - KABUSYS_ENV=paper_trading OPENAI_API_KEY=xxx python -m kabusys.run_execution

ライセンス / 貢献
-----------------
（この README には含まれていません。必要に応じて LICENSE ファイルや貢献ガイドをプロジェクトルートに追加してください。）

補足
----
ここに示した操作や環境変数はソース内の docstring / Settings クラス / 各モジュールのコメントに基づく要約です。実運用前に必ず .env の内容、DB バックアップ、ブローカー API の接続確認を行ってください。質問や特定ファイルの詳細な説明が必要であれば教えてください。