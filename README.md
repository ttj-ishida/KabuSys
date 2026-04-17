KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を目的とした小規模なフレームワークです。
主な機能は以下のとおりです。

- 注文実行エンジン（ExecutionEngine）と OrderManager / Reconciler による起動時リコンシリエーション
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と通知（LINE）
- Paper Trading 用の完全分離された SQLite DB と MockBrokerClient のサポート
- DuckDB を使ったファクタ計算・リサーチ（momentum / volatility / value 等）
- ニュースを LLM（OpenAI）でセンチメント解析し銘柄別スコアを書き込む AI モジュール
- Paper Trading の検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

このリポジトリは「戦略の算出（純粋関数群）」「実行ロジック」「監視」「AI ユーティリティ」「リサーチ」の各要素を分離して実装しています。

主な機能一覧
--------------
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - OrderManager / OrderRepository / Reconciler による発注・同期・復旧
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い data/paper_trading.db に記録
- Monitoring
  - SystemMonitor（プロセス生存 / CPU/メモリ/ディスク / データ鮮度）
  - TradeMonitor（滞留注文 / 約定異常価格）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件により data/kill.flag を書き込んで Execution を停止）
  - AlertManager（LINE push による通知）
  - MonitoringEngine / run_monitoring スクリプト
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio construction
  - 候補選定、等金額/スコア加重、リスク調整、ポジションサイジング（純粋関数群）
- Research / AI
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - ニュースを OpenAI でスコアリングして ai_scores テーブルへ書き込み（src/kabusys/ai/news_nlp.py）
  - 市場レジーム判定モジュール（regime_detector）
- ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）

セットアップ手順
-----------------
前提
- Python 3.9+（プロジェクトの実際の要件に合わせて調整）
- 以下の主な外部ライブラリ（requirements.txt を用意してください）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit

インストール例（仮想環境推奨）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

3. リポジトリルートに data ディレクトリを作成（必要に応じて）
   - mkdir -p data

環境変数 / .env
- このコードベースは .env / .env.local を自動でプロジェクトルートから読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数
  - KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各外部 API 用トークン（必須な場合）
  - OPENAI_API_KEY: OpenAI を使うモジュールで必要
  - PAPER_FILL_MODE: Paper Trading の成行/約定挙動（instant, partial, never, reject）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知をスキップ）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（実行例）
-----------------

1) 監視ループを起動（本番監視）
- デフォルトでは MONITOR_POLL_INTERVAL=60 秒
- 簡易起動:
  - python -m kabusys.run_monitoring
- 環境変数で間隔上書き:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

注意: run_monitoring は Settings に従い監視用 DB（SQLITE_PATH）を使用します。停止にはプロジェクトルート data/stop_requested.flag を作成するか Ctrl+C。

2) 実行エンジンを起動（ExecutionEngine）
- 本番/開発:
  - python -m kabusys.run_execution
- Paper Trading で実行する場合:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Paper Trading では settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

停止制御:
- run_execution/run_monitoring は data/stop_requested.flag の存在を検知すると安全に終了します。
- KillSwitch（監視側）が条件を満たし実行停止を要求すると data/kill.flag を書き込み、ExecutionEngine 起動時にこれを検出して停止します。

3) Streamlit ダッシュボード（監視情報閲覧）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB を read-only で開いて表示します。MonitoringEngine が定期的にデータを書き込みます。

4) Paper Trading 検証レポート
- 単発実行:
  - python -m kabusys.tools.paper_verification_report
- 日付指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パス指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

AI / OpenAI 関連
- news_nlp.score_news や regime_detector.score_regime は OPENAI_API_KEY を必要とします。環境変数または関数引数で指定してください。
- OpenAI 呼び出しはリトライやフェイルセーフの保護が入っていますが、API キー未設定だと例外が発生します。

監視・運用に関する注意点
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番の monitoring DB）を使います（設計上の意図）。
- run_execution は KABUSYS_ENV=paper_trading のときのみ paper_sqlite_path を使用します（本番 DB と完全分離）。
- PID ファイル（デフォルト data/execution.pid）により実行プロセスの生存チェックを行います。PID が stale の場合は自動で削除しアラートログを記録します。
- kill.flag（Settings.kill_flag_path）を KillSwitch が書き込むと ExecutionEngine を停止するためのシグナルになります（冪等）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / .env ロードと Settings
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                  — ニュースを OpenAI でセンチメント化して ai_scores に書き込む
  - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py             — SQLite テーブル初期化・永続化層
  - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py             — 注文滞留・約定価格異常検出
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みユーティリティ
  - alert_manager.py             — LINE push 通知ラッパー
  - monitoring_engine.py         — 各 Monitor を束ねるループ
  - streamlit_dashboard.py       — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity 管理
- data/                          — 実行時に使用するフラグ・DB ファイル保存先（リポジトリに含めないこと）

（注）上記は本リポジトリに含まれる主要ファイルの抜粋です。実際のプロジェクトでは追加のモジュール（broker API, order_repository, data pipeline 等）が存在します。

開発者向けメモ
----------------
- .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストで環境読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- SQLite / DuckDB のスキーマは init_monitoring_db で冪等に作成されます。DuckDB 側はデータ投入（prices_daily, raw_news 等）が必要です。
- process_priority.set_process_priority により起動直後に優先度を上げる処理があります。権限不足で失敗した場合はログに警告が出ますが継続します。

トラブルシューティング
---------------------
- DB が開けない / テーブルがない:
  - run_execution / run_monitoring は init_monitoring_db を呼びますが、DuckDB 側の prices_daily などのテーブルは外部投入が必要です。
- OpenAI 関連でエラーが出る:
  - OPENAI_API_KEY の設定とネットワーク接続を確認してください。API エラーは内部でリトライ・フェイルセーフが入ります。
- LINE 通知が送れない:
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を確認してください。設定が空の場合は送信をスキップします。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートに LICENSE があればそちらを参照してください（本 README には含めていません）。

お問い合わせ・貢献
-----------------
バグ報告・機能提案があれば Issue を立ててください。開発に参加する場合は、既存の設計方針（外部 API への依存最小化、ルックアヘッドバイアス回避、フェイルセーフ重視）に沿って PR をお送りください。

おわりに
--------
この README はコードベースの主要機能と運用方法をまとめたものです。実行前に .env（または環境変数）を適切に設定し、必要な DB と外部 API の準備を行ってください。