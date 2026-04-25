KabuSys — 日本株自動売買システム（README）
==================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine（注文発行・注文管理・リスク管理）
- Monitoring（システム稼働監視・トレード監視・キルスイッチ）
- Portfolio（銘柄選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI（ニュース NLP によるセンチメント評価・レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート など）

主要な設計方針の抜粋
- 設定は .env または環境変数で構成（config_setup.py によるウィザードあり）
- 本番とペーパー（paper_trading）DB は分離（paper_trading 時は data/paper_trading.db を使用）
- DuckDB を分析用に利用、SQLite を監視/注文ログ用に利用
- OpenAI（gpt-4o-mini 等）を用いた NLP 機能（API キー必須、失敗時はフェイルセーフ処理）

機能一覧
---------
- 実行系
  - run_execution.py: ExecutionEngine を起動して発注セッションを実行
  - BrokerClientFactory により本番/モックブローカー切り替え（KABUSYS_ENV=paper_trading）

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - MonitoringEngine: system/trade/risk 各モニタを束ねて定期実行
  - KillSwitch: リスク条件に応じた停止フラグ（data/kill.flag）生成

- ポートフォリオ構築
  - 銘柄選定、等金額/スコア重み、リスク調整（セクター上限、レジーム乗数）、株数決定（単元丸め）

- リサーチ
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI
  - news_nlp: ニュース記事から銘柄別センチメントを OpenAI で評価し ai_scores に保存
  - regime_detector: ETF MA とマクロ記事センチメントを合成して market_regime を生成

- ツール
  - config_setup.py: 対話式 .env ウィザード（.env を生成/更新）
  - validate_config.py: 起動前設定検証（必須環境変数や config/*.yaml の存在等）
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート生成

セットアップ手順
----------------

前提
- Python 3.9+（コードは型注釈・モダン API を利用）
- git リポジトリルートにプロジェクトが存在する想定（.env 自動読み込みのため）

1. リポジトリをクローン（省略）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証で任意: pip install pyyaml

   （requirements.txt がない場合は上記を適宜インストールしてください）

4. ディレクトリ作成
   - mkdir -p data logs

5. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（例）:

     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も含めて失敗させたい場合: python -m kabusys.validate_config --strict

使い方（主なコマンド）
--------------------

1. ExecutionEngine を起動（発注実行）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録
     - 起動時に data/stop_requested.flag が存在すると起動せず終了
     - 実行中に data/stop_requested.flag を作成すると Engine に停止指示が送られます

2. Monitoring を起動（ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
     - 例: export MONITOR_POLL_INTERVAL=30
   - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用
   - 停止は data/stop_requested.flag を作成することで（run_execution と同様）

3. .env 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も exit(1) 扱いになります

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を直接指定する場合:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

6. AI / OpenAI 機能
   - news_nlp.score_news, regime_detector.score_regime を呼ぶ際は OpenAI API キーの設定が必要
     - 環境変数 OPENAI_API_KEY を設定するか、関数に api_key を渡す
   - OpenAI 呼び出しは冗長なリトライ・フェイルセーフを備えているが、API 使用にはコストがかかります

設定と環境変数（主要項目）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: Execution は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能で必要）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。0 推奨）

運用メモ
--------
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - KillSwitch は危険条件でこのファイルを書き込み、ExecutionEngine 側で停止を促します
  - 本番で KILL_FLAG_CLEAR_ON_START=1 は危険（自動クリアされてしまうため）

- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring が参照する停止フラグ（手動で作成すると安全停止）

- ログ
  - logs/<app_name>.log に日次ローテーションで出力（utils.logging_setup.setup_logging）
  - コンソールは stdout に出力

- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時にテーブルを冪等で作成・簡易マイグレーションを行います

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                 # 設定読み込み（.env 自動ロード）
    config_setup.py           # .env 対話式ウィザード
    validate_config.py        # 設定検証 CLI
    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # SystemMonitor 起動スクリプト

    utils/
      __init__.py
      logging_setup.py        # ログ設定ユーティリティ
      process_priority.py     # プロセス優先度/CPU affinity 設定ユーティリティ

    monitoring/
      __init__.py
      monitoring_db.py        # SQLite 永続化層
      system_monitor.py       # システム状態・データ鮮度監視
      trade_monitor.py        # トレード監視（滞留注文等）  <-- 実装参照（省略）
      risk_monitor.py         # ドローダウン・ポジション上限監視
      kill_switch.py          # kill.flag 制御
      monitoring_engine.py    # 各 Monitor を束ねる
      alert_manager.py        # （アラート送信用、実装参照）

    execution/
      broker_factory.py       # ブローカークライアント生成
      execution_engine.py     # ExecutionEngine（メインロジック）
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      __init__.py
      news_nlp.py             # ニュース NLP スコアリング（OpenAI 依存）
      regime_detector.py      # レジーム判定（MA + LLM）

    data/                      # 実行時に利用する DB / flag 等（プロジェクトルート）
      monitoring.db
      paper_trading.db
      kill.flag
      stop_requested.flag
      execution.pid

    tools/
      __init__.py
      paper_verification_report.py

補足 / トラブルシュート
-----------------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行われます。
  - 自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB / OpenAI / PSUtil 等の外部依存は事前にインストールしてください。
- run_monitoring は監視 DB に常に settings.sqlite_path（本番用）を使用します。開発中に別 DB を使いたい場合は環境変数で SQLITE_PATH を変更してください。
- OpenAI 利用時は API レートやコストに注意してください。API 呼び出しはリトライ・クリッピング等の安全機能が実装されていますが、鍵の管理は必ず安全に行ってください。

ライセンス
----------
（本 README にライセンス情報が無ければプロジェクトのライセンスファイルを参照してください）

---
この README はリポジトリ内のソースを元に作成しています。各モジュールの詳細は該当ソースファイル（src/kabusys 以下）を参照してください。必要であれば、実行例や開発者向けの詳細ドキュメント（API、テスト方法、CI 設定等）を別途追加します。