KabuSys
======

日本株向けの自動売買システム（モジュール群）です。  
このリポジトリは注文エンジン、監視機構、ポートフォリオ構築、調査用ファクター計算、ニュースNLP / レジーム判定などをコンポーネント化して提供します。

主な目的は「研究（Research） → シグナル生成（Strategy） → Execution（発注） → Monitoring（監視／Kill Switch）」のワークフローを安全に運用できることです。

主な機能
-------

- ExecutionEngine：発注フロー（ブローカー抽象化、リスク管理、注文管理、再帰処理）
- Monitoring：システム稼働状況・データ鮮度・注文状態・リスクを定期ポーリングし、アラートや Kill Switch を発動
- Config 管理：.env 自動ロード、対話式 .env 作成ウィザード、設定検証 CLI（strict モード有）
- Portfolio construction：候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research：DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）、特徴量探索、IC 計算
- AI モジュール：ニュースの NLP スコアリング（OpenAI）と市場レジーム判定（OpenAI + MA200）
- Tools：ペーパートレード検証レポート生成スクリプト等
- 永続化：SQLite（監視ログ / ペーパートレード DB）、DuckDB（時系列・財務データ集計）

動作要件（概略）
----------------

- Python 3.9+（ソースは型ヒントで 3.9+ 想定）
- 必須外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証時に config/*.yaml をパースする場合）
- SQLite は標準ライブラリで使用
- システム上の DB ファイル・ログディレクトリへ書き込み権限が必要

例（仮）インストール:
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール
  - pip install duckdb psutil openai PyYAML

初期セットアップ
---------------

1. リポジトリをクローンしてワークディレクトリへ移動します。

2. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - 対話ウィザードに従って J-Quants トークン、kabu API パスワード等を入力します。
   - 生成される .env は絶対に Git にコミットしないでください。

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit(1)）になります。

主要な環境変数（概要）
---------------------

（config_setup.py にある項目を抜粋）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient が使用され、発注は data/paper_trading.db に記録されます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant/partial/never/reject）

起動（主要スクリプト）
--------------------

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 停止にはプロジェクトルート/data/stop_requested.flag を作成（または既存のものを配置）すると、監視ループは検知して終了します。
    - Monitoring は Settings に関わらず本番 sqlite_path を使用します（監視ログは共通 DB）。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db へ記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag がすでに存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を書き込みます。停止は stop フラグを書き込むか、Kill Switch を利用。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB 指定可能

停止 / Kill Switch
------------------

- Kill Switch（自動停止）
  - モニタリングの RiskMonitor が定義された閾値（ドローダウン・ポジション上限など）を超えた場合、KillSwitch が data/kill.flag を書き込み、ExecutionEngine を停止させる挙動を持ちます。
  - KillSwitch.write は冪等で、既にフラグが存在する場合は上書きしません。

- 手動停止
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_execution/run_monitoring のループは検知して正常終了を試みます。

ログ
----

- ログは共通ユーティリティでセットアップされます（kabusys.utils.logging_setup.setup_logging）。
- デフォルト出力先:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト保管 30 日）
- ログディレクトリは環境変数 LOG_DIR で上書き可能。

主要モジュールと役割（ファイル参照）
--------------------------------

- kabusys/config.py — 環境変数・.env 自動ロード、Settings クラス
- kabusys/config_setup.py — .env 対話ウィザード
- kabusys/validate_config.py — 起動前チェック CLI
- kabusys/run_execution.py — ExecutionEngine 起動スクリプト
- kabusys/run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- kabusys/monitoring/ — 監視関連:
  - monitoring_db.py（SQLite 永続化層）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager.py
- kabusys/execution/ — 発注・リスク管理・OrderManager など（発注ロジック）
- kabusys/portfolio/ — ポートフォリオ構築（選定・重み付け・リスク調整・ポジションサイズ）
- kabusys/research/ — DuckDB を利用したファクター計算・特徴量解析
- kabusys/ai/ — OpenAI を使ったニュース NLP とレジーム検出
- kabusys/tools/ — 補助ツール（paper_verification_report など）
- kabusys/utils/ — logging_setup, process_priority（優先度・CPU affinity 設定）など

ディレクトリ構成（抜粋）
-----------------------

プロジェクトルートの想定（src レイアウト）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/          # ExecutionEngine, OrderManager, BrokerFactory...
    - monitoring/         # system_monitor, trade_monitor, risk_monitor, monitoring_db...
    - portfolio/          # portfolio_builder, risk_adjustment, position_sizing
    - research/           # factor_research, feature_exploration
    - ai/                 # news_nlp, regime_detector
    - tools/              # paper_verification_report
    - utils/              # logging_setup, process_priority
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/                   # データベース / フラグファイル（例: monitoring.db, paper_trading.db, kill.flag）
- logs/                   # ログ出力先（デフォルト）

実運用上の注意
------------

- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- .env を誤ってコミットしないよう注意してください。
- OpenAI API を利用する機能（ニュース NLP、レジーム判定）は API キーの管理と使用料に注意が必要です。
- ポートフォリオ構築や発注ロジックは戦略設計文書（PortfolioConstruction.md / StrategyModel.md）等に沿ってカスタマイズしてください（本 README では詳細の説明は省略）。

開発者向け補足
--------------

- DuckDB 接続を受ける研究モジュールは DB 内の prices_daily / raw_financials 等のスキーマに依存します。
- テストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると .env 自動ロードを無効にできます。
- ロギングは一貫して setup_logging を使ってください（ハンドラの二重登録を防止）。

サンプルコマンド一覧
-------------------

- .env を対話式で作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視開始:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----

この README はコードベースから抽出した情報をまとめた概要ドキュメントです。実装詳細（関数の引数や戻り値、さらなる設定項目など）は該当するモジュール（kabusys/ 以下の各ファイル）を参照してください。必要であれば、各モジュールごとの詳細なドキュメント（API リファレンス）を追加できます。