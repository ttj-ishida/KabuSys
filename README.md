KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買／リサーチ／監視用ライブラリ群と起動スクリプトを含みます。  
本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の用途を想定したモジュール群です。

- 自動発注の実行エンジン（ExecutionEngine）
- システム・発注・リスクの監視（Monitoring）
- ポートフォリオ構築・ポジションサイジング（Portfolio）
- ファクター計算・研究ユーティリティ（Research）
- AI を使ったニュースセンチメント評価（OpenAI 経由）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード等）
- ペーパートレード用の分離 DB と検証レポート生成ツール

注意点:
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離された専用 SQLite を使用します（デフォルト: data/paper_trading.db）。
- Monitoring は常に本番 sqlite_path（data/monitoring.db デフォルト）を使用します。
- OpenAI API を使う機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY が必要です。

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker 使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定管理 / 検証
  - config_setup.py: 対話式で .env を生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml のプリチェック
- 監視
  - monitoring/monitoring_db.py: 監視ログ用 SQLite スキーマと永続化ロジック
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py 等
- 発注・リスク管理（execution パッケージ、broker_factory 等）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選択、等分配／スコア加重、リスク調整、ポジションサイジング
- 研究用モジュール（research パッケージ）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算等
- AI（ai パッケージ）
  - news_nlp: raw_news をまとめて OpenAI に送り銘柄ごとのスコアを ai_scores テーブルへ書き込む
  - regime_detector: ma200 とマクロニュースを合成して日次レジーム判定を行う
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

セットアップ手順（開発者向け）
-------------------------
以下は一般的な手順の例です。環境に合わせて調整してください。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - optional: PyYAML（validate_config の YAML 検証用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がない場合は上記を目安に必要なライブラリを追加してください）

4. 環境変数ファイルの作成
   - 対話式ウィザードで作る（推奨）
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）
   - 代表的な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB のパス)
     - LOG_LEVEL (DEBUG|INFO|...)
     - KILL_FLAG_CLEAR_ON_START (0|1)

   - 自動 .env ロード:
     - 起動モジュールは .env / .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

6. 必要なディレクトリの作成（多くは自動で作成されますが念のため）
   - mkdir -p data logs

基本的な使い方
----------------

起動スクリプト
- 監視ループを開始（デフォルトポーリング 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring

- 実行エンジンを起動
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - python -m kabusys.run_execution

停止方法
- stop_flag / kill.flag:
  - run_monitoring と run_execution はプロジェクトルート下 data/stop_requested.flag を監視します。ファイルが存在すると監視ループ／エンジンを終了します。
  - KillSwitch は条件成立時に data/kill.flag を書き込みます（ExecutionEngine はこれを検知して停止する設計）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ペーパートレード検証レポート
- tools/paper_verification_report.py を実行してペーパートレード DB の集計レポートを出力できます。
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用）

AI 機能
- ai.news_nlp.score_news / ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY または引数）を必要とします。
- OpenAI への呼び出しはリトライやレスポンス検証を行いますが、API キー未設定時は例外になります。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- コンソールは stdout に出力されます。
- setup_logging(app_name="execution") を各起動スクリプトで呼んで統一されたログ設定を行っています。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: execution 動作モード（development | paper_trading | live）、デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール抜粋です（全ファイルはリポジトリを参照してください）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 起動前設定チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - execution/                 — ExecutionEngine 関連（broker_factory, order_manager, risk_manager, etc.）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意 / トラブルシュート
-----------------------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時に必要なテーブルを冪等に作成します。既存テーブルのカラム追加 (ALTER TABLE) も一部行います。
- Paper Trading:
  - paper_trading モードは専用 SQLite に記録され、本番データとは分離されます（安全対策）。
- OpenAI API:
  - API 呼び出しはレート制限やネットワークエラーに対して指数バックオフでリトライしますが、API キー未設定だと失敗します。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。プラットフォームにより効果や許可が異なります（権限不足で警告）。
- 停止制御:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。
  - KillSwitch は条件に応じて data/kill.flag を作成し ExecutionEngine 側が検知して停止します。KILL_FLAG_CLEAR_ON_START を必要に応じて設定してください。

開発者向けメモ
----------------
- ほとんどの計算関数は副作用がない純関数として実装されています（ユニットテストが容易）。
- DuckDB を使って時系列／財務データの集計を行う設計になっています（research モジュール）。
- AI まわりの API 呼び出し箇所はテストのために _call_openai_api をモックできるように分離しています。

追加情報 / 参考コマンド
-----------------------
- .env を生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 開発時ログ確認:
  - tail -F logs/execution.log logs/monitoring.log

ライセンス / 貢献
-----------------
（ここにライセンスやコントリビューションの方針を追記してください。）

以上がこのコードベースの概要と基本的な運用手順です。必要であれば各モジュール（ExecutionEngine や Monitoring の内部仕様、config の詳細、DB スキーマ等）について別途ドキュメントを作成します。どの部分を詳しく記述するか教えてください。