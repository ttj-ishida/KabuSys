README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには
- 発注実行エンジン (ExecutionEngine)
- 監視コンポーネント（System / Trade / Risk Monitor、Kill Switch）
- リサーチ（ファクター計算・特徴量探索）
- ポートフォリオ構築・ポジションサイジング
- AI 補助（ニュース NLP / レジーム判定）
- 運用補助ツール（.env ウィザード / 設定検証 / Paper Trading 検証レポート）

が含まれます。設計方針として、本番 DB とペーパートレード DB を分離し、DuckDB を分析用に利用、OpenAI API を用いた非決済的な NLP 機能を提供します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番 or paper_trading（MockBroker）で動作
  - 発注・リスク管理・注文再整合化の起動
- Monitoring（run_monitoring.py）
  - システム状態、データ鮮度、取引ログ、リスク閾値をポーリングして永続化・アラート判定
  - Kill Switch による ExecutionEngine 停止（flag ファイル方式）
- 環境設定ウィザード（config_setup.py）
  - 対話式で .env を作成/更新
- 設定検証 CLI（validate_config.py）
  - .env および config/*.yaml の基本検証
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・成功率・レイテンシ等を集計して PASS/FAIL 判定
- リサーチ API（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン・IC 計算・統計サマリー
- AI モジュール（ai）
  - ニュースのセンチメント評価（OpenAI を利用）
  - 市場レジーム判定（ma200 とマクロニュースの組合せ）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限適用 など

前提条件
--------
- Python 3.9+
- SQLite（標準ライブラリに含まれます）
- 推奨 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
- （任意）.env を使った環境変数管理

セットアップ手順
--------------
1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を利用）

3. .env の初期作成
   - python -m kabusys.config_setup
     - 対話式で必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力して .env を作成します。
   - もしくは .env を直接作成して環境変数を定義してください。

主な環境変数（抜粋）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
  - OPENAI_API_KEY: OpenAI API を使う機能で必要
  - LOG_LEVEL, LOG_DIR
  - KILL_FLAG_CLEAR_ON_START: 起動時の kill.flag 自動クリアフラグ（0|1）
- 監視関連
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH: data/kill.flag の場所（Settings.kill_flag_path）

.env 作成の流れ
--------------
- 実行: python -m kabusys.config_setup
- 完了後: python -m kabusys.validate_config で検証
  - --strict を付けると警告もエラー扱い（exit 1）

使い方（実行例）
----------------

- ExecutionEngine 起動
  - 簡易:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は専用ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBroker を用います。
    - 起動時に data/stop_requested.flag があれば起動をキャンセルします。
    - 実行中は data/execution.pid に PID を書き、同ディレクトリに stop フラグが作られると停止を試みます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒）。例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しません）。

- .env の検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースパスを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます。

- AI 機能（ライブラリ利用例）
  - ニューススコアリング:
    - from datetime import date
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, date(2026,4,1), api_key="sk-...")  # OPENAI_API_KEY が環境変数にある場合は api_key 引数省略可
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026,4,1), api_key="...")

停止・Kill Switch
-----------------
- Kill Switch は data/kill.flag に理由文字列を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch クラス）。
- run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag を見ることで外部からの停止（stop_requested.flag を作る）に反応します。
- Settings.kill_flag_clear_on_start=1 を有効にすると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。

ログ
---
- ログ出力は kabusys.utils.logging_setup.setup_logging により統一管理されます。
- デフォルト: logs/<app_name>.log を日次ローテーションで出力（30日分保持）。
- コンソール出力は stdout を使用します。

開発・テストのヒント
--------------------
- モジュール単体は関数呼び出しで利用できます（例: research.calc_momentum、portfolio.calc_position_sizes）。
- MonitoringEngine には run_once() があり、単発実行で各モニタの動作を検証できます（ユニットテストに便利）。
- OpenAI 呼び出し部分は関数の差し替え（patch）やモックが想定されており、テストが容易です。

ディレクトリ構成
----------------
（プロジェクトルートの src/kabusys を基準に一部抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py  (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py   (参照あり)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/            (発注周りのモジュール群: BrokerClientFactory 等)
    - data/                 (実行時に生成される sqlite / duckdb / pid / flag ファイル 等)
    - logs/                 (デフォルトログ出力先)

（注）上記は主要ファイルの一覧です。実装はさらにモジュール分割されています。

ライセンス / バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はプロジェクトルートの LICENSE 等を参照してください（本リポジトリには含まれていない場合があります）。

補足（設計上の注意点）
--------------------
- 監視（Monitoring）は常に Settings.sqlite_path（本番監視 DB）を参照します。KABUSYS_ENV によらず本番の監視 DB を使う設計になっています。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- OpenAI を使う機能は API キーの有無・サーバーエラーに対してフォールバック・リトライロジックを実装しており、API 失敗時もシステム全体が停止しないよう配慮されています。

お問い合わせ
------------
不明点や拡張要望があればリポジトリの Issue や担当者へご連絡ください。