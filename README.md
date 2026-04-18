KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買・調査・監視を目的とした小規模フレームワークです。  
本リポジトリには下記のような主要機能群が含まれます。

- ExecutionEngine（発注実行ループ、paper_trading 用のモック対応）
- Monitoring（システム稼働・注文状態・リスク監視、Kill Switch）
- Portfolio construction（候補選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算、特徴量解析）
- AI 補助（ニュース NLP によるセンチメント集約、レジーム判定）
- ツール（Paper Trading 検証レポート生成、設定ウィザード、設定検証 CLI）
- 永続化：SQLite（監視・ペーパートレード DB） + DuckDB（時系列・分析用）

主な機能一覧
-------------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
  - PID ファイル管理、停止フラグ検知に対応
- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status / trade_logs / risk_logs / dashboard を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- monitoring モジュール
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を備え、MonitoringEngine がまとめて実行
  - MonitoringDB（SQLite）に読み書きする永続層
- portfolio モジュール
  - 候補選定（select_candidates）、等重・スコア重み算出、ポジションサイズ計算、セクター上限適用、レジーム乗数
- research モジュール
  - DuckDB 上の prices_daily / raw_financials からファクター（Momentum/Volatility/Value）計算、将来リターン、IC、統計要約
- ai モジュール
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースを銘柄別にスコア化して ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF / マクロニュースを組合せて日次レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成
- 設定管理ツール
  - config_setup.py: 対話式 .env ウィザード（.env の初期作成・更新）
  - validate_config.py: .env と config/*.yaml の基本チェックを行う CLI

動作要件（概略）
----------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（YAML 検証など）
  - PyYAML
- その他: ネットワーク接続（kabuステーション API / OpenAI を利用する場合）、適切な環境変数設定

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証が必要であれば）pip install PyYAML

   *注: requirements.txt が存在する場合は pip install -r requirements.txt を使用してください。*

4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考にしてください）
   - 自動ロード: プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env/.env.local が自動ロードされます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict オプションをつけると警告も失敗扱いになります。

使い方（実行例）
----------------
- ExecutionEngine の起動（本番 or paper_trading を .env で指定）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBroker を利用します。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（例: export MONITOR_POLL_INTERVAL=120）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- ライブラリ的に AI スコアを実行（プログラム内から）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

重要な環境変数（主要なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用）
- PAPER_FILL_MODE — ペーパートレードのフィルモード（instant/partial/never/reject。デフォルト: instant）
- OPENAI_API_KEY — OpenAI API 呼び出しに使用
- MONITOR_POLL_INTERVAL — run_monitoring ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=有効。※本番では 0 推奨）

停止・Kill フラグ
-----------------
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を監視しており、存在するとループを終了します。
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（監視側が条件を満たすと書き込む）。
- 実行時の PID ファイル: data/execution.pid（パスは Settings.pid_file_path で上書き可能）

ログ
----
- ログは stdout とファイル（デフォルト logs/<app_name>.log）に出力されます。ファイルは日次ローテート（30日保持）。
- LOG_DIR 環境変数でログディレクトリを変更できます。

DB 初期化
--------
- monitoring の起動時に init_monitoring_db() が呼ばれて必要なテーブルの作成と簡易マイグレーション（列追加）を行います。通常手動での初期化は不要です。

ディレクトリ構成（主なファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (実装の詳細は省略)
    - kill_switch.py
    - alert_manager.py (実装の詳細は省略)
  - execution/               — 発注関連（Engine / BrokerFactory / OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/ and other modules as above

注意事項 / 運用上のヒント
-----------------------
- KABUSYS_ENV=live を使うと実際に発注が行われます。設定の確認（特に API キー・決済可能な資金量）を十分に行ってください。validate_config の警告は無視しないでください。
- .env は決してリポジトリにコミットしないこと（config_setup.py のヘッダにも注意喚起あり）。
- OpenAI API を利用する機能は API キーの利用量とレスポンスタイムに依存します。適切なエラーハンドリングとコスト管理を行ってください。
- paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。本番 DB を誤って上書きしないためにこの運用を活用してください。
- MONITOR_POLL_INTERVAL を小さくし過ぎるとログや API 呼び出しが多発するため注意してください。

開発者向け
----------
- モジュールは可能な限り副作用を避ける設計（DB 初期化は明示的関数、.env 自動ロードは可否切替）をしています。
- テスト時に .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は _call_openai_api をパッチしてユニットテストを行えるように実装されています。

ライセンス・貢献
----------------
この README はコードベースのドキュメント生成を目的とした概要です。実際のライセンスや貢献フローはリポジトリの LICENSE / CONTRIBUTING ドキュメントを参照してください。

以上。必要があれば各サブモジュール（ExecutionEngine、MonitoringEngine、AI 部分など）の詳細ドキュメントやサンプル .env を追記します。どのセクションを詳しく書くか指示ください。