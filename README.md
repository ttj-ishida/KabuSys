KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視機能を備えた小規模なシステムです。  
本リポジトリは以下の機能群を含みます（主要コンポーネント）:

- ExecutionEngine（発注・リスク管理・注文管理）起動スクリプト
- Monitoring（システム稼働・注文・リスク監視）ポーリングループ
- Portfolio construction（銘柄選定・重み付け・株数計算）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- Paper Trading 検証レポート生成ツール

主な特徴
-------
- 設定は .env（自動ロード）および config/*.yaml で管理
- 本番/ペーパートレード用 DB を分離（paper_trading モード時）
- DuckDB を利用した分析用データ処理（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）によるニュースセンチメント & マクロ評価機能
- Monitoring 系は SQLite ベースで監視ログを永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
- ログはコンソール出力 + 日次ローテートされたファイル出力（logs/*.log）

セットアップ手順
----------------
前提:
- Python 3.10 以上（コードは PEP 604 の union 型 (A | B) を使用しています）
- git が使える環境

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要ライブラリをインストール
   必要最小限のパッケージ:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML (config/*.yaml の内容検証に必要だが必須ではない)

   例:
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください）

4. 初期設定（.env）作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（リポジトリルートに配置）
     必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     推奨/デフォルト例:
       - KABUSYS_ENV=development
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - LOG_LEVEL=INFO
     注意: .env は絶対にリポジトリにコミットしないでください。

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けるとワーニングもエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. 必要ディレクトリの作成（通常は自動作成されますが手動で作る場合）
   - mkdir -p data logs

使い方（主要スクリプト）
-----------------------
- 環境作成ウィザード（.env を生成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- Monitoring（監視ポーリングループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
    - 実行中は data/stop_requested.flag が存在するとループを終了します
  - Monitoring は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の時は MockBrokerClient を使用し、paper SQLIte DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録します
  - 実行時の停止制御:
    - data/stop_requested.flag を作成するとエンジン停止をトリガー
    - Kill Switch は data/kill.flag によって外部から停止要求を行います
  - 実行時に data/execution.pid に PID を書きます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定する必要があります
  - プログラム内から:
    - from kabusys.ai import score_news
    - kabusys.ai.regime_detector.score_regime を使用

運用・停止関連
---------------
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch は risk チェック等の条件でこのファイルを書き込み、ExecutionEngine に停止を促します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 にしていると自動でクリアします（本番では 0 推奨）

- stop_requested.flag
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します

ログ
----
- デフォルトは logs/<app_name>.log（例: logs/monitoring.log, logs/execution.log）
- 環境変数:
  - LOG_DIR: ログ保存ディレクトリを上書き
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- setup_logging() ユーティリティが統一的にログ設定を行います（コンソール stdout + 日次ローテートファイル）

主要モジュール一覧（抜粋）
-------------------------
- kabusys.config
  - 設定の解決と .env 自動ロードロジック
- kabusys.config_setup
  - .env 対話式ウィザード
- kabusys.validate_config
  - 環境・設定検証 CLI
- kabusys.run_monitoring
  - Monitoring のポーリングループ起動スクリプト
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（paper_trading 切替あり）
- kabusys.utils.logging_setup
  - ロギング初期化
- kabusys.utils.process_priority
  - プロセス優先度 / CPU affinity 設定
- kabusys.monitoring.*
  - monitoring_db, system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, alert_manager（アラートロジック）
- kabusys.portfolio.*
  - portfolio_builder, position_sizing, risk_adjustment（純粋関数群）
- kabusys.research.*
  - factor_research, feature_exploration（DuckDB を用いたファクター計算 / IC 等）
- kabusys.ai.*
  - news_nlp（ニュースセンチメント）, regime_detector（市場レジーム判定）
- kabusys.tools.paper_verification_report
  - Paper Trading 検証レポート生成

ディレクトリ構成（抜粋）
--------------------
以下はリポジトリ内の主要ファイル/ディレクトリ構成（本ドキュメント作成時点での抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - (その他: execution/, data/, strategy/ 等のサブパッケージ)

補足（運用上の注意）
-------------------
- .env 自動ロード:
  - プロジェクトルートに .env / .env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- データベース:
  - デフォルト DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
- OpenAI の呼び出しは外部 API を利用します。API キー・コストに注意してください。API 呼び出しはリトライ・バックオフやフェイルセーフ実装がありますが、失敗時はスコアを 0.0 にフォールバックする設計です。
- 本番運用（KABUSYS_ENV=live）の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を慎重に設定してください。

ライセンス / バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンスはリポジトリに含まれる LICENSE ファイルを参照してください（本 README には未記載）。

問い合わせ / 開発者向けメモ
-------------------------
- 追加の実装（execution/broker, order_manager 等）は execution パッケージに集約されます。テストやローカル実行時は KABUSYS_ENV=development / paper_trading を活用してください。
- DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）に基づく前処理 / ETL を実行しておく必要があります（データ投入パイプラインは別途実装）。

以上。運用や導入で不明点があれば、どの部分を詳しくドキュメント化するか教えてください。