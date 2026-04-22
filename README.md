KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／研究／監視を行うための Python パッケージです。本リポジトリには以下の主要機能を持つモジュール群が含まれます。

- ExecutionEngine（注文発行・リスク管理）
- Monitoring（システム稼働・注文・リスク監視、Kill Switch）
- Portfolio construction（候補選定、重み算出、ポジションサイジング）
- Research（ファクター計算・特徴量探索）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）

主な設計方針
- 本番／ペーパートレードを環境変数 KABUSYS_ENV で切替可能（development / paper_trading / live）。
- .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可）。
- DuckDB（分析用）と SQLite（監視・ペーパートレード用）を併用。
- OpenAI API（ニュース NLP 等）を利用する機能あり（APIキーは OPENAI_API_KEY）。

機能一覧
--------
- execution
  - ExecutionEngine：ブローカークライアントを使用した発注ループ（paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録）
  - RiskManager / OrderManager / Reconciler 等
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・Execution プロセスの監視
  - TradeMonitor：発注ログの監視（滞留注文、約定異常 等）
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch：条件を満たすと data/kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine：複数 Monitor を束ねたポーリング実行
- portfolio
  - 候補選定（select_candidates）、重み計算（等重／スコア重み）、ポジションサイズ算出（単元丸め・リスクベース）、セクター上限適用、レジーム乗数
- research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- ai
  - news_nlp.score_news：ニュース記事を LLM に送り銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime：ETF とマクロニュースを組合せて日次の市場レジームを判定
- tools
  - paper_verification_report：ペーパートレード DB から検証レポートを生成
- utils
  - logging_setup：統一ログ設定（stdout + 日次ローテーションファイル）
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ
- CLI
  - config_setup：対話式 .env 作成ウィザード
  - validate_config：起動前設定検証ツール

セットアップ手順
----------------

1. Python 環境準備
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化してください。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 本リポジトリに requirements.txt がある前提で:
     - pip install -r requirements.txt
   - 主要依存（例）
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config の YAML 検証を行う場合）
   - もし requirements.txt がない場合は上記パッケージを個別に pip install してください。

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使うオプション（デフォルトが使えるものもあります）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG / INFO / …)
     - OPENAI_API_KEY（AI 機能を使う場合）

   注意:
   - config.py はプロジェクトルートにある .env / .env.local を自動読み込みします（自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

4. DB 初期化
   - monitoring 用 SQLite は初回起動時に必要テーブルを作成します（init_monitoring_db を呼び出します）。
   - DuckDB はスキーマ作成スクリプト等に応じて適宜テーブルを準備してください（prices_daily / raw_financials / raw_news 等を利用するリサーチ／AI モジュールが想定）。

使い方（実行例）
----------------

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする（CI 等）: python -m kabusys.validate_config --strict

- .env の対話式作成
  - python -m kabusys.config_setup

- ExecutionEngine を起動
  - 本番 or デフォルト: python -m kabusys.run_execution
  - paper_trading モードで起動するには .env で KABUSYS_ENV=paper_trading を設定
    - paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録されます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）を設定
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring はプロセス優先度を高く設定し、監視 DB（SQLite）と DuckDB に接続します。

- 停止方法
  - 監視・実行プロセスはプロジェクト内のフラグファイルを監視します:
    - data/stop_requested.flag が存在すると run_* スクリプトはループを抜けて終了します（外部から停止したい場合に作成）。
    - KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（条件は監視ロジックで判定）。
  - Execution 起動時に PID ファイル（例: data/execution.pid）が書き出されます。

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB のパスを指定: --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI / レジーム判定（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続を受け取り内部でテーブル（raw_news / news_symbols / ai_scores / prices_daily 等）を参照します。
  - OPENAI_API_KEY を環境変数に設定しておくと api_key を省略できます。

主な環境変数一覧
-----------------
（validate_config モジュールがチェックするものを抜粋）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、run_monitoring で有効）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1。production では 0 推奨）

ロギング
--------
- ログは stdout と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。
- LOG_DIR 環境変数でログディレクトリ変更、LOG_LEVEL でログレベル指定が可能です。

ディレクトリ構成（抜粋）
-----------------------

src/kabusys/
- __init__.py
- config.py                      — 環境変数読み込み / Settings
- config_setup.py                — .env 対話式ウィザード（CLI）
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート CLI
- utils/
  - logging_setup.py              — ログ設定ユーティリティ
  - process_priority.py           — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py              — SQLite の DB 層
  - system_monitor.py             — システム・データ鮮度監視
  - trade_monitor.py              — 注文ログ監視（ファイルに含まれない場合あり）
  - risk_monitor.py               — ドローダウン・ポジション監視
  - kill_switch.py                — Kill Switch（flag ファイル管理）
  - monitoring_engine.py          — 各 monitor を束ねる
  - alert_manager.py              — アラート送信（LINE 等／実装次第）
- execution/
  - execution_engine.py           — 発注エンジン本体（存在）
  - broker_factory.py             — ブローカークライアント生成
  - order_manager.py              — 注文管理
  - order_repository.py           — 注文永続化
  - reconciler.py                 — 差分調整
  - risk_manager.py               — リスク管理
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py            — レジーム判定（OpenAI）
- monitoring/ (既出)
- data/ (想定されるランタイム生成場所)
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/（ログファイル出力先、デフォルト）

補足・運用上の注意
-----------------
- KABUSYS_ENV=live で起動する場合は設定（LINE 通知、API トークン等）を慎重に確認してください。validate_config によるチェックを強く推奨します。
- paper_trading は本番 DB と完全に分離されるようデザインされています。ペーパートレードは data/paper_trading.db に記録されます。
- AI 機能を利用する場合、OpenAI の API 利用料とレイトリミットに注意してください。news_nlp はバッチ処理とリトライを組み込んでいますが、APIキーの管理は厳重に行ってください。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合は stdout のみで動作します。運用環境での権限を確認してください。
- 自動読み込みされる .env/.env.local は機密情報を含むため Git 管理対象から除外してください（config_setup でも注意喚起を出しています）。

問い合わせ / 開発
-----------------
- 各モジュールはユニットテストや追加のドキュメントで補完することを想定しています。特にブローカー実装・order flow・DB スキーマ周りは実運用前に十分な検証を行ってください。

以上が本リポジトリの主要な使い方・構成の概要です。必要であれば、インストール用の requirements.txt や起動用 systemd/サービス定義、運用マニュアル（停止・ログローテーション・バックアップ方針）などのテンプレを作成します。どの情報を優先して追加しますか？