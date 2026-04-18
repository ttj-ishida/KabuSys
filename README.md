KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・検証・監視を目的とした内部ライブラリ群と起動スクリプトを提供するプロジェクトです。  
主な機能は発注エンジンの起動、システム＆取引の監視、ポートフォリオ構築、ファクター計算、ニュース NLP によるセンチメント評価、ペーパートレード用の検証レポート生成などです。

特徴
----
- ExecutionEngine（発注エンジン）／ペーパートレード分離
  - KABUSYS_ENV により development / paper_trading / live を選択可能
  - paper_trading モードでは MockBrokerClient を使用し専用 SQLite（data/paper_trading.db）に記録
- 監視（Monitoring）
  - システムリソース、プロセス生存、データ鮮度、取引ログ、リスク監視（ドローダウン・ポジション上限）を定期的にチェック
  - kill.flag による外部からの停止（Kill Switch）
- ポートフォリオ構築
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数などの純粋関数実装
- リサーチ（DuckDB ベース）
  - モメンタム、バリュー、ボラティリティなどのファクター計算（prices_daily / raw_financials テーブル参照）
  - 将来リターン、IC、統計サマリ等の分析ツール
- AI（OpenAI）連携
  - ニュースを LLM（gpt-4o-mini 相当）で評価し ai_scores に保存（スコアのクリップ、リトライ、バリデーション実装）
  - 市場レジーム判定モジュール（ETF の MA200 とマクロニュースセンチメントの合成）
- ユーティリティ
  - .env 対話型ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

前提・依存
-----------
- Python 3.10+
  - 型注釈に | 演算子（PEP 604）を使用しているため
- ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML （config/*.yaml の構文チェックを行う場合）
- SQLite（標準ライブラリで利用可）
- ネットワークアクセス（OpenAI API を使用する場合）

セットアップ手順
----------------
1. リポジトリをクローンし、パッケージの作業ディレクトリへ移動:
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリに含まれていない場合は上の個別インストールで代替）。

4. データ／ログ用ディレクトリを準備（起動時に自動作成されることもありますが事前作成推奨）:
   - mkdir -p data logs

5. .env を作成:
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは手動で .env ファイルを作成（必須変数は下記参照）

重要な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モード時の専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（news/regime）を利用する場合に設定

設定検証
-------
.env や config/*.yaml の基本チェックを行う:
- python -m kabusys.validate_config
- 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 実際に発注（kabu API 経由）
  - 起動時、data/execution.pid に PID を書き込みます。data/stop_requested.flag があると起動せず終了します。
  - 停止は data/stop_requested.flag を作成する（または Kill Switch によって data/kill.flag が書かれる）ことで行います。

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することでループを抜けます

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ系（プログラム的に利用）
  - ニュースセンチメント（ai）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - ファクター計算（research）:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

ログ・ファイル
--------------
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。setup_logging が全スクリプトで使われます。
- PID / フラグ:
  - data/execution.pid: ExecutionEngine の PID（実行中）
  - data/stop_requested.flag: 監視ループや実行ループを穏やかに停止させるためのフラグ（作成で停止）
  - data/kill.flag: Kill Switch による強制停止シグナル（ExecutionEngine に停止を指示）

ディレクトリ構成（抜粋）
----------------------
リポジトリの主要なモジュール配置（src/kabusys 以下の抜粋）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込み
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py            (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            (実装あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項・運用上のヒント
---------------------
- KABUSYS_ENV を "live" に設定する場合は特に注意してください。validate_config は本番向けの追加警告を出します。
- paper_trading モードでは本番 DB に書き込まないように設計されていますが、環境変数で SQLite パスを誤って本番 DB に指してしまわないよう確認してください。
- OpenAI を使う機能は API 呼び出しの失敗に備え、フェイルセーフ（スコア 0 にフォールバック、部分失敗の保護）を実装しています。ただし API キーやレート制限の管理は運用で注意してください。
- ローカルで開発・テストする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動ロードを抑制できます（テストコード実行時など）。

ライセンス・貢献
----------------
（この README にはライセンス情報は含まれていません。リポジトリの LICENSE ファイルを参照してください。）

以上。必要であれば README にサンプル .env のテンプレート、推奨 requirements.txt、systemd / cron などでのデーモン化手順、ユニットテストの実行方法等を追加で作成できます。どの情報を追記しますか？