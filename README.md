KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究用ユーティリティ群を含む軽量なコードベースです。本リポジトリには以下の目的のコンポーネントが含まれます。
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
- システム監視ポーリング（run_monitoring、MonitoringEngine）
- 環境設定ウィザード・設定検証ツール（config_setup、validate_config）
- Paper Trading 向け検証レポート生成ツール
- ポートフォリオ構築・ポジションサイズ計算ロジック（純粋関数群）
- 研究用ファクター計算モジュール（DuckDB を利用）
- ニュース NLP / レジーム検出（OpenAI を利用する AI モジュール）
- 共通ユーティリティ（ロギング設定・プロセス優先度設定 等）
設計方針として、外部副作用（実際の発注等）を分離し、Paper Trading 用 DB と本番 DB を分けて扱えるようになっています。

主な機能
--------
- 起動・運用系
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い data/paper_trading.db に記録。
  - run_monitoring: SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス存否の監視と永続化（SQLite）。
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine: 注文滞留・ドローダウン・ポジション上限などを監視し、必要に応じて停止フラグやアラートを発行。
  - MonitoringDB: SQLite を使った永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）。
- ポートフォリオ構築（portfolio）
  - 銘柄選定・スコア順ソート（select_candidates）
  - 等金額／スコア加重重み（calc_equal_weights, calc_score_weights）
  - 単元丸め・リスクベース等のポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- 研究（research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
  - DuckDB 接続を受け取り SQL による高速集計を実行
- AI（ai）
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュース記事のセンチメントを銘柄ごとに評価し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースセンチメントを組合せて市場レジーム判定
- ユーティリティ（utils）
  - setup_logging: stdout と日次ローテートファイル出力を統一的に設定
  - process_priority: Windows / POSIX の差を吸収しプロセス優先度・CPU affinity を設定

セットアップ手順
----------------
1. Python 環境を準備
   - Python 3.10+ を推奨（コードは型注釈に最新構文を一部使用）
   - 仮想環境を作成して activate することを推奨

2. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 任意/機能依存:
     - PyYAML（config/*.yaml の検証に使用）
   - pip 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートの.env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要環境変数（.env で指定する主な項目）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール使用時に必要）
     - LOG_LEVEL（DEBUG/INFO/...）
     - PAPER_FILL_MODE（instant|partial|never|reject）※paper_trading の約定挙動

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いに（exit code 1）

5. 初期 DB 作成
   - 実行スクリプトが起動時に monitoring DB のテーブルを冪等作成します（init_monitoring_db）。明示的な初期化は不要。

使い方
------
- 環境変数の設定と確認
  - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
  - KABUSYS_ENV によって run_execution の挙動が変わります（paper_trading は専用 DB と MockBroker）。

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行時は PID ファイル（data/execution.pid 等）を作成します。

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を秒数で指定（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は production sqlite_path を使用（Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照します）。
  - 監視ループを停止するにはプロジェクトルート/data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 設定ウィザード・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI モジュール（ニュース NLP / レジーム）
  - OpenAI API キーが必要。環境変数 OPENAI_API_KEY または関数呼び出しで指定。
  - 例（スクリプト内から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="xxxxx")
  - 戻り値や挙動は各モジュールの docstring を参照してください。

ログとデータ
------------
- ログ出力
  - kabusys.utils.logging_setup.setup_logging により stdout と logs/<app_name>.log に出力（日次ローテート、30 日保存）
  - LOG_DIR 環境変数でログディレクトリを指定可（デフォルト: logs/）
  - LOG_LEVEL 環境変数でログレベルを指定（デフォルト: INFO）

- データファイル（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID/Flag: data/execution.pid, data/stop_requested.flag, data/kill.flag

停止シグナル
----------
- 停止フラグ:
  - run_execution / run_monitoring は data/stop_requested.flag を監視し、存在時に安全に停止します（run_execution は起動直後にフラグがあれば起動しない）。
- Kill Switch:
  - KillSwitch モジュールはデータベースの監視結果（ドローダウンやポジション上限）から data/kill.flag を書き込み、ExecutionEngine に停止指示を出す仕組みです。KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に自動でクリアしますが、本番では 0 を推奨します。

設定項目（抜粋）
----------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- OPENAI_API_KEY: AI モジュール使用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理、自動 .env 読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 対応）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

subpackages / 主要モジュール:
- ai/
  - news_nlp.py — ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — MA200 とマクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・永続化 API
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — （発注ログ監視、コード参照）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — 停止フラグの作成 / 管理
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py — （通知管理）
- portfolio/
  - portfolio_builder.py — 候補選定、スコア順ソート
  - position_sizing.py — 株数算出、aggregate cap 処理、単元丸め
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading のレポート生成
- utils/
  - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上のヒント
-----------------------
- .env は絶対にレポジトリにコミットしないこと（config_setup.py でも警告あり）。
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- Monitoring は監視 DB（SQLITE_PATH）を参照します。run_monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意してください。
- AI モジュールは OpenAI API に依存します。API 呼び出しの失敗時はフェイルセーフ（スコア 0 やスキップ）する実装になっていますが、API キーとコスト管理は運用上留意してください。
- ファイル出力が失敗した場合でもログは stdout に出力されるよう設計されています。

貢献・拡張
-----------
- DuckDB テーブル（prices_daily, raw_financials, raw_news など）を整備すると研究・AI 機能が活用できます。
- ExecutionEngine や BrokerClient 実装を差し替えることで実取引・別ブローカー対応が可能です（BrokerClientFactory を参照）。
- CSV からのデータ投入スクリプトや CI 用のテストヘルパーは別途用意すると運用が楽になります。

以上。詳細な各関数・クラスの使い方は各モジュールの docstring を参照してください。README に記載のコマンド例で起動して問題が発生する場合はログ（logs/）を確認してください。