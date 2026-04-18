README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ/研究用実装）です。
主要機能として戦略の研究/ファクター計算、ポートフォリオ構築、発注実行エンジン、監視・アラート、AI（ニュースセンチメント／レジーム判定）連携、ペーパートレード検証用ツール等を含みます。

主な特徴
--------
- ExecutionEngine：実際のブローカーまたはモックを使った発注処理（KABUSYS_ENV により paper_trading と live を切替え）
- Monitoring：システム資源・データ鮮度・注文状態・リスクを定期ポーリングして永続化・アラート発行。Kill Switch により安全停止
- Portfolio モジュール：銘柄選定、重み付け、セクターキャップ、ポジションサイズ計算など純粋関数群
- Research：DuckDB を使ったファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- AI（OpenAI 経由）：ニュースの NLP スコアリング、マクロセンチメントを組み合わせた市場レジーム判定
- ユーティリティ：設定ウィザード (.env 作成)、設定検証、ログ設定、プロセス優先度設定
- ツール：ペーパートレード検証レポート生成スクリプトなど

セットアップ手順
----------------

前提
- Python 3.10 以上（コード内で | 型注釈等を使用しています）
- system パッケージ：duckdb, psutil, openai（OpenAI 機能を使う場合）、PyYAML（設定 YAML の検証を行う場合）

手順（例）
1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt が無い場合は必要なパッケージを個別にインストールしてください）

4. データ・ログ用ディレクトリを作成（通常は自動で作成されますが、手動で準備しておくと安心です）
   - mkdir -p data logs

5. 環境変数の設定（.env）
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 生成された .env をプロジェクトルートに配置（.env は絶対に Git にコミットしないでください）

6. 設定検証
   - python -m kabusys.validate_config
   - 必要なら --strict を付けて警告も失敗扱いにできます

主要な環境変数（概要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（default: development）
  - development / paper_trading / live
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
- LOG_LEVEL（default: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、run_monitoring で使用）
- PAPER_FILL_MODE（paper_trading のマッチング挙動: instant | partial | never | reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

使い方
------

起動スクリプト
- Execution エンジン（本番 / ペーパー）
  - python -m kabusys.run_execution
  - 実行前に .env を設定し、必要な API キーやパスを指定してください。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。停止は data/stop_requested.flag を作成することで行えます（run_execution は実行中に stop_requested を監視して安全に停止します）。
  - 実行中は data/execution.pid に PID を書きます（設定により変更可）。

- Monitoring（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でループ間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使って監視テーブルを初期化します（monitoring は KABUSYS_ENV に依存せず本番 sqlite を参照する設計）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います。

設定関連 CLI
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]

ツール
- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定

ライブラリ API（抜粋）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュースセンチメントを ai_scores に書き込みます（OpenAI API キーが必要）
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームを判定して market_regime テーブルへ書き込みます
- kabusys.research.calc_momentum / calc_volatility / calc_value
  - DuckDB 接続と日付でファクターを計算します
- kabusys.portfolio.* モジュール
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

監視・停止フラグの仕組み（運用メモ）
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止信号を送る目的で使います（監視側が条件を満たしたら kill.flag を作成）。
  - ExecutionEngine 側は起動時に kill.flag をチェックし、設定次第で自動クリア（KILL_FLAG_CLEAR_ON_START）しますが、本番では自動クリアを有効にしないことを推奨します。
- stop_requested.flag:
  - run_execution / run_monitoring 側でループ停止を目的に使用されるフラグ。手動で作成/削除すると起動・停止の制御に使えます。

ログ
- 共通のログ設定関数 setup_logging を利用し、logs/<app_name>.log に日次ローテートで出力します（デフォルト logs ディレクトリ）。環境変数 LOG_DIR で変更可能。ログレベルは LOG_LEVEL または引数で指定。

ディレクトリ構成
----------------

（src/kabusys 配下の主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  # ペーパートレード検証レポート
  - ai/
    - news_nlp.py            # ニュース NLP（OpenAI）連携
    - regime_detector.py     # レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py       # SQLite 永続化層（初期化 / DB 操作ラッパ）
    - system_monitor.py      # システム状態 / データ鮮度監視
    - trade_monitor.py       # （注文監視ロジック — 実装ファイルあり）
    - risk_monitor.py        # ドローダウン / ポジション上限監視
    - kill_switch.py         # kill.flag の作成/評価
    - monitoring_engine.py   # 各 Monitor を束ねるエンジン
    - alert_manager.py       # （アラート送信ロジック — 実装ファイルあり）
  - execution/
    - execution_engine.py    # ExecutionEngine 本体（発注ループ等）
    - broker_factory.py      # ブローカークライアントのファクトリ（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    # データファイル（実行時に生成されることが多い）
  - utils/
    - logging_setup.py       # 共通ログ設定
    - process_priority.py    # プロセス優先度 / CPU affinity ユーティリティ

注意事項 / 運用上のポイント
--------------------------
- .env は機密情報を含むため絶対にコミットしないでください。
- 本番（KABUSYS_ENV=live）では Kill Switch と LINE 通知などのアラート設定を必ず確認してください。validate_config は本番環境でのチェックが含まれます。
- OpenAI を使う機能は API 使用料が発生します。API キーと利用設定は慎重に扱ってください。
- monitoring は監視専用の sqlite DB を使いますが、ペーパートレード用 DB は別ファイルに分離されています（paper_trading 時のデータ分離を確保）。
- process_priority.set_process_priority() が最初に呼ばれ、可能であればプロセス優先度を上げます（OS 権限に依存し失敗する場合あり）。

貢献・拡張
----------
- 戦略ロジック、ブローカープロバイダ、アラート送信先（LINE 等）を自由に拡張できます。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）に依存するため、データインジェストパイプラインの整備が必要です。

問題や質問があればリポジトリの Issue に記載してください。