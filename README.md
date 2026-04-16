# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。シグナル処理・ポートフォリオ構築・注文発行・監視・検証・研究用ユーティリティ群を含みます。本リポジトリはモジュール単位で使えるよう設計されており、実行エントリポイントやコマンドラインツール、Streamlit ダッシュボードを備えています。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（実行例）
- 環境変数一覧（主なもの）
- ディレクトリ構成（抜粋）
- 運用上の注意・補足

---

プロジェクト概要
- 日本株自動売買システムのコアライブラリ群（注文管理、リコンシリエーション、リスク管理、監視、ポートフォリオ構築、リサーチ、AI 補助機能など）。
- DuckDB を用いた時系列・財務データ分析、SQLite を用いた監視ログ・注文ログ保存。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価や市場レジーム判定の実装を含む（APIキーが必要）。

主な機能一覧
- Execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）。
  - ブローカークライアント抽象化（実運用時は kabuステーション、paper_trading 環境では MockBroker を使用）。
  - OrderManager / OrderRepository による注文状態遷移管理、Reconciler による再起動時の同期処理。
  - RiskManager による発注制限（設定により利用）。
- Monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor によるポーリング監視。
  - MonitoringEngine による監視ループ管理とアラート送信（LINE Push）。
  - MonitoringDB（SQLite）へ監視ログ永続化・マイグレーション対応。
  - Streamlit ダッシュボード（監視情報可視化）。
  - KillSwitch / kill.flag による外部停止（ExecutionEngine 停止）トリガー。
- Portfolio:
  - 候補選定、等金額・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元株丸め、aggregate cap）。
- Research:
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン計算、IC 計算、統計サマリ。
- AI:
  - ニュース NLP（news_nlp.score_news）: raw_news を集約して OpenAI に投げ、銘柄別センチメントを ai_scores テーブルへ保存。
  - 市場レジーム判定（regime_detector.score_regime）。
- ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。

---

セットアップ手順（ローカル開発 / 実行環境）
1. リポジトリをクローン
   - git clone <リポジトリ>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他のユーティリティも追加でインストール）

   （注）requirements.txt がある場合は:
   - pip install -r requirements.txt

4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）が見つかれば、.env/.env.local を自動で読み込みます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - サンプル（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

5. データディレクトリ
   - data/ 配下に DB や PID/flag ファイルが作られます。必要なら作成して権限を確認してください。

---

使い方（主要なコマンド例）

- 監視ループを起動（Monitoring）
  - デフォルトポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL で上書き可能。
  - 実行:
    - python -m kabusys.run_monitoring
    - 環境変数で間隔変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 実行時の挙動:
    - Settings から sqlite_path（monitoring DB）を読み、init_monitoring_db でテーブル作成（冪等）。
    - SystemMonitor.check_once をポーリング実行し、監視ログを書き込みます。
    - stop は data/stop_requested.flag を作成して行えます（スクリプトはこのフラグを検出してループを終了します）。

- Execution（注文エンジン）を起動
  - Paper trading と本番は DB を分離（KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用）。
  - 実行:
    - python -m kabusys.run_execution
    - Paper trading モードで起動:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag（実行前に作成されている場合は起動せず終了）
    - 起動中に同じフラグを作成すると実行エンジンを停止します。
  - 実行時は ExecutionEngine が別スレッドで run_session を実行します。PID ファイル（data/execution.pid）などを利用。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring DB を読み取り専用で開きます（存在しない場合はエラーメッセージ）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH でパスを指定

- AI 機能（ニュース NLP / レジーム判定）
  - 両機能とも OpenAI API キー（OPENAI_API_KEY）を必要とします（引数で渡すことも可能）。
  - プログラムから呼ぶ例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - score_news は DuckDB 接続（raw_news, news_symbols, ai_scores 等）を受け取り、銘柄別スコアを ai_scores テーブルへ書き込みます。
  - API 呼び出しはレート制限・5xx 等に対してエクスポネンシャルバックオフでリトライします。失敗時はフェイルセーフで継続します（未取得コードは書き込まれません）。

---

環境変数（主要なもの）
- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
  - paper_trading の場合、Execution は paper_sqlite_path（data/paper_trading.db など）を使い本番 DB と分離される。
- MONITOR_POLL_INTERVAL (default: 60)
  - run_monitoring のポーリング間隔（秒）。1 未満の値は無効扱いでデフォルトにフォールバック。
- SQLITE_PATH (default: data/monitoring.db)
  - Monitoring DB のパス（SQLite）。
- DUCKDB_PATH (default: data/kabusys.duckdb)
  - DuckDB ファイルのパス（研究・ファクター計算・raw データ）。
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - Paper Trading 用の SQLite DB（本番と分離）。
- PAPER_FILL_MODE (default: instant)
  - paper_trading 時の MockBroker の約定モード: instant | partial | never | reject
- OPENAI_API_KEY
  - OpenAI API を利用する機能で必要（news_nlp, regime_detector 等）。
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 外部 API（J-Quants、kabuステーション）連携のためのトークン / パスワード。
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - AlertManager（LINE push）を使う場合に必要。未設定だと送信せずログに記録されます。
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等
  - PID / kill flag のパスや挙動（詳細は Settings を参照）。

注: .env 自動読み込み
- プロジェクトルートを自動検出して .env を読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py        — psutil を用いた優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite テーブル作成・監視 DB ラッパー
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
    - ... (broker_factory, execution_engine, order_repository 等)
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
  - data/                        — (実行時に生成されることが多い: DB, pid, flag)

（上記は本リポジトリの主要ファイルのみ抜粋）

---

運用上の注意・補足
- DB マイグレーション:
  - init_monitoring_db() は実行時に不足カラムを検出して追加する簡易マイグレーションを行います（例: trade_logs に latency_ms を追加）。
- 権限:
  - set_process_priority はプラットフォーム依存で、優先度設定や CPU affinity の変更に管理者権限が必要になる場合があります。失敗すると警告ログを出してスキップします。
- フラグ制御:
  - 実行停止はプロジェクト内の data/stop_requested.flag を作成することで行います。KillSwitch は data/kill.flag を書き込み、ExecutionEngine を停止させるトリガーとして機能します。
- AI API 使用時の注意:
  - OpenAI API のレスポンスは妥当性検証を行いますが、API 利用にはコスト・レート制限があります。APIキーの管理および利用量の監視を行ってください。
- テスト:
  - 各モジュールは可能な限り純粋関数 / 副作用の少ない設計を目指しています。AI 呼び出し等は外部呼び出し部を差し替えてテスト可能です（モック推奨）。

---

必要に応じて README に実行コマンド例、.env.example、requirements.txt を追加してください。リポジトリの運用方法やデプロイ手順（systemd などでのサービス化）、バックアップや監視の運用ドキュメントは別途用意することを推奨します。

必要であれば、README 内に「.env.example のテンプレート」や「よくあるトラブルシューティング」を追加で作成します。どの情報を追記しましょうか？