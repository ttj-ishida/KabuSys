README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python 製のモジュール群です。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine（発注エンジン） — 実際の発注 / ペーパートレードの実行
- Monitoring（監視） — システム状態・データ鮮度・注文ログ・リスク監視
- Portfolio / Position sizing（銘柄選定・配分・株数計算）
- Research（ファクター計算・特徴量解析）
- AI（ニュース NLP / レジーム判定） — OpenAI を用いたセンチメント評価および市場レジーム判定
- ユーティリティ（環境セットアップウィザード、設定検証、ツール類）

機能一覧
--------
主な機能とスクリプト（抜粋）:

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパートレード）
  - python -m kabusys.run_monitoring: SystemMonitor をポーリング実行（監視ログの保存・アラートトリガー等）
- 設定関連
  - python -m kabusys.config_setup: 対話式に .env を作成 / 更新するウィザード
  - python -m kabusys.validate_config: .env や config/*.yaml の設定チェック（--strict オプションあり）
- ツール
  - python -m kabusys.tools.paper_verification_report: ペーパートレード DB から検証レポートを生成
- 監視・リスク
  - monitoring.monitoring_db: SQLite による監視ログ永続化
  - monitoring.system_monitor / trade_monitor / risk_monitor / monitoring_engine: 定期監視、Kill Switch、アラート連携
- ポートフォリオ構築
  - portfolio.portfolio_builder / position_sizing / risk_adjustment: 候補選定・重み計算・株数決定・セクター制限
- Research
  - research.factor_research / feature_exploration: DuckDB を用いたファクター計算・IC 解析等
- AI
  - ai.news_nlp: OpenAI でニュースをスコアリングして ai_scores に書き込む
  - ai.regime_detector: MA とマクロセンチメントを合成して market_regime を判定

セットアップ手順
----------------

1. Python 環境の準備
   - 推奨: Python 3.10 以上（typing に | を使用するため）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 主要依存例:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML （validate_config で YAML 検証を行う場合、任意）
   - pip インストール例:
     - pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt があればそちらを使用してください。

3. プロジェクトルートとディレクトリ
   - data/ と logs/ の作成（起動時に自動作成されるケースもありますが、手動で用意しておくと良いです）
     - mkdir -p data logs

4. 環境変数の設定
   - .env を作成する方法:
     - 対話式ウィザード: python -m kabusys.config_setup
     - あるいは手動で .env を作成（.env は Git にコミットしないこと）
   - 必須環境変数（validate_config による検証対象）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - 各種設定（主なもの）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
     - LOG_LEVEL: DEBUG/INFO/...
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
     - KILL_FLAG_CLEAR_ON_START: 0/1（本番で 1 は危険）

   - 自動 .env ロードの挙動:
     - プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには --strict を付ける

初回起動補足
- monitoring の初回実行や execution の起動時に init_monitoring_db() により監視テーブルが作成されます。
- デフォルトでは monitoring は sqlite_path（監視 DB）を使用します。run_execution は KABUSYS_ENV が paper_trading の場合に paper_sqlite_path を使用します（本番 DB と分離）。

使い方
------

基本的な起動例（プロジェクトルートで実行）:

- 環境セットアップ（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 補足:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
    - Monitoring は設定環境（KABUSYS_ENV）にかかわらず sqlite_path（本番監視 DB）を使用する設計です。
    - 停止フラグ: data/stop_requested.flag を作成すると監視ループが停止します。

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid が設定されます。停止は data/stop_requested.flag の作成や Kill Switch による kill.flag によって行われます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI/レジーム機能（ライブラリ API として）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # ai_scores テーブルへ書き込む
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")  # market_regime に書き込み

主要な動作フロー・ファイル
- Kill Switch
  - kabusys.monitoring.kill_switch: 条件により data/kill.flag を書き込み ExecutionEngine 停止をリクエスト
  - Kill Switch の評価は Monitoring により行われ、必要に応じてアラート通知が行われます

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。
- デフォルトは logs/ ディレクトリに日次ローテーションでログを保存（logs/<app_name>.log）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。

ディレクトリ構成
----------------

（リポジトリの src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング実行スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - monitoring/
    - monitoring_db.py        — SQLite の監視テーブル初期化と永続化 API
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py        — （注文ログ監視）※コードベース内に存在
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の書き込み / 解除
    - monitoring_engine.py    — 各モニタを束ねて定期実行
    - alert_manager.py        — （アラート送信ロジック、実装に応じて存在）
  - execution/
    - execution_engine.py     — 発注エンジン（ExecutionEngine）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — ブローカークライアント生成（Mock / 実ブローカー）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・資金配分ロジック
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Value / Volatility ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py             — OpenAI を使ったニューススコアリング
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - data/ (runtime)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag などのフラグ/状態ファイル
  - logs/ (runtime)           — ログファイル群

注意事項 / ベストプラクティス
-----------------------------
- .env は絶対にリモートリポジトリにコミットしないでください（APIキーや秘密情報が含まれます）。
- KABUSYS_ENV を "live" にする前に、必ず validate_config で警告や設定を確認してください（本番では特に注意）。
- 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動で Kill Flag を消す設定は危険）。
- AI 関連（OpenAI）を有効にする場合は API キーの管理（レート制限やコスト）に注意してください。
- DuckDB / SQLite のパスは十分なディスク容量がある場所を指定してください。
- psutil 等は OS 依存の機能を利用するため、OS 権限により一部機能（プロセス優先度設定や CPU affinity）が失敗する場合があります。ログにワーニングが出力されます。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（なければ追加してください）。

補足
----
より詳細な設計意図やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントにまとめられている想定です。実務利用前に各モジュールの実装・テストを十分に行ってください。

問題や追加情報が必要であれば、どの部分を詳しく記載するか教えてください。