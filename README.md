KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究ツール群です。本リポジトリには以下を含みます（抜粋）:

- 注文実行エンジン（ExecutionEngine）
- 監視用コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI 支援モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、Paper Trading レポート生成）

特徴（主な機能）
----------------
- 実行環境分離:
  - KABUSYS_ENV によって動作モードを切替（development / paper_trading / live）。
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。
- 監視・Kill Switch:
  - System/Trade/Risk の監視を行い、閾値に達した場合に data/kill.flag を書き込んで ExecutionEngine を安全に停止できます。
  - 実行プロセスは stop_requested.flag による即時停止に対応（run_monitoring/run_execution が参照）。
- ポートフォリオ構築:
  - 候補選定、等重/スコア重み、リスクベースのポジションサイジング、セクター上限適用など。
- 研究用機能:
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）と IC/統計解析。
- AI モジュール:
  - OpenAI（gpt-4o-mini 等）を使い、ニュース記事のセンチメント集計や市場レジーム判定を行う（API キー必須）。
- ロギング:
  - 統一的なログ設定（コンソール + 日次ローテートファイル、デフォルト: logs/<app>.log）。

前提（推奨環境）
----------------
- Python 3.10 以上（型注釈に | を使用しているため）
- pip などで次のパッケージをインストールしてください（最低限）:
  - duckdb, psutil, openai
  - 開発時や設定検証に PyYAML があると便利（validate_config が YAML のパースを行います）

例:
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
3. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML
4. .env を作成（推奨: 対話式ウィザードを使用）
   python -m kabusys.config_setup
   → ウィザードで必要な値を入力するとプロジェクトルートに .env が作成されます。
5. 設定検証（任意）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モードの SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ロギング制御
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効。デフォルト "0"）

使い方（主要 CLI / スクリプト）
----------------

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に書き込みます。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 停止は data/stop_requested.flag を作成する（例: touch data/stop_requested.flag）か、kill.flag により段階的停止が発動します。
    - PID ファイルは data/execution.pid に書き出されます（設定で変更可）。

- 監視ポーリング起動（SystemMonitor のループ）
  python -m kabusys.run_monitoring
  環境変数:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  注意:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを残します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）

- 研究 / AI の呼び出し（ライブラリとして）
  例: ファクター計算
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, date(2026,4,1))
  AI:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・Kill フラグについて
-------------------------
- stop_requested.flag
  - run_monitoring.py / run_execution.py がループ中でこれを検出すると即時終了します。
  - パス: project_root/data/stop_requested.flag（スクリプトはこのファイルを参照します）
  - 例（UNIX）: touch data/stop_requested.flag

- kill.flag
  - KillSwitch が危険状態（ドローダウン超過、ポジション上限超過など）を検出すると data/kill.flag に理由を書き込みます。
  - ExecutionEngine はこの kill.flag を検出して安全に停止処理を行います。
  - 手動でトリガーする場合は内容を書き込んでください（注意: 本番での利用は慎重に）。

ログ
----
- デフォルトのログディレクトリ: logs/
- 各アプリケーションは logs/<app_name>.log に日次ローテートで書き込み（30日保持）。
- 例: logs/execution.log, logs/monitoring.log
- コンソール出力は stdout に出ます（cron 等での一括リダイレクトに配慮）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理（自動 .env ロードを含む）
- config_setup.py           — .env 作成ウィザード（対話式）
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- execution/                 — 注文関連ロジック（broker_factory, execution_engine, order_manager 等）
- monitoring/
  - monitoring_db.py        — SQLite 永続層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
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
- tools/
  - paper_verification_report.py

よくあるトラブルと対処
---------------------
- 必須環境変数が未設定:
  - python -m kabusys.validate_config を実行し、エラー/警告を確認してください。
- DuckDB / SQLite ファイルが見つからない:
  - デフォルトは data/kabusys.duckdb / data/monitoring.db / data/paper_trading.db です。.env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API 呼び出しエラー:
  - OPENAI_API_KEY を設定してください。API のレート制限やネットワーク障害に対してはリトライロジックが入っていますが、キー未設定だと機能しません。
- ログディレクトリ作成失敗:
  - 権限等で logs/ が作れない場合、コンソール出力のみで継続します。必要なら LOG_DIR 環境変数で別ディレクトリを指定してください。
- 実行プロセスが停止しない / フラグが残る:
  - data/stop_requested.flag や data/kill.flag を手動で確認・削除してください（KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で削除されますが、本番は 0 推奨）。

セキュリティ注意
----------------
- .env は秘密情報を含みます（API キー、パスワード等）。絶対にバージョン管理にコミットしないでください。
- 本番（KABUSYS_ENV=live）では kill フラグ等操作に十分注意してください。

開発者向けメモ
----------------
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env / .env.local を自動で読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で実行可能。既存スキーマにカラムが無い場合は ALTER TABLE による簡易マイグレーションを行います。
- ロギング:
  - 全アプリケーションは setup_logging(app_name=...) を呼ぶことで統一されたログ設定を使います。

サンプル .env（例）
-------------------
# 簡易サンプル（実運用前に正しい値で上書きしてください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。詳細な挙動や内部設計は各モジュールの docstring / コメントを参照してください。何か特定の操作手順やトラブルシュートを詳細に知りたい場合は教えてください。