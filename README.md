KabuSys — 日本株自動売買システム
================================

このリポジトリは、KabuSys（日本株自動売買システム）のコアライブラリ群と起動用スクリプトを含みます。  
主に下記の機能を持つモジュール群で構成されています：注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および AI によるニュース解析など。

この README は日本語での導入・使い方の概要をまとめたものです。

主な特徴
-------
- ExecutionEngine: ブローカークライアント経由の発注・注文管理・リスク管理（paper_trading モードあり）
- Monitoring: システム稼働監視、データ鮮度チェック、トレード監視、Kill Switch（flagファイルによる停止）など
- Portfolio: 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数
- Research: DuckDB 上の価格・財務データからファクター（Momentum / Volatility / Value）や将来リターン、IC 等を算出
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングして ai_scores に格納、マクロセンチメントと MA を合成して市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード/検証ツール、Paper Trading 検証レポート生成

セットアップ手順
-------------
前提
- Python 3.10 以上（型アノテーションで | を使用）
- システムレベルで DuckDB、SQLite を使います（Python パッケージ duckdb を利用）
- OpenAI を利用する機能は OPENAI_API_KEY が必要

1) 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 必要パッケージ（最低限）
   - pip install duckdb psutil openai
   - 追加推奨: pip install pyyaml  （config の YAML 検証に使用）

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3) .env 作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話で KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等を設定します
     - .env はセキュリティ上コミットしてはいけません

4) 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit 1）になります

5）データディレクトリ（自動作成されることが多い）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/<app_name>.log（日時ローテーション）

環境変数（主要）
----------------
主な環境変数（Settings クラスを参照）／デフォルト値:
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading モード時)
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視関連

使い方（起動スクリプト）
-----------------------
主なスクリプトはモジュールとして実行できます。

1) ExecutionEngine を起動（本番／ペーパートレード）
   - 環境例（ペーパートレード）:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 本番実行:
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   動作:
     - paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離します。
     - 起動時に data/stop_requested.flag が存在すると起動しません。
     - 実行中は data/execution.pid が使用されます。

2) Monitoring を起動
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト60秒）。
   - python -m kabusys.run_monitoring
   動作:
     - システム CPU/メモリ/ディスクや Execution のプロセス存在確認、トレード／リスクチェックを定期実行します。
     - 監視は本番 sqlite_path（Settings.sqlite_path）を使用してログを残します。
     - 監視中、data/stop_requested.flag があればループを停止します。

3) 設定ウィザード（.env 生成）
   - python -m kabusys.config_setup

4) 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

ログ
----
- 共通の setup_logging(app_name=...) を利用して、コンソール（stdout）と日次ローテーションされたファイルログ（logs/<app_name>.log）を生成します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

重要なファイル / フラグ
----------------------
- data/stop_requested.flag: run_monitoring / run_execution が参照する停止フラグ（存在で停止）
- data/kill.flag: KillSwitch が作成するフラグ（ExecutionEngine 停止要求）
- data/execution.pid: ExecutionEngine の PID ファイル（run_execution で使用）
- DB マイグレーション: monitoring_db.init_monitoring_db() が必要なテーブルを冪等的に作成します

モジュール（主なディレクトリと役割）
----------------------------------
src/kabusys/
- __init__.py
- config.py: 環境変数読み込み・Settings 定義、自動 .env ロード（.env / .env.local）
- config_setup.py: .env 対話式ウィザード
- validate_config.py: 起動前チェック CLI

- run_execution.py: ExecutionEngine 起動スクリプト（paper_trading 切替、DB 初期化、スレッドで実行）
- run_monitoring.py: SystemMonitor ベースのポーリング監視ループ

- execution/: ExecutionEngine、本物のブローカークライアント/モック、OrderManager, RiskManager 等（起動ロジックは run_execution.py）
- monitoring/:
  - monitoring_db.py: SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: （トレード監視、ログ比較など）※詳細は実装ファイル参照
  - risk_monitor.py: ドローダウン・ポジション上限監視（KillSwitch と連携）
  - kill_switch.py: data/kill.flag を書いて ExecutionEngine を停止させる
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （通知管理。LINE 等）※実装参照

- portfolio/:
  - portfolio_builder.py: 候補選定、等重・スコア重み
  - position_sizing.py: 発注株数計算、aggregate キャップ
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/:
  - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン、IC、統計サマリー

- ai/:
  - news_nlp.py: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py: ETF MA とマクロセンチメントを合成して market_regime を決定
  - どちらも OPENAI_API_KEY を参照（引数で上書き可能）

- tools/:
  - paper_verification_report.py: Paper Trading の検証レポートを生成

- utils/:
  - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ローテーション）
  - process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティ

ディレクトリ構成（概略）
----------------------
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/...
    - monitoring/...
    - portfolio/...
    - research/...
    - ai/...
    - tools/...
    - utils/...
- data/             （デフォルト DB / flag / pid が置かれる）
- logs/             （ログ出力先）

運用上の注意
-----------
- KABUSYS_ENV=live の場合は、本番設定（LINE 通知など）を慎重に確認してください。validate_config の live 向けガードが有効です。
- .env は絶対に Git にコミットしないでください。
- OpenAI を利用する処理は API コストとレイテンシに注意してください。rate limit / 5xx はリトライ実装がありますが、運用ポリシーを決めてください。
- monitoring は本番 sqlite を参照して監視ログを残します。paper_trading は paper 用 DB に分離されます（run_execution の実装参照）。

開発・テスト補助
----------------
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（テストなど）。
- news_nlp / regime_detector の外部 API 呼び出し部はテストで差し替えられるよう設計されています（_call_openai_api を patch する等）。
- DuckDB のクエリはテスト用に簡単にモックできます。

参考（よく使うコマンドまとめ）
----------------------------
- .env を作る: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

その他
-----
この README はコードの主要部分から抽出した運用情報をまとめたものです。詳細な実装や追加オプションは各モジュールの docstring / コメントを参照してください。必要であれば、各サブモジュールごとの詳細 README を追加します。