KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買およびリサーチ基盤ライブラリです。  
主な目的は以下です。

- 戦略に基づくポートフォリオ構築（銘柄選定、重み付け、株数決定）
- 実行エンジン（注文管理、ブローカー同期、リコンシリエーション）
- 監視・アラート（システム状態、注文滞留、リスク監視、Kill Switch）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースのセンチメント集計、マーケットレジーム判定）
- Paper Trading 検証とレポート出力
- Streamlit ベースの監視ダッシュボード

主な機能一覧
-------------
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - セクター制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes） — リスク制限、単元丸め、aggregate cap 対応
- 実行関連
  - OrderManager、ExecutionEngine（起動スクリプト: run_execution.py）
  - Reconciler：再起動時の注文・ポジション突合
  - BrokerClientFactory による本番 / PaperTrading 切替（KABUSYS_ENV）
- 監視
  - SystemMonitor（プロセス生存、CPU/メモリ/ディスク、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション数上限）
  - KillSwitch（条件に応じて data/kill.flag を書き込み、実行エンジンに停止指示）
  - AlertManager（LINE Push を使った通知）
  - MonitoringEngine（複数モニタの統合運用）
  - run_monitoring.py による常駐ポーリング起動
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- リサーチ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC 計測、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM でスコア化して ai_scores テーブルへ書込
  - regime_detector.score_regime: ET F MA とマクロニュースで日次レジーム判定
- ツール
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. リポジトリを取得、仮想環境を作成:
   - python >= 3.9 を想定
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存ライブラリをインストール（requirements.txt がなければ最低限）:
   - pip install duckdb psutil openai requests streamlit
   - プロジェクトで別途 requirements を用意している場合はそれを使ってください。

3. 環境変数 / .env
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
   - .env のパースは bash ライクな形式をサポートします。詳細は kabusys.config を参照。

4. データディレクトリ
   - デフォルトでは data/ 以下に DB や PID/flag ファイルが作られます。必要に応じてディレクトリを作成してください。
   - 実行スクリプトは停止用フラグ file を監視します（stop_requested.flag, kill.flag）。

初期化
- monitoring DB（SQLite）は起動時に自動で init_monitoring_db を走らせます。明示的な初期化は不要です。

使い方（主要なコマンド）
----------------------

1) 監視ループ（Monitoring）
- 実行:
  - python src/kabusys/run_monitoring.py
  - もしくはパッケージ形式で: python -m kabusys.run_monitoring
- オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。0 や負の値は無視されデフォルトが使われます。
  - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path (Settings.sqlite_path) を使用します（監視専用の DB を使う設計）。
- 停止:
  - data/stop_requested.flag を作成するとループを終了します（起動スクリプトが検知）。

2) 実行エンジン（Execution）
- 実行:
  - python src/kabusys/run_execution.py
  - または: python -m kabusys.run_execution
- 振る舞い:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録します。本番 DB と分離されます。
  - 起動時に data/execution.pid を使ってプロセス生存を管理します。停止は data/stop_requested.flag や kill.flag を利用します。
- 停止:
  - data/stop_requested.flag を置くとエンジンを停止します。KillSwitch による data/kill.flag が書かれると、異常検出により停止シグナルを送出します。

3) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）
- 出力: 標準出力に検証結果と PASS/FAIL 判定（稼働率、成功率、レイテンシ等）

4) Streamlit ダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視用 SQLite を読み取り専用で開き、ダッシュボードを表示します。
  - MonitoringEngine が書き込み中でも可読モードで開ける URI を利用します。

5) AI 機能（OpenAI）
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別スコアを生成して ai_scores テーブルに書き込む。
  - api_key を省略すると環境変数 OPENAI_API_KEY を参照。
  - 複数の保護措置（トークン制限、文字数上限、リトライ、レスポンス検証）が組み込まれています。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 1321 ETF の MA200 乖離とマクロニュースの LLM センチメントを組み合わせて日次の market_regime を書き込みます。
- 注意: OPENAI_API_KEY が必要。API 呼び出し失敗時は安全側のデフォルトで継続するよう設計されています（例: macro_sentiment=0.0）。

ファイル / ディレクトリ構成（主要）
---------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義、バージョン
- config.py
  - 環境変数 / .env 読み込みと Settings クラス
- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替、PID 管理）
- tools/
  - paper_verification_report.py
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数決定、スケーリング、単元処理
  - risk_adjustment.py — セクター上限、レジーム乗数
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化と CRUD（MonitoringDB クラス）
  - system_monitor.py — CPU/メモリ/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留、約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE push 通知
  - monitoring_engine.py — 各監視の統合
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文状態管理 API
  - reconciler.py — 起動時リコンシリエーション
  - （その他実装ファイル群: broker_factory, execution_engine, order_repository 等）
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- ai/
  - news_nlp.py — ニュースセンチメントスコア算出（OpenAI）
  - regime_detector.py — レジーム判定（OpenAI と価格指標の合成）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/
  - （実行時に作られる SQLite / DuckDB / pid / flag ファイル群: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag, data/stop_requested.flag）

注意点 / 運用上のヒント
---------------------
- 環境分離:
  - Paper Trading 時は paper_sqlite_path を使って本番 DB と分離します（KABUSYS_ENV=paper_trading）。
  - ただし、Monitoring は常に Settings.sqlite_path を使用する設計になっています（監視用 DB は本番 DB を想定）。
- フラグによる終了:
  - run_monitoring/run_execution は data/stop_requested.flag の検出で終了します。KillSwitch は data/kill.flag を書き込み ExecutionEngine 停止を誘発します。
- 優先度設定:
  - 起動スクリプトは最初に set_process_priority("high") を試みます。失敗しても警告を出して続行します（権限依存）。
- DB マイグレーション:
  - init_monitoring_db は既存 DB に対して冪等にテーブルやカラム追加（例: latency_ms, peak_value）を行います。
- LLM 統合:
  - OpenAI 呼び出しはリトライ / クリップ / バリデーションを実装していますが、API 費用・レート制限に注意してください。
- テスト / CI:
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。ユニットテスト時に有用です。

実例：よく使うコマンド
--------------------
- 監視開始:
  - KABUSYS_ENV=development python -m kabusys.run_monitoring
- 実行エンジン（Paper）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 開発
----------------
- コードの各モジュールはドキュメンテーションコメント（docstring）を豊富に含んでいます。内部設計や制約（例: ルックアヘッドバイアス回避、DuckDB の executemany の注意点など）も記載されていますので、実装の拡張や改修時は該当モジュールの docstring を参照してください。
- 外部 API キー（OpenAI など）は環境変数で管理し、不要な公開を避けてください。

ライセンス
---------
（このリポジトリにライセンスファイルがあれば追記してください）

以上。必要があれば README に「セットアップの具体的な requirements.txt」や「実行例のスクリーンショット」「運用手順（デーモン化、systemd ユニット例）」などを追加します。どの情報が欲しいか教えてください。