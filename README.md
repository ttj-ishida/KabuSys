README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python プロジェクトです。  
システム監視、Execution エンジン起動（本番／ペーパートレード切替）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を用いたセンチメント評価）などのコンポーネント群を含みます。  
本リポジトリ内のモジュールは「実行用スクリプト」「監視」「注文管理」「ポートフォリオ構築」「リサーチ」「AI（ニュース処理）」など役割ごとに分離され、.env による設定を参照して動作します。

主な特徴（機能一覧）
-----------------
- 実行エンジン起動スクリプト
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV により paper_trading（モックブローカー）/ live（本番）を切替。
  - ペーパートレード時は data/paper_trading.db に完全分離して記録。
- 監視（Monitoring）
  - run_monitoring.py：SystemMonitor のポーリングループを実行。監視ログは SQLite（monitoring.db）へ保存。
  - MonitoringEngine：SystemMonitor/TradeMonitor/RiskMonitor をまとめて実行し、アラートや Kill Switch を評価。
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ記録。
  - KillSwitch：条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止を促す。
- ポートフォリオ構築
  - 候補選定、等重／スコア加重、リスク制約（セクターキャップ、レジーム乗数）、ポジションサイズ計算（ロット丸め、aggregate cap）を提供。
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ。
- AI（ニュース NLP / レジーム判定）
  - OpenAI を使ったニュースの銘柄別センチメント評価（ai/news_nlp.py）。
  - マクロニュース + ETF MA による市場レジーム判定（ai/regime_detector.py）。
  - OpenAI 呼び出しはリトライやレスポンス検証を組み込み。
- 管理・ユーティリティ
  - 設定読み込み（.env 自動ロード、Settings クラス）
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度／CPU affinity 設定ユーティリティ（utils.process_priority）
  - Paper Trading 用検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順
---------------
1. Python（推奨）
   - Python 3.10 以上を推奨（typing における | 演算子等を使用）。

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 最低限の依存（プロジェクトで使用されている主なライブラリ）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注意: requirements.txt は本リポジトリに含まれていないため、環境に応じてバージョン固定を行ってください。

4. 初期設定 (.env)
   - 対話式ウィザードで .env を生成・編集:
     - python -m kabusys.config_setup
   - 生成後、設定検証を実行:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを配置します。スクリプト起動時に自動作成されることもありますが、手動で mkdir -p data logs を推奨します。

代表的な環境変数（主要なもの）
--------------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行関連:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

- DB パス（デフォルト）:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 専用）

- OpenAI:
  - OPENAI_API_KEY

- その他:
  - PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードの約定挙動）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0|1

使い方（起動例）
----------------
- 設定作成 / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
    - 問題なければ exit 0、問題があれば exit 1（--strict で警告も失敗扱い）

- 実行エンジン起動
  - 本番（注意して使用）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - ペーパートレード（モックブローカー、専用 DB に記録）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  - ExecutionEngine は data/execution.pid に PID を書き、data/stop_requested.flag によって外部から停止指示を検出します。data/kill.flag が書かれると Kill Switch 経由で停止処理が行われます（設定次第）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - export MONITOR_POLL_INTERVAL=30  # 30秒間隔
  - 監視は Settings に基づく sqlite_path（本番用 monitoring.db）を参照します（KABUSYS_ENV に依らず本番 sqlite_path を使用する挙動に注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能、環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI（ニューススコア/レジーム判定）の利用
  - ai/news_nlp.score_news(conn, target_date, api_key=None)：OpenAI API キーを env または引数で指定する必要あり。
  - ai/regime_detector.score_regime(conn, target_date, api_key=None)：同上。
  - OpenAI API 呼び出しはリトライ・レスポンス検証を行いますが、API キーと利用上のコストに注意してください。

停止・Kill Switch
-----------------
- 外部からの停止（全体）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して順次終了します（stop flag）。
- Kill Switch:
  - 監視モジュールにより条件が満たされた場合、data/kill.flag が書き込まれます。ExecutionEngine は起動時にこのフラグの存在を確認し、起動を抑止または停止処理を行います（設定次第）。
- PID ファイル:
  - run_execution は data/execution.pid を用います（pid ファイルパスは Settings により変更可）。

ディレクトリ構成（主要ファイル）
------------------------------
下記は src/kabusys 以下の主要モジュールと概要です（抜粋）:

- kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数/.env 読み込みと Settings クラス（設定取得ユーティリティ）
  - config_setup.py — .env 作成用ウィザード（CLI）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- kabusys/utils/
  - logging_setup.py — 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- kabusys/monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor をまとめるエンジン
  - kill_switch.py — フラグファイルによる停止トリガー
  - alert_manager.py, trade_monitor.py など（アラート／取引監視ロジック）

- kabusys/execution/  （注文管理 / ExecutionEngine 実装）
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（ロット丸め、aggregate cap）
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- kabusys/research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py — IC / forward returns / 統計サマリー

- kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート出力ユーティリティ

運用上の注意
------------
- .env ファイルは機密情報（API キー等）を含むため絶対に Git 等へコミットしないでください（config_setup.py のヘッダーにも注意書きあり）。
- KABUSYS_ENV=live では実際の発注が行われます。運用前に validate_config で設定を十分確認してください。
- OpenAI API を利用する機能は API コストやレート制限の影響を受けます。API キーの管理・使用上限には十分注意してください。
- ログはデフォルトで logs/ 下に日次ローテートで出力されます。ログディレクトリの作成に失敗した場合はコンソールのみ出力されます。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値は無効でデフォルトにフォールバックします。

さらに詳しく / 拡張
------------------
- DuckDB を用いたファクター計算や AI モジュールは、テーブル定義（prices_daily / raw_news / raw_financials 等）に依存します。データパイプライン側でこれらのテーブルを整備してください。
- execution/ 内はブローカークライアントの抽象化（BrokerClientFactory）を使って実運用向け・モックの切替を行っています。新しいブローカーを追加する際は factory を拡張してください。
- 将来的な改善点（README 内記載の TODO 等）はソース内コメントを参照してください。

問い合わせ / 貢献
----------------
- この README はコードベースの概要説明を目的としています。各モジュールの詳細な使用法や API（関数引数・戻り値等）はソースの docstring を参照してください。  
- プロジェクトに貢献する場合は、まずローカルで config_setup → validate_config → unit テスト（存在すれば）を実行し、変更点の動作検証を行ってください。

以上。