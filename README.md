README
=====

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ライブラリ兼実行環境です。
主に以下を提供します:

- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算ロジック
- ファクター計算・特徴量探索の研究モジュール（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI を用いたスコアリング）
- 監視用 DB 層（SQLite）と監視エンジン（アラート・Kill Switch）
- 開発用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

特徴（主な機能）
----------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式ウィザードで .env を作成・更新（kabusys.config_setup）
  - 起動前に設定・ファイルパス等を検証する CLI（kabusys.validate_config）
- 実行・監視
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live を切替）
  - run_monitoring: SystemMonitor を定期実行（MONITOR_POLL_INTERVAL で間隔変更可）
  - 停止フラグ（data/stop_requested.flag）や Kill Switch（data/kill.flag）で安全停止
- 監視
  - system_monitor: CPU/メモリ/ディスク、プロセス存在、データ鮮度を監視
  - trade_monitor / risk_monitor: 注文滞留、約定異常、ドローダウン・ポジション上限を監視
  - monitoring_db: SQLite に監視ログやトレードログを永続化
- ポートフォリオ
  - 銘柄選定、等配分/スコア配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（リスクベース、等配分など、単元株丸め対応）
- 研究・分析
  - DuckDB を使ったファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI 統合（OpenAI）
  - news_nlp: ニュース記事を LLM に送信して銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF 指標 + マクロニュースで市場レジーム（bull/neutral/bear）を判定
- ユーティリティ
  - ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

前提・依存
-----------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で config/*.yaml をパースする場合）
- DuckDB / SQLite を利用します（ファイルはデフォルトで data/ 配下に作成されます）
- OpenAI を使う機能は環境変数 OPENAI_API_KEY が必要

セットアップ手順
----------------
1. リポジトリをクローンし、Python の仮想環境を作成・有効化  
   例: python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール  
   例:
   pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を利用）

3. .env を作成する  
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくはルートに .env を手動で作成（.env.example を参考に）

   主な環境変数（代表例）:
   - KABUSYS_ENV: development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading）
   - OPENAI_API_KEY: OpenAI を使う場合に必要
   - LOG_LEVEL: DEBUG / INFO / WARNING / ...

4. 設定検証（起動前に推奨）  
   python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます

5. ログディレクトリの確認  
   デフォルトで logs/ に日次ローテートログが出力されます。必要なら環境変数 LOG_DIR で変更。

使い方（起動・各コマンド）
-------------------------
- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、ペーパートレード用 DB（data/paper_trading.db）に記録されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。
  - 起動時に data/execution.pid が使用されます（PID ファイル）。

- 監視プロセスを起動:
  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使って監視テーブルに書き込みます（環境に依存しません）。
  - stop フラグ（data/stop_requested.flag）で停止します。

- コンフィグ作成（対話式）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- 研究用 API（Python コード内から呼ぶ）
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    結果は DuckDB 接続を渡して取得します。
  - ニュース NLP / レジーム判定:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="...")

監視・停止フラグの仕組み
-----------------------
- data/stop_requested.flag: run_execution / run_monitoring が起動ループで監視する停止フラグ。存在すればプロセスを終了します。
- data/kill.flag: KillSwitch によって書き込まれるファイル。ExecutionEngine に停止を促す目的で使用。Settings.kill_flag_path でパスを決定します。
- KillSwitch はリスク監視（ドローダウンやポジション上限）等によりフラグを書きます。ExecutionEngine は起動時・実行中にこのフラグを確認して停止します。

主な設定項目（環境変数）
-----------------------
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: AI 機能を使う場合に必須
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: 各種 DB ファイルパス
- LOG_LEVEL, LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: run_monitoring 用ポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1）

ディレクトリ構成（主要ファイル説明）
------------------------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数の読み込みと Settings クラス。.env 自動ロード、検証ユーティリティを含む。
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID / stop flag 処理含む）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- utils/
  - logging_setup.py: 統一ログ設定（Stream + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度 / CPU affinity 設定（psutil 使用）
- monitoring/
  - monitoring_db.py: SQLite 用の永続化層（テーブル作成・CRUD）
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: （トレード監視ロジック）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の書き込みロジック
  - monitoring_engine.py: 各 Monitor をまとめるエンジン
  - alert_manager.py: （アラート送信ロジック）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - ExecutionEngine とそれに依存するコンポーネント群（ブローカー、リスク管理、注文管理など）
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・リスク制限・単元丸め
  - risk_adjustment.py: セクター制限・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
  - __init__.py: 主要研究 API エクスポート
- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores へ書き込む
  - regime_detector.py: ETF 指標 + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート生成スクリプト

注意事項・運用上のポイント
-------------------------
- 本リポジトリは実際の発注に関わる設計を含みます。KABUSYS_ENV=live を設定する際は設定値、認証情報、Kill Switch の挙動を必ず確認してください。
- .env ファイルは機密情報を含むため Git へコミットしないでください。
- OpenAI など外部 API を使う機能は API キー不要時に呼ばないなど安全柵を設けていますが、API 使用時のコストとレート制限に注意してください。
- DuckDB / SQLite のファイルパスは環境変数で変更可能です。ペーパートレードは本番 DB と分離されます（paper_trading 用 DB を使用）。

貢献・拡張
-----------
- 研究モジュールは DuckDB クエリ + Python 関数で拡張可能です。
- BrokerClient の実装を追加することで新しい証券会社への接続対応が可能です（broker_factory）。
- logging_setup / process_priority はアプリ全体で統一されています。カスタム設定が必要ならこれらを活用してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理（現在 0.1.0）。
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

以上。必要であればサンプル .env テンプレートや起動シナリオ（開発 / ペーパートレード / 本番）の具体例を追記します。どの部分を詳しく書くか指示ください。