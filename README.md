README
=====

概要
----
KabuSys は日本株向けの自動売買フレームワークです。取引エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築・サイズ決定ロジック、リサーチ/ファクター計算、LLM を用いたニュースセンチメント評価（OpenAI）などを含むモジュール群で構成されています。

主な設計方針:
- 本番／ペーパートレードを環境変数で切り替え（KABUSYS_ENV）。
- DuckDB を分析用データストア、SQLite を監視・発注ログ用に使用。
- .env による設定管理を提供し、対話式ウィザードで初期化可能。
- モジュールは可能な限り副作用を避け、ユニットテストしやすい純粋関数／明確な API を心がけています。

機能一覧
--------
- Execution
  - ExecutionEngine による発注処理（本番 / ペーパートレード切替）。
  - RiskManager, OrderManager, Reconciler などの実務的な依存コンポーネント。
  - ペーパートレード時は MockBrokerClient を利用し data/paper_trading.db に記録。

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度の監視。
  - TradeMonitor: 注文の滞留、約定異常などの監視（trade_logs を参照）。
  - RiskMonitor: ドローダウンやポジション数上限の監視とアラート記録。
  - KillSwitch: しきい値超過時に data/kill.flag を書き込んで Engine を停止させる仕組み。
  - MonitoringEngine: 各 Monitor をまとめたポーリングループ。

- Data / Research
  - ファクター計算（Momentum / Volatility / Value 等） — DuckDB を用いた SQL/Python 実装。
  - Forward returns / IC 計算 / 統計サマリ等の探索ツール。

- Portfolio Construction
  - 候補選定、等配分・スコア配分、リスクベースのポジションサイズ決定。
  - セクターキャップやレジーム乗数の適用。

- AI（OpenAI）
  - ニュース NLP（news_nlp）: raw_news を LLM でセンチメント評価し ai_scores に書き込み。
  - Regime Detector（regime_detector）: ETF MA とマクロニュースを統合して市場レジーム判定。
  - 再試行・バリデーションや部分書き込みによるフェイルセーフ実装。

- ユーティリティ
  - config_setup: .env を対話的に作成するウィザード。
  - validate_config: .env と config/*.yaml の事前検証 CLI。
  - logging_setup: 共通のログ設定（コンソール + 日次ローテートファイル）。
  - process_priority: psutil を使ったプロセス優先度/CPU affinity 設定。

セットアップ手順
--------------
1. クローン / ワークディレクトリ準備
   - リポジトリをクローンし、python 仮想環境を作成して有効化します。
     例:
       python -m venv .venv
       source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール
   - requirements.txt がある場合:
       pip install -r requirements.txt
   - 主に必要なパッケージ（目安）:
       pip install duckdb psutil openai pyyaml

   注: OpenAI を使う機能を利用する場合は openai パッケージが必要です。YAML の検証を行う場合は PyYAML が必要です。

3. 環境変数（.env）設定
   - 対話式ウィザードで生成:
       python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに配置）。必須項目:
       JQUANTS_REFRESH_TOKEN=...
       KABU_API_PASSWORD=...
     推奨・デフォルト値:
       KABUSYS_ENV=development  # development | paper_trading | live
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       KILL_FLAG_CLEAR_ON_START=0

   - 自動ロード:
     プロジェクト起動時に .env/.env.local が自動で読み込まれます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリの作成（必要に応じて）
   - logs/ や data/ に書き込み権限を与えてください。ログはデフォルトで logs/<app_name>.log に出力されます。

使い方
------
主なエントリポイント（モジュールとして実行）:

- ExecutionEngine を起動
    KABUSYS_ENV に応じて本番 or paper_trading が切り替わります。
    python -m kabusys.run_execution

  動作ポイント:
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に注文履歴を保存します。
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
  - 実行中に stop フラグを立てると Engine に停止シグナルが送られます（stop は flag ファイル削除で解除されません）。

- Monitoring のポーリングループ起動
    python -m kabusys.run_monitoring

  動作のカスタマイズ:
  - ポーリング間隔を環境変数で変更:
      MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    （1 秒以上の正の整数が必要。無効値はデフォルト 60 秒にフォールバックします）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（Monitoring は環境に依らず本番 DB を参照する設計）。

- 設定検証
    python -m kabusys.validate_config
  オプション:
    --strict  # 警告も FAIL として扱う

- .env ウィザード（対話型）
    python -m kabusys.config_setup

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH を指定すると PAPER_TRADING_SQLITE_PATH の代わりに使用できます。

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  例（スクリプトから呼ぶ）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1))  # OPENAI_API_KEY が設定されている必要あり

運用・停止フロー
- Kill Switch:
  - RiskMonitor 等が閾値超過を検出すると data/kill.flag を書き込みます。ExecutionEngine は起動時に kill flag を確認し、存在する場合は起動しません。Kill flag は明示的に削除する必要があります。
- 停止フラグ:
  - run_execution/run_monitoring は data/stop_requested.flag の存在を検知して終了します（停止要求用）。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイルを生成します（Settings.pid_file_path、デフォルト data/execution.pid）。

主な環境変数（抜粋）
------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用上重要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: AI 機能を使う場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）。本番では 0 推奨。

ディレクトリ構成
----------------
以下は主要ファイル／パッケージの構成（src/kabusys 以下）です。実際のリポジトリでは pyproject.toml 等がルートにあります。

- src/kabusys/
  - __init__.py
  - config.py               # 環境変数読み込み・Settings
  - config_setup.py         # .env 対話式ウィザード
  - validate_config.py      # 設定検証 CLI
  - run_execution.py        # ExecutionEngine 起動スクリプト
  - run_monitoring.py       # Monitoring ポーリングループ起動スクリプト

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py      # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py           # ニュースセンチメント（OpenAI）
    - regime_detector.py    # レジーム判定（OpenAI + MA）

  - data/                   # 実行時に使用するファイル（デフォルト）
    - monitoring.db (default for SQLITE_PATH)
    - paper_trading.db (for paper trading)
    - kabusys.duckdb (default for DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

ログについて
------------
- setup_logging() により logs/<app_name>.log に日次ローテーションで出力します（30日保持）。
- コンソール出力は stdout を使用します。
- LOG_DIR 環境変数でログディレクトリを変更可能。ファイルハンドラ作成に失敗した場合はコンソールのみで継続します。

注意事項 / 運用上のヒント
------------------------
- 本番運用時は KABUSYS_ENV=live に設定し、.env の値（API トークン等）を厳重に管理してください。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に既存の kill.flag を自動でクリアしますが、本番では誤って Kill Switch を無効化するリスクがあるため 0 を推奨します。
- OpenAI API を利用する機能は API のエラー耐性（リトライ、フェイルセーフ）を実装していますが、API キー管理とコスト制御に注意してください。
- ペーパートレードは本番データベースと完全分離される設計です（デフォルトで data/paper_trading.db）。実運用前に構成を確認してください。

貢献 / 開発
------------
- 新しい依存を追加したら requirements.txt を更新してください。
- config/*.yaml は validate_config でチェックできます。YAML 検証には PyYAML が必要です。
- ユニットテストを追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 .env 読み込みを抑制すると便利です。

補足: サンプル .env の例
-----------------------
下記は最小構成例（プロジェクトルートの .env）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

以上。README に不足している点や、特定モジュールの API ドキュメント（例: ExecutionEngine の設定オプションや RiskConfig のパラメータ）を追加で作成したい場合は知らせてください。