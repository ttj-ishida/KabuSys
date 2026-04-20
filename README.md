KabuSys — 日本株自動売買システム
================================

本ドキュメントはこのリポジトリ内の主要スクリプト・モジュールの使い方とセットアップ手順をまとめた README です。

概要
----
KabuSys は日本株の自動売買・研究・監視のための内部ライブラリ群です。特徴は次の通りです。

- 注文エンジン / ExecutionEngine（本番・ペーパートレード対応）
- 監視サブシステム（System / Trade / Risk のモニタ、Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- リサーチ用モジュール（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- Paper Trading の検証レポート作成ユーティリティ

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録
  - プロセス優先度設定・PID ファイル管理・停止フラグ監視対応
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム稼働監視・データ鮮度チェック・滞留注文／異常約定検出・リスク監視
  - Kill Switch の自動作動（条件に応じて data/kill.flag を書き込み）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を指定（デフォルト 60 秒）
- Portfolio モジュール
  - 候補抽出、等重／スコア重み、ポジション数計算、セクターキャップ、レジーム補正
- Research（DuckDB を使ったファクター計算 / 事前解析）
- AI（OpenAI を利用したニュースセンチメント score_news / regime_detector）
- ツール: config_setup（.env ウィザード）、validate_config（起動前チェック）、paper_verification_report

動作要件（推奨）
----------------
- Python 3.9+
- 必要パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（設定 YAML の内容検証を行う場合）
- ローカル環境では logs/ や data/ に書き込みできること

インストール・セットアップ
-------------------------
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば pip install -r requirements.txt）

4. 環境変数設定（.env）
   - 対話式ウィザードで作成するのが推奨です:
     - PYTHONPATH=src python -m kabusys.config_setup
     - デフォルトではプロジェクトルート/.env に保存されます
   - .env の主要キー（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB, デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0 推奨）

5. 設定の検証（起動前チェック）
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

実行方法（主要スクリプト）
--------------------------

※ 開発時は PYTHONPATH=src を指定してパッケージをモジュールとして実行するのが簡便です。
例: PYTHONPATH=src python -m kabusys.run_monitoring

1. 監視ループ（Monitoring）
   - PYTHONPATH=src python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）
   - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依らない）
   - 監視を終了させたい場合はプロジェクトルート/data/stop_requested.flag を作成

2. ExecutionEngine（注文エンジン）
   - PYTHONPATH=src python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
   - 起動前に data/stop_requested.flag が存在すると起動しません
   - エンジン停止は data/stop_requested.flag の作成で行えます
   - 実行中には PID ファイル (data/execution.pid 等) を生成

3. .env 設定ウィザード
   - PYTHONPATH=src python -m kabusys.config_setup
   - 初期 .env を対話で作成・更新できます

4. 設定検証
   - PYTHONPATH=src python -m kabusys.validate_config [--strict]

5. Paper Trading 検証レポート
   - PYTHONPATH=src python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - レポートは稼働率、注文成功率、送信率、レイテンシ等をまとめ PASS/FAIL 判定

AI 機能（OpenAI 使用）
----------------------
- モジュール:
  - kabusys.ai.news_nlp.score_news — ニュースを LLM でスコアリングして ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime — ETF (1321) の MA とマクロセンチメントを合成して market_regime を書き込む
- 必要: OPENAI_API_KEY 環境変数（または関数引数でキー指定）
- 使用モデルは gpt-4o-mini、出力は JSON モードでバリデーション・リトライ実装あり
- API エラー時はフェイルセーフ（部分的にスキップして継続）になるよう実装されています

運用に関する補足
----------------
- Paper Trading と本番 DB は分離されています（paper_sqlite_path）。
- kill.flag（Settings.kill_flag_path）: Kill Switch のフラグファイル。監視側やオペレーターがこれを書き込むことで ExecutionEngine に停止要求を送れます。KillSwitch は冪等的に動作します。
- stop_requested.flag: run_monitoring / run_execution がループを終了するためのフラグ。
- ログ: logs/<app_name>.log に日次ローテーションで出力（TimedRotatingFileHandler、既定で logs/ ディレクトリ）。setup_logging 関数で設定します。
- MONITOR_POLL_INTERVAL は 1 秒以上の正の整数で指定すること（0 や負の値は無効扱いでデフォルト 60 秒になります）。

設定項目（Settings クラスの主なプロパティ）
-----------------------------------------
- env: KABUSYS_ENV（development | paper_trading | live）
- is_paper / is_live / is_dev: 環境判定ヘルパ
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視 DB（デフォルト data/monitoring.db）
- paper_sqlite_path: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- pid_file_path, kill_flag_path, KILL_FLAG_CLEAR_ON_START
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant|partial|never|reject）
- CPU / memory / disk の閾値設定（環境変数で上書き可）

プロジェクトディレクトリ構成（主要ファイル）
-----------------------------------------
以下は src/kabusys 以下の主要ファイル一覧（本リポジトリに含まれるファイルを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_monitoring.py        — 監視ループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （この README の対象外だが存在）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート通知処理）
  - execution/               — ExecutionEngine 関連（エンジン、ブローカーファクトリ等）
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

補足 / 運用上の注意
-------------------
- 本番運用時（KABUSYS_ENV=live）の設定は慎重に管理してください。validate_config は live 環境向けの追加警告を出します。
- .env は決して Git にコミットしないでください（config_setup のヘッダにも記載）。
- OpenAI 等外部 API キーは権限管理が重要です。テスト時はキーのローテーションやモックを検討してください。
- DuckDB / SQLite のバックアップやパス指定に注意してください（デフォルトは data/ 配下）。

開発者向けヒント
----------------
- パッケージをインポートして使う場合は PYTHONPATH=src を設定するか、パッケージを pip editable インストールしてください:
  - pip install -e src
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると自動的に .env をロードしないため環境制御が容易です。
- AI 周りの関数は外部呼出しを内部で隔離しているため、ユニットテストでは該当呼び出し（_call_openai_api 等）を patch してテストしてください。

ライセンス・コントリビュート
----------------------------
（ここにプロジェクトのライセンスやコントリビュート方法を記載してください。リポジトリに該当情報があれば置き換えてください。）

以上。ご不明点や追加で README に載せたい内容があれば教えてください。