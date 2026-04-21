README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うための Python コードベースです。  
主な機能は戦略用ファクター計算、ポートフォリオ構築、注文執行エンジン（本番／ペーパートレード切替）、監視・アラート、LLM を用いたニュース NLP / レジーム判定、検証レポート生成などです。

主要コンポーネント
- execution: 注文実行エンジン（ExecutionEngine）と注文管理／リスク管理
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db に書き込む（本番 DB と分離）
- monitoring: システム状態・注文状態・リスク監視 / Kill Switch / アラート
- portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター制約などの純粋関数群
- research: DuckDB を用いたファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー 等）
- ai: OpenAI を使ったニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）
- utils: ログ設定、プロセス優先度設定などのユーティリティ
- tools: 検証レポート生成スクリプト等

主な提供ファイル／スクリプト
- python -m kabusys.run_execution : ExecutionEngine 起動スクリプト
- python -m kabusys.run_monitoring : SystemMonitor ポーリング起動スクリプト
- python -m kabusys.config_setup  : .env 対話式作成ウィザード
- python -m kabusys.validate_config: .env / config/*.yaml 等の事前検証 CLI
- python -m kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成

機能一覧
--------
- 環境管理
  - .env の自動読み込み（プロジェクトルートにある .env / .env.local を優先）
  - config_setup による対話的 .env 作成
  - validate_config による起動前設定検証（--strict で警告も失敗扱い）
- ログ
  - コンソール（stdout）と日次ローテートファイル出力（logs/<app>.log、30 日保持）
- Execution
  - 本番・ペーパートレード切替（PAPER_TRADING_SQLITE_PATH を利用）
  - 注文管理、リスク管理（max position, utilization, drawdown など）
- Monitoring
  - CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - リスク（ドローダウン、ポジション上限）監視と kill.flag 書き込みによる停止シグナル
  - 監視ログは SQLite（data/monitoring.db デフォルト）へ永続化
- AI
  - OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント集計と ai_scores への格納
  - マクロ記事を用いた市場レジーム判定（market_regime テーブル）
- Research / Portfolio
  - DuckDB 上でのファクター計算（momentum, volatility, value）
  - 候補選定、重み付け、単元株丸めを含むポジションサイズ計算
- ツール
  - Paper Trading の検証レポート生成（稼働率、約定成功率、レイテンシ等）

セットアップ手順
----------------
前提
- Python 3.9+（一部の型注釈やライブラリに依存）
- システムパッケージ: libpq 等は不要だが、psutil や duckdb のビルド要件を満たす必要あり

推奨手順（例）
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - ない場合は最低限次をインストール:
     - pip install duckdb psutil openai
     - PyYAML は validate_config の YAML 検証で任意: pip install pyyaml

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動で .env を配置（.env.example を参考に）

5. 設定検証
   - python -m kabusys.validate_config
   - すべてクリアするか、警告を確認してから次へ（本番では --strict 推奨）

6. データディレクトリの確認
   - デフォルトの DB / PID / フラグファイルパスは data/ 下に作られます。必要に応じてパスを .env で変更。

重要な環境変数
----------------
（Defaults は設定がある場合のみ記載）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (monitoring 用, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject; default: instant)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1, default: 0)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV (development | paper_trading | live; default: development)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ出力先)
- OPENAI_API_KEY (news_nlp / regime_detector 用)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、default: 60)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動 .env ロードを無効化

使い方（主要コマンド）
--------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗とする）: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定しておくと mock ブローカーを利用（DB は PAPER_TRADING_SQLITE_PATH）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変える: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照（環境に関わらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコア / レジーム判定（ライブラリ関数として）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ※ 実行には OPENAI_API_KEY の設定が必要

停止・フラグファイル
-------------------
- 停止リクエスト（run_monitoring / run_execution の終了）
  - data/stop_requested.flag を作成すると run_monitoring のループや実行フローが検出して終了します
- Kill Switch（Execution 停止）
  - monitoring.kill_switch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリア（本番では 0 推奨）

ログ
----
- デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- コンソールは stdout に出力
- 日次ローテート、30 日分保持
- LOG_DIR を指定して変更可
- setup_logging は各起動スクリプトで呼ばれます

注意事項 / 運用メモ
-------------------
- run_monitoring は monitoring DB（sqlite_path）を使用して監視ログを永続化します。monitoring は環境にかかわらず本番 sqlite_path を参照します。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB を使うか本番 DB を使うか切り替えます。
- process priority の設定（high）は psutil を使います。権限により設定が失敗することがありますがその場合は警告を出して継続します。
- OpenAI 呼び出しは外部 API 依存かつ料金が発生するため、キー管理と呼び出し回数に注意してください。
- DuckDB / SQLite のスキーマ変更は init_monitoring_db でマイグレーション対応（列追加）するようになっていますが、バックアップ推奨です。

ディレクトリ構成（抜粋）
---------------------
src/
  kabusys/
    __init__.py
    config.py                   # 環境変数・自動ロードロジック
    config_setup.py             # .env 対話式ウィザード
    validate_config.py          # 起動前検証 CLI
    run_execution.py            # ExecutionEngine 起動スクリプト
    run_monitoring.py           # SystemMonitor 起動スクリプト
    tools/
      paper_verification_report.py
    ai/
      news_nlp.py
      regime_detector.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py          # （実装あり）
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py          # （実装あり）
    execution/
      execution_engine.py       # （実装あり）
      order_manager.py
      order_repository.py
      broker_factory.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      risk_adjustment.py
      position_sizing.py
    research/
      factor_research.py
      feature_exploration.py
    utils/
      logging_setup.py
      process_priority.py
    data/                       # 実行時に生成されることが想定（DB / pid / flag 等）

（注）上記は本 README 作成時点の主要ファイルを抜粋しています。プロジェクト全体はさらに多くのモジュールを含みます。

開発者向け情報
----------------
- DuckDB 接続を受け渡す形で research / ai モジュールが設計されています（DB を直接書き換える処理は明示）。
- pure function（副作用なし）で設計されている関数群（portfolio, research 等）はユニットテストしやすい構造です。
- OpenAI の呼び出し部分は外部依存のため、_call_openai_api の差し替え（モック）でテスト可能です。
- .env の自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから Python を起動してください（テスト時に便利）。

よくある質問
--------------
Q. ペーパートレードと本番の DB は分離されていますか？  
A. はい。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視 DB は別途 monitoring.db を使用します。

Q. ログの場所やレベルはどう変更しますか？  
A. .env で LOG_DIR / LOG_LEVEL を設定するか、setup_logging に直接引数を渡して変更できます。

Q. OpenAI キーがない場合 AI 機能は使えますか？  
A. OPENAI_API_KEY が未設定の場合、ai 関連関数は例外を投げるか（明示的にチェックしている箇所あり）フェイルセーフでスキップする実装が混在します。AI 機能を使う場合はキーが必要です。

終わりに
--------
この README はコードベースの主要機能と運用手順の要点をまとめたものです。実運用前に python -m kabusys.validate_config を実行して設定を確認し、必要な DB やログディレクトリのバックアップを行ってください。問題や拡張点があれば各モジュールのドキュメント・ソースコメントを参照してください。