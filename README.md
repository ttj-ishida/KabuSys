README
======

概要
----
KabuSys は日本株の自動売買システム用ライブラリ群および実行スクリプトのコレクションです。  
主に以下を提供します。

- 発注やリスク管理を行う ExecutionEngine（run_execution.py）
- システム／取引状況をポーリングして監視・アラート・Kill Switch を制御する Monitoring（run_monitoring.py）
- ポートフォリオ構築・ポジションサイジング・セクター制約などの純粋関数群（kabusys.portfolio）
- DuckDB を用いたファクター計算やリサーチユーティリティ（kabusys.research）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（kabusys.ai）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、検証ツール 等）
- ペーパートレード検証用レポート生成スクリプト等のツール群

特徴
----
- 本番／ペーパートレードの DB を分離（KABUSYS_ENV により paper_trading 用 DB を使用）
- DuckDB を分析用 DB として採用（ファクター計算やリサーチ処理向け）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントとレジーム判定（フェイルセーフ設計）
- 監視: CPU/メモリ/ディスク、データ鮮度、滞留注文、ドローダウン・ポジション数監視、Kill Switch
- ログはコンソールと日次ローテートファイルに出力（logs/*.log）
- 設定ウィザード（.env の対話式作成）と起動前設定検証 CLI を備える

前提 / 依存
-------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に必要）
- OS: Linux / macOS / Windows（プロセス優先度や CPU affinity の機能はプラットフォーム差あり）

推奨インストール例
-----------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意で: pip install pyyaml

セットアップ手順
----------------

1. プロジェクトルートを確認（.git または pyproject.toml があるディレクトリをルートとみなします）。

2. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-xxxx (AI 機能を使う場合)

   注: 自動ロード（kabusys.config）がプロジェクトルートを検出すると .env/.env.local を環境変数に読み込みます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

4. 必要なディレクトリの作成（ログやデータ保存先）
   - mkdir -p data logs

主要な実行方法
--------------

- ExecutionEngine を起動（実際に注文を発行する / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中は PID を data/execution.pid（デフォルト）に書きます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - 停止には data/stop_requested.flag を作成してください（Monitoring はこのフラグを見てループを終了します）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db（または env の PAPER_TRADING_SQLITE_PATH）

API / ライブラリ的な使い方（主要関数）
----------------------------------

- AI スコアリング
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（duckdb.connect(...)）を渡し、target_date のニュースをスコアして ai_scores テーブルに書き込みます。
    - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。

  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF(1321) の MA200 とマクロニュースを合成して market_regime を更新します。

- リサーチ / ファクター
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)

- ポートフォリオ構築 / サイズ決定
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_equal_weights(...)
  - kabusys.portfolio.calc_score_weights(...)
  - kabusys.portfolio.calc_position_sizes(...)
  - kabusys.portfolio.apply_sector_cap(...)
  - kabusys.portfolio.calc_regime_multiplier(...)

- ログ設定ユーティリティ
  - from kabusys.utils.logging_setup import setup_logging
  - setup_logging(app_name="execution")

- プロセス優先度 / CPU affinity
  - from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity

監視・停止関連ファイル（運用時の注意）
-------------------------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py がループを終了するために監視するファイル。存在すると起動を中断したり実行を停止します（外部から停止命令を出す際に使用）。
- data/kill.flag
  - KillSwitch が条件を満たした際に書き込むファイル。ExecutionEngine に対する停止シグナル。Settings.kill_flag_clear_on_start を 1 にしておくと起動時に自動でクリアする（本番は 0 推奨）。
- data/execution.pid
  - 実行エンジンの PID を保持するデフォルトパス（Settings.pid_file_path で変更可）。

ログ
----
- デフォルトログディレクトリ: logs/
- ログファイル: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログはコンソール stdout と日次ローテーションファイルの両方に出力されます。

データベース（デフォルトパス）
-----------------------------
- DuckDB: data/kabusys.duckdb （Settings.duckdb_path）
- Monitoring SQLite: data/monitoring.db （Settings.sqlite_path）
- Paper trading SQLite: data/paper_trading.db （Settings.paper_sqlite_path, KABUSYS_ENV=paper_trading 時使用）

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの src/kabusys 配下のおおまかな構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（監視用）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       (実装ファイルあり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       (実装ファイルあり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時に使用するファイル（logs, DB, flag など。リポジトリに含まれない場合は作成）

（注）一部ファイルはここでは省略していますが、上記が主要コンポーネントです。

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では Kill Switch・LINE 通知設定等を十分に確認してください。
- .env は絶対に Git にコミットしないこと（config_setup も README に明示）。
- OpenAI API を使う機能は API キーの課金に注意して使用してください。API 失敗時はフェイルセーフとして処理を継続する設計になっていますが、運用ポリシーを作ってください。
- DuckDB / SQLite ファイルのバックアップ・保全を検討してください（誤操作でデータが失われるリスク）。

トラブルシューティング
----------------------
- PyYAML がないと config/*.yaml の内容検証がスキップされます（validate_config が警告を出します）。インストールするには pip install pyyaml。
- ログディレクトリ作成失敗時はコンソールログのみになります。パーミッションを確認してください。
- psutil の一部機能は権限不足で失敗する可能性があります（プロセス優先度変更など）。管理者権限が必要な場合があります。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

---

必要であれば、README に付録で .env.example の例や起動コマンドの具体的なデプロイ手順（Systemd ユニット例、Dockerfile、監視・バックアップ運用設計）を追加できます。どの情報を優先して追記しますか？