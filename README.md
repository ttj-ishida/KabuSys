# KabuSys — README (日本語)

簡潔な説明書です。本プロジェクトは日本株向けの自動売買・リサーチ基盤です。以下にはプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

注意: この README はリポジトリ内のソースコード（src/kabusys/）を基に作成しています。実運用では .env に機密情報を含めないように注意してください。

概要
----
KabuSys は日本株の自動売買・リサーチを支援する Python ベースのシステムです。主な要素は次の通りです。

- ExecutionEngine: 発注実行・注文管理・リスク管理
- Monitoring: システム状態・注文・リスク監視、Kill Switch（停止フラグ）
- Research: DuckDB を使ったファクター計算・特徴量解析
- AI モジュール: OpenAI を利用したニュースセンチメント評価・レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度管理
- Paper Trading 対応: KABUSYS_ENV=paper_trading 時は発注をモックして専用 DB に記録

主な機能
--------
- 環境設定ウィザードと自動 .env 読み込み（config_setup.py / config.py）
- 起動前の設定検証 (validate_config.py) — 必須環境変数や config/*.yaml の存在チェック
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番とペーパートレードで DB を分離（ペーパートレードは data/paper_trading.db）
  - プロセス優先度設定、pid / stop フラグ管理
- Monitoring（run_monitoring.py / monitoring/*）
  - システムリソース、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）監視
  - Kill Switch（data/kill.flag）を生成して ExecutionEngine を停止可能
  - 監視ログを SQLite（デフォルト: data/monitoring.db）へ永続化
- Research（research/*）
  - モメンタム、ボラティリティ、バリューファクター等を DuckDB（data/kabusys.duckdb）上で計算
  - 将来リターンや IC（Information Coefficient）計算、統計サマリー
- AI（ai/*）
  - OpenAI API を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
  - スコア／レジームは DuckDB 上のテーブルに書き込み
- ポートフォリオ構築ヘルパー（portfolio/*）
  - 候補選定、重み計算、リスク調整、株数決定（lot 単位で丸め）
- 運用ツール（tools/）
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report.py）

前提（依存ライブラリ）
--------------------
主な外部依存（例）
- Python 3.9+（型注釈等に合わせる）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定検証で YAML を検証する際に必要。インストールされていない場合は検証をスキップ）

インストール例（venv 使用）
- Python 仮想環境を作成・有効化
- 必要パッケージをインストール:
  pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. クローン / コピー
   - リポジトリを取得して作業ディレクトリを移動します。

2. 仮想環境・依存パッケージをインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
   - requirements.txt がない場合は上記の主要パッケージを個別にインストールしてください。

3. .env 初期作成（対話式ウィザード）
   - 実行:
     python -m kabusys.config_setup
   - ウィザードに従い J-Quants トークン、kabuステーション API パスワード、DB パス等を入力します。
   - 生成される .env のデフォルト:
     - KABUSYS_ENV=development（development / paper_trading / live）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. 設定検証
   - 実行:
     python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit(1)）になります。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（環境変数または .env）

5. データディレクトリ・ログディレクトリ
   - デフォルトで data/ と logs/ を使用します。必要に応じて手動作成してくださいが、コードは存在しなければ作成することが多いです。
   - ログ保存先は環境変数 LOG_DIR で変更できます（デフォルト logs/）。

環境変数の自動読み込み
--------------------
- config.py はプロジェクトルート（.git または pyproject.toml が存在する場所）から .env/.env.local を自動読み込みします。
- 自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要環境変数（代表）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使用する場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant | partial | never | reject）

使い方（主要スクリプト）
-----------------------
- 実行エンジン起動（ExecutionEngine）
  - 実行:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag があると起動をスキップします。
  - 実行中は data/execution.pid に PID を出力します（設定によりパス変更可）。

- 監視ループ起動（Monitoring）
  - 実行:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず本番の監視 DB を参照・更新します）。
  - 停止フラグ data/stop_requested.flag を置くとループは終了します。
  - kill_switch により data/kill.flag を書き込めば ExecutionEngine を停止させる運用が可能です。

- 設定検証 CLI
  - 実行:
    python -m kabusys.validate_config
  - 重要な環境変数や設定ファイルの有無、パスの親ディレクトリ存在をチェックします。

- Paper Trading 検証レポート
  - 実行:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db
  - レポートは稼働率、注文成功率、レイテンシ、リスク却下数などを出力します。

- AI 関連（ニューススコア / レジーム判定）
  - news_nlp.score_news, regime_detector.score_regime を呼び出すと DuckDB に結果を書き込みます（OPENAI_API_KEY 必須）。
  - 大量の API 呼び出しはレート制限やコストに注意してください。

停止 / Kill Switch / フラグ
--------------------------
- data/stop_requested.flag: run_execution / run_monitoring のループを検出して停止するための外部フラグ（停止要請）。
- data/kill.flag: KillSwitch が書き込むファイル。存在すると ExecutionEngine に停止シグナルを送る運用を行います。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアできます（本番では 0 推奨）。

ログ
---
- 共通の logging 設定は kabusys.utils.logging_setup.setup_logging で行われます。
- stdout にもログを書き、加えて日次ローテーションのファイルハンドラ（logs/<app_name>.log）を使用します（LOG_DIR で変更可能）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル/モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite スキーマと永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （存在する想定、アラート送信ロジック）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - data/                     — データファイル（例: data/*.db, .flag 等）※実データはリポジトリに含めない

補足／運用上の注意
-----------------
- 本番（KABUSYS_ENV=live）では .env に機密情報を含めるため、絶対に Git へコミットしないでください。
- validate_config と設定ウィザードを併用して起動前に必ず設定を確認してください。
- AI（OpenAI）を利用する際は API コストとレート制限に注意してください。news_nlp と regime_detector はリトライ・バックオフの実装がありますが、運用の設計は慎重に行ってください。
- Monitoring は監視結果を常に本番の sqlite_path に書き込みます。環境に関係なく監視 DB は本番経路を使う設計ですので、テスト時は意図的に監視 DB を分離するか注意してください。
- Paper Trading を完全に本番と分離したい場合は KABUSYS_ENV=paper_trading と PAPER_TRADING_SQLITE_PATH を利用してください。

ライセンス / コントリビュート
-----------------------------
- 本 README ではライセンス情報やコントリビュート方法は含めていません。リポジトリルートに LICENSE や CONTRIBUTING.md があればそちらを参照してください。

問い合わせ
---------
- コードベースについての質問や改善案はリポジトリの issue/PR を利用してください。

以上。必要であれば README にサンプル .env テンプレートやより詳しい運用手順（systemd / supervisor / Docker でのデプロイ例など）を追加できます。どの情報を追記しますか？