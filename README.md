KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした Python ベースのプロジェクトです。
主な機能群は以下の通りです。

- 取引実行エンジン（ExecutionEngine）：ブローカークライアント経由で発注・注文管理・リスク制御
- 監視（Monitoring）：システム状態・注文・リスクをポーリングしてログ記録・アラートや Kill Switch を発動
- ポートフォリオ構築（Portfolio）：候補選定、配分重み計算、ポジションサイジング、セクター制限
- リサーチ（Research）：ファクター計算（Momentum / Value / Volatility 等）、特徴量探索、IC 等の統計指標
- AI 支援（AI）：ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI を利用）
- ユーティリティ／ツール：.env 設定ウィザード、設定検証、Paper Trading 検証レポート生成 等

特徴
----
- 設定は .env（/.env.local）および環境変数で管理。Settings クラスで安全に取得・検証される
- 実行環境は KABUSYS_ENV（development / paper_trading / live）で切替。paper_trading は専用 DB を使用し本番 DB と分離
- 監視（monitoring）は環境に関わらず本番用 sqlite_path を使って監視ログを記録
- ログ出力は共通の setup_logging を利用し標準出力 + 日次ローテートファイルログを提供
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価とレジーム判定をサポート（失敗時はフォールバック）
- DuckDB を分析用（時系列・財務データ）に利用、SQLite を監視／トレードログ永続化に使用
- フラグファイル（data/kill.flag, data/stop_requested.flag など）を用いた外部停止制御をサポート

セットアップ手順
----------------
1. リポジトリをクローン
   - 仮定: この README はパッケージが src/ 配下にある構成を前提としています。

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - プロジェクトの requirements.txt はここに含まれていませんが、実行に必要な主なライブラリ:
     - duckdb
     - psutil
     - openai
     - pyyaml (config 検証で任意)
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env の作成（推奨: 対話式ウィザードを利用）
   - python -m kabusys.config_setup
     - ウィザードが .env を生成します（.env は絶対に Git にコミットしないでください）
   - または手動で .env を作成し必要な環境変数を設定

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番前に --strict を付けて警告も致命扱いにできます:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトでは data/ を使います。必要に応じて作成してください（logs/ も作成されますが自動作成もされます）。

主な環境変数
--------------
必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意／デフォルト
- KABUSYS_ENV — execution の動作モード: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
- DUCKDB_PATH — 分析用 DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（1=クリア。production では 0 推奨）
- OPENAI_API_KEY — OpenAI 呼び出し (AI モジュール使用時に必須)
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（取引実行）
  - python -m kabusys.run_execution
  - 動作のポイント:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 途中停止は data/stop_requested.flag を作成するとスレッドが検出して停止します
    - 起動時に PID を data/execution.pid に書き込みます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作のポイント:
    - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60 秒）
    - 監視は「環境にかかわらず」本番 sqlite_path を使用して監視ログを記録
    - 停止はプロジェクトルート data/stop_requested.flag を検出すると終了

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可）

- AI / リサーチ関数（Python API）
  - ニュースセンチメント付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
      - duckdb_conn: duckdb.connect(...)
      - target_date: datetime.date オブジェクト（ルックアヘッド防止のため外部で日付を渡す）
      - 戻り値: 書き込んだ銘柄数
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)
  - これらは内部で OpenAI API を呼びます。OPENAI_API_KEY が必要です。

実装／挙動に関する重要メモ
------------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を探す）を検出できれば .env と .env.local をロードします（OS 環境変数を保護）
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- ログ:
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30日分保持）へ出力します
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作します
- DB マイグレーション:
  - init_monitoring_db は冪等でテーブルを作成し、既存 DB に対して必要カラムがない場合は ALTER TABLE で追加します（簡易マイグレーション）
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil を使ってプラットフォーム依存に対応）
- Kill Switch / Stop フラグ:
  - kill.flag: KillSwitch が書き込み ExecutionEngine を停止するために使用（Settings.kill_flag_path）
  - stop_requested.flag: run_execution/run_monitoring が検出して自身を終了するために使用（data/stop_requested.flag）
  - kill.flag を自動でクリアする挙動は KILL_FLAG_CLEAR_ON_START で制御（本番は 0 推奨）
- Paper Trading:
  - paper_trading モードでは MockBrokerClient を利用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と完全分離します

ディレクトリ構成
----------------
（主要ファイル・モジュールの抜粋）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings クラス（.env ロード機能含む）
  - config_setup.py         — .env 対話式ウィザード（CLI）
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite 監視 DB ラッパ（初期化・CRUD）
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文 / 約定監視（※実装ファイルが存在）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag を扱うユーティリティ
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — アラート送信（LINE など）（※実装ファイルが存在）
  - execution/
    - execution_engine.py   — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py     — BrokerClient の生成（Mock 対応）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 呼出）と ai_scores 書き込み
    - regime_detector.py    — マーケットレジーム判定（OpenAI 呼出）
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成

開発・運用上のヒント
--------------------
- 本番（live）の場合は必ず validate_config を実行して必須変数やログ設定を確認してください
- .env を絶対にリポジトリにコミットしないでください
- AI モジュールは API 呼び出しにコストがかかり、失敗時はフォールバックする設計ですが、OpenAI のレート制限やキー管理には注意してください
- 監視ループ（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
- paper_trading 環境では実発注が発生しないことを必ず確認してください（MockBrokerClient 実装に依存）

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE 等を参照してください（本コード内には明示されていません）

問い合わせ
----------
実装に関する質問や運用上の不明点があれば、リポジトリの Issue や開発チームにお問い合わせください。

以上。README を元にまず .env を作成 → validate_config → ローカルで実行（paper_trading モード推奨）して挙動を確認してください。