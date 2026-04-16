KabuSys — 自動売買 / リサーチ基盤
================================

このリポジトリは日本株向けの自動売買・リサーチ基盤「KabuSys」の実装断片です。
トレード実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、
リサーチ（ファクター計算 / 特徴量探索）、AI を使ったニューススコアリング等の
主要コンポーネントを含んでいます。

主な特徴
--------
- Execution
  - ExecutionEngine による発注・リスク管理・注文状態管理
  - paper_trading モード（モックブローカー、完全に別DBに記録）
  - 起動時のリコンシリエーション（再起動後の自動復旧）
- Monitoring
  - System / Trade / Risk 各モニタのポーリング監視
  - SQLite に永続化される監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch によるフラグファイル停止、LINE への通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio construction（純粋関数）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン / IC / 統計サマリ等
- AI 支援
  - OpenAI を使ったニュースのセンチメントスコアリング（ai.news_nlp）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定（ai.regime_detector）

セットアップ手順
----------------

前提
- Python 3.10 以上推奨（型注釈に Python 3.10 の構文を使用）
- sqlite3 が利用可能
- 必要な外部ライブラリ: duckdb, psutil, openai, requests, streamlit

例: 仮想環境を作成して依存パッケージをインストール
- venv 作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
- 必要パッケージをインストール（例）
  - pip install duckdb psutil openai requests streamlit

環境変数 / .env
- 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- 主要な環境変数:
  - KABUSYS_ENV: 起動環境（development, paper_trading, live）。デフォルト: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant, partial, never, reject。デフォルト: instant）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用。デフォルト 60）

ファイルおよびデフォルトデータ位置
- データ・フラグ類は data/ 配下を使用:
  - data/monitoring.db（監視ログ）
  - data/paper_trading.db（paper_trading 用）
  - data/kabusys.duckdb（DuckDB）
  - data/execution.pid（ExecutionEngine の PID 保存）
  - data/stop_requested.flag（run_execution/run_monitoring の停止判定に利用）
  - data/kill.flag（KillSwitch が書く停止指示フラグ）

使い方（主要スクリプト）
-----------------------

1) 監視ループ起動（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 動作:
  - process priority を "high" に設定し（可能なら）、監視 DB を初期化して SystemMonitor のポーリングを行います。
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書き可能（デフォルト 60）。
  - 停止: プロジェクトルート/data/stop_requested.flag が存在するとループを抜けて終了します。
- 実行例:
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

2) 実行エンジン起動（Execution）
- スクリプト: src/kabusys/run_execution.py
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。
  - プロセス優先度を設定し、OrderManager / RiskManager / ExecutionEngine を組み立てて実行します。ExecutionEngine は別スレッドで run_session を実行。
  - 停止: data/stop_requested.flag を検出すると engine.stop() を呼び待機します。
  - PID ファイル path は Settings.pid_file_path（デフォルト data/execution.pid）。
- 実行例:
  - production 例（本番接続設定済み）: KABUSYS_ENV=live python -m kabusys.run_execution
  - paper_trading 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3) Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリ＋ PASS/FAIL 判定

4) Streamlit ダッシュボード（監視画面）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: 実行中の monitoring.db を読み取り専用で開いてダッシュボード表示

5) AI（ニューススコア／レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None) — raw_news を集約して OpenAI でセンチメントを計算し ai_scores テーブルに書き込む
- regime_detector.score_regime(conn, target_date, api_key=None) — ETF 1321 の ma200 乖離 + マクロニュースでレジーム判定を行い market_regime テーブルに書き込む
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

監視 DB（SQLite）スキーマ（要点）
--------------------------------
init_monitoring_db により次のテーブルが作成されます（冪等）:
- system_status: cpu/memory/disk/process_ok, recorded_at
- trade_logs: 発注イベントログ（latency_ms カラム含む）
- positions: 現在のポジション
- risk_logs: リスクイベント（重複抑止機能付）
- dashboard: ダッシュボード集計（id=1 の単一行）

KillSwitch / 停止フロー
----------------------
- RiskMonitor が DRAWDOWN_ALERT / POSITION_LIMIT を検出すると KillSwitch が設定され、data/kill.flag を書き込みます（ExecutionEngine は起動時に kill_flag_clear_on_start 設定で消去可）。
- 外部から確実に停止させたい場合は data/stop_requested.flag を作成すると run_execution / run_monitoring のメインループが検知して終了します。

Tips / 注意点
-------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。CWD に依存せずパッケージ配布後も動作するよう設計されています。
- Settings の検証:
  - KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。
  - PAPER_FILL_MODE は instant / partial / never / reject のいずれか。
  - 一部キーは必須（_require を通してチェックされます）。
- process priority / cpu affinity 設定は psutil を使用。権限不足や未対応 OS の場合は警告を出してスキップします。
- DuckDB / OpenAI 周りはネットワーク・API エラーを考慮してリトライ設計が組み込まれていますが、API キーや料金には注意してください。
- Paper Trading モードは本番データベースと完全分離されます。必ず KABUSYS_ENV=paper_trading を指定してください。

主要ディレクトリ構成
--------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings 管理（.env 自動ロード含む）
- run_monitoring.py            — MonitoringEngine ポーリング起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite 永続化層（init / MonitoringDB クラス）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 Execution 系モジュールはこの配下に配置される想定)
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
- data/ (プロジェクトルートに作成される想定)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag

開発・運用時のワークフロー例
----------------------------
- ローカル検証（価格データ・DuckDB がある前提）:
  - KABUSYS_ENV=development python -m kabusys.run_monitoring
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Streamlit で監視: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper trading の結果確認:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

ライセンス・貢献
----------------
- 本 README にはライセンス情報は含めていません。実際の配布時は LICENSE を追加してください。
- 貢献は PR ベースで受け付ける想定です。ユニットテスト・型チェック（mypy 等）を整備すると安全です。

補足
----
この README は提供されたコードベースのソースコメント・設計ノートに基づいて作成しています。実運用の前に環境変数、API キー、DB バックアップ、監視・アラートの設定を十分に確認してください。必要であれば README にサンプル .env.example を追加することをお勧めします。