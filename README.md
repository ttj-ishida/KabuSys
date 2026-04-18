README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの一部実装です。
主な目的は以下の通りです。

- 自動売買エンジン（ExecutionEngine）と実行周りの管理
- システム監視（Monitoring）とアラート / Kill Switch 機能
- ポートフォリオ構築／リスク調整／ポジションサイジングの純粋関数群
- 研究用ファクター計算・特徴量探索（DuckDB を利用）
- ニュース NLP を利用した銘柄スコアリング・レジーム検出（OpenAI 経由）
- ペーパートレード検証レポート生成ツール

このリポジトリは主にライブラリ／起動スクリプト群で構成され、.env による環境設定で挙動を切り替えます。

主な機能
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV により paper_trading（MockBroker を使用）と live を切替。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔変更可。
- 環境設定管理
  - config_setup.py: 対話式ウィザードで .env を生成/更新。
  - validate_config.py: .env と config/*.yaml の簡易検証 CLI。
- 監視関連
  - monitoring_engine.py: 各モニタをまとめて定期実行、アラート／Kill Switch を評価。
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 個別モニタの実装（SystemCheck / TradeCheck / RiskCheck）。
  - monitoring_db.py: SQLite ベースの永続層（テーブル作成・マイグレーション含む）。
  - kill_switch.py: data/kill.flag により ExecutionEngine を停止させる仕組み。
- ポートフォリオ
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定、重み付け、株数決定、セクター制限、レジーム乗数など。
- 研究（Research）
  - factor_research, feature_exploration: DuckDB 上でファクター計算、将来リターン・IC・統計サマリなど。
- AI
  - news_nlp.py, regime_detector.py: OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント評価・レジーム判定。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）。

前提 / 必要要件
---------------
- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 任意 / 機能により必要:
  - PyYAML（config/*.yaml の内容検証用。未インストール時は検証をスキップします）

インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を用意する。
2. 依存パッケージをインストール（上記参照）。
3. 環境変数を設定する:
   - 対話式ウィザードで .env を作る（推奨）:
     python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照してください）。主要なキー:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_DIR / LOG_LEVEL（ログ設定）
     - その他は config_setup の質問を参照

4. 設定検証（起動前確認）:
   python -m kabusys.validate_config
   --strict オプションを付けると警告も失敗扱いとなります。

5. データディレクトリを作成（必要に応じて）:
   mkdir -p data logs

基本的な使い方
--------------
- ExecutionEngine を起動:
  - 本番相当（KABUSYS_ENV=live）または開発:
    python -m kabusys.run_execution
  - ペーパートレード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    → paper_trading の場合、MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます。

- Monitoring を起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に production 用の sqlite_path（Settings.sqlite_path）を使います。

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。

- AI 機能（ニュース NLP / レジーム判定）:
  - OPENAI_API_KEY を設定してください（env またはアプリケーション引数）。
  - news_nlp.score_news(conn, target_date, api_key=None) でスコアリングを実行。
  - regime_detector.score_regime(conn, target_date, api_key=None) でレジーム判定を実行。

シグナル / フラグファイル
------------------------
- 停止制御:
  - data/stop_requested.flag: run_monitoring/run_execution はこのファイルの存在を確認し、あれば安全に停止します（運用停止用）。
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 側は Settings.kill_flag_path を参照して停止します。
- PID ファイル:
  - data/execution.pid（Settings.pid_file_path デフォルト）に ExecutionEngine の PID を書きます。

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler、30 日保持）。
- 環境変数 LOG_DIR / LOG_LEVEL で変更可能。
- setup_logging(app_name="execution"|"monitoring") が一貫したロギング設定を提供します。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - trade_monitor.py  (参照実装あり)
    - execution/               — 発注系コンポーネント（Engine, BrokerFactory 等）
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/                    — 実行時に使用されるデータ/フラグ/DB（デフォルト path）
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

注意点 / 運用上のヒント
---------------------
- 開発時は KABUSYS_ENV=development を使用し、実際の発注は発生しないようにしてください。
- paper_trading 環境は本番 DB と分離され、デフォルトで data/paper_trading.db を使用します。
- OpenAI を利用する AI 機能は外部 API を呼ぶため API キーと通信環境が必要です。API 呼び出しはリトライやタイムアウト処理を含みますが、運用ではレート制限やコストにも注意してください。
- monitoring_db.init_monitoring_db() はテーブル作成と簡単なスキーママイグレーションを行います。既存 DB を保護するための仕組みを備えていますが、運用前にバックアップを取ることを推奨します。
- run_execution / run_monitoring は起動時にプロセス優先度を "high" にしようとします（psutil を使用）。権限がない場合は警告が出ますが継続します。

貢献 / 開発
------------
- 関数群はモジュール単位で分離してあり、ユニットテストが書きやすい構成です（純粋関数は副作用無し）。
- AI 呼び出しは内部でラッパー関数を使っているので、テスト時は該当関数をモックすることで外部依存を切り離せます（例: unittest.mock.patch）。

ライセンス
---------
（このリポジトリにライセンスファイルがある場合はそちらを参照してください）

問い合わせ
----------
不明点や実装の意図についてはコード内の docstring / コメントを参照してください。必要であれば追加のドキュメント化やサンプルを用意します。