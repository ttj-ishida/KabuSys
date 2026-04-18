README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（run_execution.py）: 発注エンジン（本番/ペーパートレード対応）
- Monitoring（run_monitoring.py / monitoring/*）: システム稼働性・注文・リスクの監視と Kill Switch
- Portfolio（portfolio/*）: 銘柄選定・重み計算・ポジションサイズ計算などの純粋関数
- Research（research/*）: ファクター計算・特徴量探索ユーティリティ（DuckDB 経由）
- AI（ai/*）: ニュース NLP によるセンチメント評価、レジーム判定（OpenAI を使用）
- Tools（tools/*）: ペーパートレード検証レポート生成等のユーティリティ
- Utilities（utils/*）: ロギング設定、プロセス優先度/CPU affinity の管理など
- 設定管理（config.py, config_setup.py, validate_config.py）: .env ウィザード、自動ロード、設定検証

主な機能
--------
- 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - paper_trading 時は MockBroker を使用し、ペーパートレード用 DB を別ファイルに保存する
- ExecutionEngine の起動／停止用フラグ（data/stop_requested.flag / data/kill.flag）
- 監視機能
  - システム CPU / メモリ / ディスク使用率、Execution プロセス死活、データ鮮度
  - 発注ログ（trade_logs）、ポジション、リスクログ保持（SQLite）
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch 書き込み
  - アラート送信（LINE 等の設定があれば通知可能）
- ポートフォリオ構築ロジック（候補選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数）
- 研究用：モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
- AI 機能：ニュース記事を LLM（OpenAI）で評価して ai_scores に記録、マクロセンチメント＋MA200 でレジーム判定
- ログ管理：stdout と日次ローテートファイル（logs/<app>.log）を自動設定

必要条件
--------
- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定検証で YAML 内容検証を行いたい場合）
- 推奨: 仮想環境（venv / pipenv / poetry など）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   （実際の requirements.txt がある場合はそれを使用してください）

セットアップ手順
--------------
1. プロジェクトルートに .env を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（例は後述）

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗として扱う）:
     - python -m kabusys.validate_config --strict

3. SQLite / DuckDB のデータディレクトリ（デフォルトは data/）やログディレクトリ logs/ を作成（必要なら）
   - 多くのコードは起動時に自動でディレクトリを作成しますが、パーミッションに注意してください。

4. （AI 機能を利用する場合）OpenAI API キーを .env に設定
   - OPENAI_API_KEY=your_api_key

主要な環境変数（代表）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring にて上書き）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

簡単な .env の例
-----------------
（config_setup を使うのが推奨）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=your_openai_api_key  # AI 機能を使う場合

使い方
-----
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します
    - 実行中は data/execution.pid が作成されます（設定で変更可）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
  - 備考:
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用して監視情報を永続化します
    - 監視ループは data/stop_requested.flag を検知すると終了します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI 機能の呼び出し（ライブラリ API）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn は duckdb.connect(...) の接続オブジェクト
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止 / Kill Switch
------------------
- kill.flag（デフォルト data/kill.flag）: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側はこのフラグをチェックして停止処理を行います）
- stop_requested.flag（data/stop_requested.flag）: run_monitoring / run_execution の外部停止制御に使用（存在するとループを抜けて終了）

注意点 / 運用メモ
----------------
- KABUSYS_ENV=live に設定する場合は全ての設定（LINE 通知、API キー等）を慎重に確認してください。validate_config で live 時の追加チェックが行われます。
- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリに書き込み権限が必要です。
- OpenAI 呼び出し部分はネットワークエラーや 429 を考慮してリトライ実装がありますが、API キーとレート制限に注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理（自動 .env ロード）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

subpackages:
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（OpenAI 呼び出し）
  - regime_detector.py      — マクロ + MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py        — （発注ログ監視等：コードベース参照）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — （アラート送信）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

ドキュメント・参照
----------------
- コード中の docstring に主要なアルゴリズムや設計意図が記載されています（PortfolioConstruction.md / StrategyModel.md 等の参照が見受けられますが本リポジトリに含まれない場合があります）。
- AI 機能を使う際は OPENAI_API_KEY を設定し、API 利用料金やレート制限に注意してください。

ライセンス / 貢献
----------------
（本リポジトリにライセンスファイルがある場合はその指示に従ってください）

問い合わせ / 開発者向けメモ
-------------------------
- 開発者は config._find_project_root() により .env 自動ロードが行われる点に注意（テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能）。
- DuckDB / SQLite のスキーマ初期化は init_monitoring_db() が冪等に実行します。
- process_priority.set_process_priority() はプラットフォーム差分（Windows / POSIX）を吸収しますが、権限不足で失敗するケースがあるためログに警告が出力されます。

以上。必要があれば各モジュールの詳細な使用例や API ドキュメント（関数引数の詳細、返り値）を別途作成します。