KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。  
本READMEはコードベース（src/kabusys）をもとにした概要・セットアップ・実行方法・ディレクトリ構成の説明です。

重要: .env ファイルには秘密情報（API トークン等）を記載します。絶対に Git にコミットしないでください。

プロジェクト概要
----------------
KabuSys は、銘柄選定（ポートフォリオ構築）、ポジションサイズ計算、発注実行、監視・リスク管理、研究用ファクター計算、AI（ニュース NLP / レジーム判定）などの機能を持つモジュール群です。  
主に以下の役割を持つコンポーネントで構成されています。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・オーダー管理を統括
- 監視（Monitoring）: システム状態・注文状況・リスクを定期チェックしアラートや Kill Switch を制御
- ポートフォリオ構築（portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制約
- 研究（research）: ファクター計算、特徴量解析、IC 計算など（DuckDB を使用）
- AI（ai）: ニュースのセンチメント評価、レジーム検出（OpenAI を利用可能）
- ユーティリティ（utils）: ロギング設定、プロセス優先度など
- ツール（tools）: ペーパートレード検証レポート等

主な機能一覧
--------------
- 環境設定ウィザード（.env 生成支援）
  - kabusys.config_setup.run_wizard により対話式で .env を生成
- 設定検証 CLI
  - kabusys.validate_config で必須環境変数や config/*.yaml の存在・基本検証
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に分離
- 監視ループ起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリング
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
- MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
- RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / AlertManager を束ねる MonitoringEngine
- ポートフォリオ構築ユーティリティ
  - 銘柄候補選定、等重・スコア加重、リスクベースの株数計算、セクター制約、レジーム乗数
- 研究用モジュール（DuckDB 前提）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC、統計要約
- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI に送信し ai_scores に保存
  - regime_detector.score_regime: ETF 指標 + マクロニュースで市場レジームを判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

セットアップ手順
----------------

1. リポジトリをチェックアウト（パッケージインストールの想定: src パスがパッケージ root）
2. Python 依存ライブラリをインストール
   - 最低限必要なパッケージ（例）
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config YAML の完全検証を行う場合）
   - 例: pip install duckdb psutil openai pyyaml
3. .env の準備（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuステーション / DB パス / LOG_LEVEL / KABUSYS_ENV 等を対話式で設定し .env を生成します
   - 生成後は python -m kabusys.validate_config で検証を行ってください
4. データディレクトリを作成（必要に応じて）
   - デフォルトでは data/ に SQLite / PID / フラグファイル等が配置されます
   - ログは logs/ に出力されます（LOG_DIR 環境変数で変更可能）
5. DuckDB 用データ（prices_daily, raw_financials, raw_news 等）は研究機能を使う場合に整備してください

主要な環境変数（抜粋）
----------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 環境/運用
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/...
  - LOG_DIR — ログ保存先ディレクトリ
- DB 関連
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- AI 関連
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp・regime_detector で利用）
- 監視/制御
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0。本番で 1 は危険）

実行方法（代表的なコマンド）
--------------------------

- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録され、本番 DB と完全分離されます
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中は data/execution.pid に PID を書きます（_EXECUTION_PID）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path を使用（monitoring DB は環境に依存せず本番パスを使用）
  - 停止は data/stop_requested.flag を作成することで行います（監視ループが検知して終了）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定（環境変数または関数引数）してから実行
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

アーキテクチャ上の注意点 / 運用上の注意
-----------------------------------
- .env の自動読み込み:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- データベース:
  - monitoring（SQLite）は init_monitoring_db でテーブル・マイグレーションを自動で行います
  - ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）
- PID / Stop フラグ / Kill Switch:
  - data/execution.pid: ExecutionEngine の PID 保存先（設定で変更可）
  - data/stop_requested.flag: 外部から起動中のループを停止させるためのフラグ（run_execution/run_monitoring で利用）
  - KillSwitch はリスク閾値を満たした時に data/kill.flag を書き込み Execution を停止させるための仕組み（clear メソッドあり）
- ログ:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトで共通利用しています。ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます
- 本番環境（KABUSYS_ENV=live）:
  - LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）が未設定だとアラートが届きません
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは危険（自動クリアで Kill Switch が無効化される可能性がある）

ディレクトリ構成（src/kabusys 以下の主要ファイル）
------------------------------------------------
- __init__.py
  - パッケージ定義（__version__ など）
- config.py
  - Settings クラス。環境変数から設定値を取得・検証。自動 .env ロード機能あり
- config_setup.py
  - 対話式 .env 生成ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前の設定チェック CLI（python -m kabusys.validate_config）
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で制御）
- ai/
  - news_nlp.py: ニュースセンチメントスコアリング（OpenAI を利用）
  - regime_detector.py: 市場レジーム判定（ETF + ニュース）
- monitoring/
  - monitoring_db.py: SQLite テーブル作成 / MonitoringDB（読み書きユーティリティ）
  - system_monitor.py: システム状態・データ鮮度チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - trade_monitor.py, alert_manager.py （存在する想定の関連モジュール）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - Execution の主要ロジックと Broker 抽象化（MockBroker は paper_trading 用）
- portfolio/
  - portfolio_builder.py: 候補選定、重み計算
  - position_sizing.py: 株数決定、aggregate cap、lot rounding
  - risk_adjustment.py: セクター上限、レジーム乗数
- research/
  - factor_research.py: momentum/value/volatility の計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py: ペーパートレード DB からの検証レポート
- utils/
  - logging_setup.py: 共通ロギング設定
  - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ

（上記に省略されているファイルやサブモジュールが一部存在します。実際のファイル一覧はリポジトリを参照してください。）

よくある運用フロー（例）
-----------------------
1. .env を作成
   - python -m kabusys.config_setup
2. 設定を検証
   - python -m kabusys.validate_config
3. （開発）ペーパートレードで Execution を起動
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
4. 監視を別プロセスで起動
   - python -m kabusys.run_monitoring
5. ペーパートレード結果の検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ローカル開発上のヒント
---------------------
- .env を複数人で共有しないこと。サンプルや .env.example を使ってテンプレートを配布してください。
- Docker や systemd でサービス化する場合は data/ 以下の永続化・権限に注意してください（PID ファイル / フラグファイル / DB）。
- OpenAI API を使う処理はレート制限・エラー処理を備えていますが、運用時は API キーのレートやコストに注意してください。

ライセンス・貢献
----------------
- この README に記載の情報はコード解析に基づくドキュメントです。実際の動作や追加ファイル（config/*.yaml 等）についてはリポジトリ内のドキュメントやコードを参照してください。

補足
----
- さらに詳しい仕様（ポートフォリオ設計、ストラテジ仕様、ExecutionEngine の詳細など）は別途ドキュメント（Design / Markdown）で管理している想定です。必要であればそこに合わせて README を拡張できます。

必要な追記（要望があれば）
-------------------------
- 実際のサンプル .env.example を作成してほしい
- systemd / Docker 用のサービスユニット例を用意してほしい
- 各モジュール（ExecutionEngine / OrderManager / Monitoring）の詳細設計の抜粋を README に追加してほしい

ご希望があれば上記のいずれかを作成します。どれを追加しますか？