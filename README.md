KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。  
主な機能は以下の通りです。

- 発注エンジン（ExecutionEngine）：実際のブローカー（kabuステーション）または MockBroker を用いたペーパートレードをサポート
- 監視（Monitoring）：システム稼働状況・データ鮮度・注文挙動・リスク指標のポーリングとログ記録
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム乗数の適用
- 研究（Research）：ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン、IC 計算等
- AI モジュール：ニュースの NLP スコアリング（OpenAI）／レジーム判定のための LLM 呼び出し
- 運用ツール：環境設定ウィザード、設定検証、Paper Trading 検証レポート生成 など
- 永続化：DuckDB（分析用）・SQLite（監視・ペーパー用）対応

機能一覧
--------
主要コンポーネント（抜粋）：

- 実行／運用
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV により本番 / paper_trading を切替）
  - run_monitoring.py : SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
- 設定
  - config_setup.py : .env を対話式に生成・更新するウィザード
  - validate_config.py : .env と config/*.yaml の事前チェック CLI
  - config.Settings : 環境変数の取得・検証ロジック（デフォルトパス等を保持）
- 監視
  - monitoring/ : SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / monitoring_db（SQLite 永続化層）
  - kill.flag / stop_requested.flag による停止・Kill Switch 機構
- ポートフォリオ（純粋関数）
  - portfolio.portfolio_builder : 候補選定・重み計算
  - portfolio.position_sizing : 発注株数算出・上限/aggregate cap 処理
  - portfolio.risk_adjustment : セクターキャップ・レジーム乗数
- AI
  - ai.news_nlp : ニュースを OpenAI に投げて銘柄ごとのセンチメントスコアを生成
  - ai.regime_detector : ETF MA とマクロニュースを合成して market_regime を判定
- 研究
  - research.factor_research : momentum/value/volatility 等のファクター計算（DuckDB を使用）
  - research.feature_exploration : 将来リターン・IC・統計サマリ等
- ツール
  - tools.paper_verification_report : Paper Trading の検証レポートを生成

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repository-url>
   - cd <project-root>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - もし requirements.txt が提供されていれば:
     - pip install -r requirements.txt
   - 最低限必要になりそうなライブラリ（例）:
     - pip install duckdb psutil openai
   - （PyYAML があれば validate_config が YAML の検証を行えます）

4. 環境変数設定 (.env)
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートの .env を手動で作成
   - 主要な環境変数（.env に含める代表例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START など

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- 実行エンジン（ExecutionEngine）
  - 本番/ペーパートレード切替は KABUSYS_ENV で制御
    - 本番:
      - export KABUSYS_ENV=live
      - python -m kabusys.run_execution
    - ペーパートレード（MockBroker を使用し data/paper_trading.db に記録）:
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
  - 起動時、data/execution.pid が作成されます。停止は kill.flag（Settings.kill_flag_path 指定）または data/stop_requested.flag を作成することで検出できます。

- 監視（Monitoring）
  - デフォルトは本番 sqlite_path（Settings.sqlite_path）を使用して稼働します（KABUSYS_ENV に依存しない）。
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成するとポーリングループが安全に終了します。

- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベースパスを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を環境変数で設定しておく必要があります。
  - 例（スクリプトや REPL から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

運用上の注意
------------
- .env は絶対にリポジトリにコミットしないでください（config_setup の出力にも注意書きあり）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動で .env を読み込む挙動を無効化できます（テスト時に便利）。
- paper_trading モードは本番 DB と完全に分離して data/paper_trading.db を使用します。
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します。
- stop/kill フラグ:
  - data/stop_requested.flag : run_monitoring / run_execution のポーリングを停止するため（プロセス側で監視）
  - data/kill.flag : KillSwitch（リスクトリガー）によって ExecutionEngine 停止シグナルとして書き込まれる
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（自動クリアされてしまうため）

ロギング
--------
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用します。
- ログは標準出力（stdout）と日次ローテートファイル logs/<app_name>.log に出力されます（デフォルトでは logs/）。
- ログレベルは LOG_LEVEL 環境変数で指定（例: DEBUG, INFO, WARNING）。

データベース（デフォルトパス）
----------------------------
- DuckDB（分析用）: data/kabusys.duckdb（Settings.duckdb_path）
- SQLite（監視）: data/monitoring.db（Settings.sqlite_path）
- SQLite（Paper Trading）: data/paper_trading.db（Settings.paper_sqlite_path）

ディレクトリ構成
----------------
（抜粋）src/kabusys 以下:

- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (存在する場合)

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

- data/
  - pipeline.py
  - stats.py
  - （DuckDB テーブル作成スクリプト等）

- tools/
  - __init__.py
  - paper_verification_report.py

- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください。）

開発・拡張のヒント
-----------------
- 研究用コード（research）や portfolio モジュールは副作用を持たない純粋関数群になっており、ユニットテストが書きやすい設計になっています。
- AI 呼び出し部分はリトライ・バリデーションやフェイルセーフ（失敗時のフォールバック）を用意しています。テスト時は _call_openai_api をモックすることを推奨します。
- MonitoringDB（monitoring/monitoring_db.py）はスキーマの冪等初期化や簡単なマイグレーションロジックを持つため、既存 DB に対して安全に初期化できます。

参考コマンドまとめ
-----------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

お問い合わせ
----------
- ソースを参照して実装の詳細・拡張方法を確認してください。コード中の docstring / コメントは実装意図や注意点を多く含んでいます。必要であれば特定モジュールのドキュメント化を追加できます。