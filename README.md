KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・調査・監視を目的とした小規模なシステムです。本リポジトリには以下の主要コンポーネントが含まれます。

- 注文発行・実行エンジン（ExecutionEngine / OrderManager 等）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築ロジック（candidate 選定・重み付け・サイズ計算）
- リサーチ用ファクター計算（momentum / volatility / value 等）
- AI 周り（ニュース NLP によるセンチメント、レジーム判定）
- 各種ユーティリティ（プロセス優先度設定・DB 初期化など）
- 運用用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / paper_trading を環境変数 KABUSYS_ENV により切替
  - paper_trading では MockBroker を使用し DB を分離（data/paper_trading.db）
  - プロセス優先度設定 / PID 管理 / 停止フラグ監視
- 監視プロセス（run_monitoring.py / MonitoringEngine）
  - サーバーの CPU / メモリ / ディスク監視、Execution プロセス監視
  - 注文滞留・約定異常・ドローダウン等の監視とリスクロギング
  - kill.flag による外部停止シグナルの発行
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - 運用検証用に稼働率・注文成功率・レイテンシなどを集計しコンソール出力
- Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
  - 監視 DB を読み取りダッシュボード表示（Portfolio / Orders / System 等）
- AI モジュール
  - news_nlp.score_news: OpenAI でニュースを銘柄ごとにセンチメント評価し ai_scores に書込
  - regime_detector.score_regime: ETF MA とマクロニュースを組合せて市場レジーム判定
- リサーチモジュール
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（lot 単位・リスクベース等）

セットアップ
------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. Python 環境（推奨: venv）を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（代表的な依存）:
   - pip install duckdb psutil requests openai streamlit
   実プロジェクトでは requirements.txt を用意している想定です。適宜追加してください。

4. データディレクトリの作成:
   - mkdir -p data

環境変数 / .env
----------------
設定は環境変数、またはリポジトリルートの .env / .env.local に記述して読み込みます（config.py により自動読み込み。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（抜粋）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: Kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant / partial / never / reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用）

重要なファイルパス（デフォルト）
- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — paper trading 用 SQLite（分離）
- data/kabusys.duckdb — DuckDB データ
- data/execution.pid — ExecutionEngine の PID 管理（Settings.pid_file_path）
- data/kill.flag — KillSwitch による停止フラグ（Settings.kill_flag_path）
- data/stop_requested.flag — run_execution / run_monitoring の停止制御（スクリプトが参照）

使い方（代表コマンド）
--------------------
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL を設定するとポーリング間隔を上書き可能（秒、デフォルト 60）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を利用し paper_trading DB に記録します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI / レジーム判定・ニューススコアリング（プログラムから呼び出す）
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...) を呼び出して ai_scores テーブルに書込
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

運用上のポイント
----------------
- paper_trading 環境は本番 DB から完全に分離されます（Settings.is_paper により paper_sqlite_path を使用）。
- 実行エンジン・監視プロセスは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足等で失敗する場合は警告が出ますが処理は継続します。
- 外部からの停止は data/stop_requested.flag（スクリプトが参照）や data/kill.flag（KillSwitch）を書き込むことで行います。KillSwitch は条件により自動的に kill.flag を作成します。
- config.py は .env の自動読み込みを行います。CI / テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使う機能（news_nlp / regime_detector）は API キーが必要です。失敗時はフェイルセーフで継続する設計の箇所がありますが、期待する結果は得られません。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__）
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート（CLI）
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化 / DB API（MonitoringDB）
    - system_monitor.py        — CPU/メモリ/ディスク / データ鮮度監視
    - trade_monitor.py         — 注文滞留 / 約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション制限監視
    - kill_switch.py           — kill.flag の作成・管理
    - alert_manager.py         — LINE プッシュ通知ラッパー
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py         — OrderManager（発注・状態管理）
    - order_repository.py      — Orders DB 操作（省略されているが存在想定）
    - reconciler.py            — 再起動時のリコンシリエーション
    - ...                      — BrokerFactory 等（コードベースによる）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・資金割当ロジック
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI 呼出・書込）
    - regime_detector.py       — マーケットレジーム判定（ETF MA + LLM）
  - data/                      — デフォルト DB / PID / flag を置く想定ディレクトリ（作成しておく）

実装メモ / 注意点
-----------------
- DuckDB / SQLite を併用しています。リサーチ系の集計は DuckDB に、運用ログは SQLite（monitoring.db / paper_trading.db）に保存します。
- 各種 DB 初期化は init_monitoring_db() により冪等に行われます（マイグレーション処理も一部含む）。
- AI 周りは OpenAI SDK（OpenAI クライアント）を用いており、API 制限・エラーに対してリトライロジックやフェイルセーフを備えていますが、コストやレイテンシに注意してください。
- 本リポジトリの設定呼び出しは Settings クラス経由で行うことを推奨します（config.settings インスタンス利用可）。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py に定義されています（例: 0.1.0）。ライセンス情報や .env.example が別途ある想定です。実運用前に .env.example を参照して必須環境変数を設定してください。

さらに知りたい点 / カスタム手順
-----------------------------
- CI 用の自動テスト、依存の pinned requirements、コンテナ化（Dockerfile）や systemd ユニットファイルのサンプルなどが必要であれば追記できます。
- broker 実装（本番接続）や OrderRepository の DB スキーマ詳細、ExecutionEngine の run_session 実装など追加説明が必要であればその箇所に合わせて README を拡張します。

必要であれば README の英語版、または運用手順（systemd / Docker / Kubernetes）向けの手順を作成します。どの情報を追加しますか？