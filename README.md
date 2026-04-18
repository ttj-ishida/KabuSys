README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部です。本リポジトリには以下の主要機能が含まれます:

- 実行エンジン起動スクリプト（run_execution）: 発注・注文管理・リスク管理を束ねる。
  KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading 用 DB に書き込む。
- 監視プロセス（run_monitoring）: システム状態 / 取引状態 / リスクを定期監視してログ・アラート・Kill Switch を管理。
- 研究モジュール: ファクター計算、特徴量探索、将来リターン計算など。
- ポートフォリオ構築ユーティリティ: 候補選定、重み付け、ポジションサイジング、セクター制約。
- AI モジュール: ニュース NLP（OpenAI）による銘柄センチメント、レジーム判定（ma200 + LLM）。
- 運用補助ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成など。
- DB 永続化/監視層: SQLite（監視用）・DuckDB（分析用）への読み書きヘルパ。

主な特徴
--------
- 環境別分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え。paper_trading は専用 SQLite（data/paper_trading.db）を使用。
- フェイルセーフ:
  - LLM/API 呼び出し失敗時はフォールバック動作（例: macro_sentiment=0.0）で継続。
- 設定支援:
  - 対話式ウィザードで .env を生成/更新（kabusys.config_setup）。
  - 起動前に設定チェックを行う CLI（kabusys.validate_config）。
- 監視・Kill Switch:
  - 監視ロジックでドローダウンやポジション上限超過を検出すると data/kill.flag を書き込んで ExecutionEngine を安全停止可能。
- ロギング:
  - 統一的な logging 設定（コンソール + 日次ローテーションファイル）。
- DuckDB を用いた研究処理:
  - prices_daily / raw_financials 等を参照してファクターを高速に計算。

セットアップ手順
--------------
1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境作成例:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール
   - 必須（代表例）:
     pip install duckdb psutil openai
   - 設定検証で YAML を使いたい場合:
     pip install pyyaml
   - （実際の requirements.txt がある場合はそちらを使ってください）

3. ディレクトリ作成（初回）
   mkdir -p data logs

4. 環境変数設定（対話式）
   - 初期 .env を作成するにはウィザードを実行:
     python -m kabusys.config_setup
   - ウィザードで入力した値はプロジェクトルートの .env に保存されます。
   - .env は機密情報を含むため絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   - 基本検証:
     python -m kabusys.validate_config
   - 警告も失敗扱いにする（本番前推奨）:
     python -m kabusys.validate_config --strict

必要な主要環境変数（抜粋）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（起動時に data/kill.flag を自動クリアするか。開発用。0/1）

起動方法（主なスクリプト）
-------------------------
- ExecutionEngine を起動（発注エンジン）
  python -m kabusys.run_execution
  動作:
    - Settings を読み込み、対応する SQLite/ DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は専用 DB に書き込む
    - data/execution.pid を使用（PID ファイル）
    - 停止はデータディレクトリに data/stop_requested.flag を置くと検知して終了

- Monitoring を起動（ポーリング監視）
  python -m kabusys.run_monitoring
  オプション/注意:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視ログを記録
    - 停止は data/stop_requested.flag を作成

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
    --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いになります

重要なファイル / フラグ
----------------------
- data/kill.flag: Kill Switch 発動時に作成される停止フラグ（ExecutionEngine 停止トリガ）
- data/stop_requested.flag: 起動・監視スクリプトの外部停止要求フラグ（両スクリプトで監視）
- data/execution.pid: ExecutionEngine の PID 保存用ファイル（監視/運用用）
- logs/: ログファイル（app_name に応じて日次ローテーションで保存）

ディレクトリ構成（抜粋）
-----------------------
以下は主要なソース配置の例（リポジトリ内 src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数/Settings 管理（自動 .env ロード機能含む）
  - config_setup.py           -- .env 対話式ウィザード
  - validate_config.py        -- 起動前設定検証 CLI
  - run_execution.py          -- ExecutionEngine 起動スクリプト
  - run_monitoring.py         -- Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             -- ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      -- レジーム判定（MA200 + LLM）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (該当ファイルがあれば)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                 -- 発注・注文管理周りの実装（BrokerFactory 等）
  - data/                      -- 実行時 DB / フラグ / その他生成アーティファクト（gitignore 推奨）
  - logs/                      -- ログ出力（デフォルト）

（実際のリポジトリには上記以外にもファイルが存在します。ここでは代表的なモジュールを列挙しています）

設計上の注意点
--------------
- .env の自動読み込み:
  プロジェクトルート（.git または pyproject.toml を基準）を探して .env / .env.local を自動読み込みします。
  テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時の注意:
  - KABUSYS_ENV=live を設定する場合は LINE 通知等の監視/アラート設定を必ず確認してください。
  - KILL_FLAG_CLEAR_ON_START=1 は本番では危険（Kill Switch を自動クリアしてしまう）ため 0 を推奨します。
- OpenAI を使う機能:
  - news_nlp / regime_detector は OpenAI API を使用します。OPENAI_API_KEY の設定が必要です。
  - API 呼び出しはリトライやフォールバック挙動を持ちますが、API レート制限やコストに注意してください。

トラブルシュート（よくある問題）
---------------------------------
- ログディレクトリ作成に失敗する:
  - 権限やパスの問題で logs/ が作れない場合、コンソール出力のみで継続します。ログディレクトリの所有者/権限を確認してください。
- DB ファイルが見つからない:
  - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH を確認してください。validate_config で警告が出ます。
- OpenAI で JSON パース失敗:
  - LLM 出力のフォーマットが想定と異なるケースがあります。エラーはログに出力され、該当チャンクはスキップされます。

ライセンス / コントリビューション
---------------------------------
- 本 README では省略しています。実際のプロジェクトでは LICENSE ファイルを追加してください。
- 機密情報（.env 等）は Git にコミットしないでください。

補足
----
本 README はソースコードの主要機能を要約したものです。各モジュールの詳細は該当ファイルの docstring / コメントを参照してください。必要であれば、起動フロー図や設定例（.env.example）を別途作成できます。