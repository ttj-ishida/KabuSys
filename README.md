KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株向けの自動売買／リサーチ基盤の一部実装です。
主要コンポーネントとして、監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、
リサーチ（ファクター計算・特徴量解析）、AI を使ったニュース評価などが含まれます。

以下はコードベースの利用者向け README（日本語）です。

概要
----
KabuSys は自動売買システムのコア機能群をモジュール化した Python パッケージです。
主な目的は以下です。

- 発注エンジンの起動・管理（実際発注 / ペーパートレード）
- システム稼働状況・注文ログ・リスク監視（SQLite を用いた永続化）
- ポートフォリオ構築（候補選定・重みづけ・株数決定・制約適用）
- リサーチ（DuckDB を用いたファクター計算・将来リターン計算）
- AI（OpenAI）を用いたニュースのセンチメント評価・レジーム判定
- 運用支援ツール（設定ウィザード・設定検証・ペーパートレード検証レポート）

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを分離）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理・ユーティリティ
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
  - config.py: Settings クラスにより環境変数を統合して提供
- 監視（monitoring）
  - monitoring_db.py: SQLite による監視ログテーブル初期化 / 永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py
  - Kill Switch 実装（data/kill.flag による ExecutionEngine 停止）
- 発注関連（execution）
  - BrokerClientFactory を経由したブローカークライアント取得（paper_trading で Mock）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository 等
- ポートフォリオ（portfolio）
  - 候補選定・重みづけ（等金額 / スコア加重）
  - セクター上限適用、レジーム乗数、株数計算（単元丸め、aggregate cap 等）
- リサーチ（research）
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC 計算、統計サマリ
- AI（ai）
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジームを判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI

セットアップ手順
----------------
1. Python 環境（推奨: 3.9+）を用意し、仮想環境を作成します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 必要なパッケージをインストールします（プロジェクトルートに requirements.txt があればそれを使用）。
   必須と思われる主要パッケージ:
   - duckdb
   - psutil
   - openai
   - PyYAML (設定ファイル検証を使う場合)
   例:
     pip install duckdb psutil openai PyYAML

   （パッケージ名やバージョンはプロジェクトの配布方法に従ってください）

3. ディレクトリ作成（デフォルトで使用される場所）
   - data/: SQLite / PID / フラグファイル等を保存
   - logs/: ログファイル
   例:
     mkdir -p data logs

4. .env の準備
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成してください。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

よく使う環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時）
- DUCKDB_PATH: DuckDB DB パス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL / LOG_DIR: ログ制御
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: MockBroker の約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方（主なコマンド）
---------------------

1) 設定ウィザード（.env の作成）
   python -m kabusys.config_setup

2) 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

3) 監視ループ起動（SystemMonitor）
   - デフォルトは MONITOR_POLL_INTERVAL=60（秒）
   - 実行:
     python -m kabusys.run_monitoring
   - 環境変数で間隔変更:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 停止方法:
     data/stop_requested.flag（stop_requested.flag の存在を監視して停止）
   - 監視は Settings に従って sqlite_path を使用（監視は常に本番 sqlite_path を参照）

4) ExecutionEngine 起動（発注エンジン）
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、
     DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録されます。
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
   - 実行中は data/execution.pid に PID を出力します。
   - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT を送ってください。

5) Paper Trading 検証レポート
   python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6) AI 系ユーティリティ（プログラム的に呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   これらは DuckDB 接続および target_date を受け取り、DB の該当テーブルへ書き込みを行います。
   OPENAI_API_KEY を環境変数で用意するか、api_key 引数で渡してください。

ログ
---
- ログはデフォルトで stdout に出力され、logs/<app_name>.log に日次ローテーションで書き出されます。
- ログレベルは LOG_LEVEL（環境変数）または setup_logging の引数で制御可能です。

停止フラグ / Kill Switch
-----------------------
- ExecutionEngine の停止シグナル:
  - data/stop_requested.flag: run_execution/run_monitoring がこのファイルを検知すると
    安全にシャットダウンします（起動時の存在チェックも行います）。
- Kill Switch（運用上の強制停止）:
  - monitoring 側でリスク条件がトリガーすると data/kill.flag を作成します。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では推奨されません。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 内の主要ファイルと概要です。

- __init__.py
  - パッケージ初期化・バージョン情報

- config.py
  - Settings クラス: 環境変数の取得・検証・デフォルト

- config_setup.py
  - .env 対話式ウィザード

- validate_config.py
  - 設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py: 共通ログ設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - 他ユーティリティ群

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と DB 操作ラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, kill_switch.py, alert_manager.py など

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py

- research/
  - factor_research.py, feature_exploration.py

- ai/
  - news_nlp.py, regime_detector.py

- data/
  - （実運用では SQLite / DuckDB / flag / pid ファイルなどをここに置きます）

- logs/
  - （ログファイルが出力される既定ディレクトリ）

開発時の注意点 / 実運用の考慮
----------------------------
- 本プロジェクトは本番発注ロジックを含むため、KABUSYS_ENV=live の設定時は十分に注意してください。
- .env は絶対に VCS にコミットしないでください（シークレットを含む）。
- AI 呼び出し（OpenAI）はコストとレート制限があるため運用での利用ルールを定めてください。
- run_monitoring は Monitoring 用 DB（settings.sqlite_path）を使います。監視は本番 DB を参照してログを取る設計です。
- run_execution は paper_trading 時には専用 DB を使い、本番 DB と分離します。

トラブルシュート
-----------------
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合、validate_config は警告を出します。必要に応じて手動で作成してください（log ディレクトリ等も同様）。
- psutil によるプロセス優先度の設定は権限不足で失敗する場合があります（警告ログのみ）。

貢献
----
バグ修正や機能追加はプルリクエストを歓迎します。テストやドキュメントの追加も助かります。

ライセンス
----------
（ここにライセンス情報を記載してください）

付録：よく使う実行例
--------------------
- .env の対話式作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config

- 監視起動（60 秒間隔）:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動（ペーパートレード）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。運用・開発で必要な追加ドキュメント（API仕様、ExecutionEngine の詳細設計書、DB スキーマ説明など）は別途まとめることを推奨します。