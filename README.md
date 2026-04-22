KabuSys — 日本株自動売買システム
======================

概要
----
KabuSys は日本株の自動売買システムのコアライブラリ群です。本リポジトリは以下の主要機能を提供します。
- 発注・ExecutionEngine（実運用 / ペーパートレード切替）
- システム監視・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP（OpenAI を用いたセンチメント計算）とレジーム判定
- 開発支援スクリプト（.env ウィザード・設定検証・Paper Trading レポート生成）

本 README はコードベース（src/kabusys 以下）を参照して、セットアップ・実行方法と各コンポーネントの役割を説明します。

主な機能一覧
--------------
- ExecutionEngine 起動（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント切替（MockBrokerClient を paper_trading で使用）
  - 発注履歴・監視テーブル初期化（SQLite / DuckDB）
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件満たせば data/kill.flag を作成して Execution を停止
  - MonitoringEngine: 上記をまとめたポーリングループ
- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 等配分 / スコア配分（calc_equal_weights, calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
  - DuckDB 接続を受け取り SQL + Python で高速処理
- AI（ai）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API とリトライ / バリデーションロジックを内包
- ユーティリティ
  - logging_setup: 統一ログ設定（コンソール stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config_setup: .env 対話ウィザード
  - validate_config: 起動前設定検証
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------
1. Python 環境
   - Python 3.10 以上を推奨（typing/構文に依存）
2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（validate_config の YAML 検証用）
   インストール例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください（本コード断片には含まれていません）。

3. .env の作成
   - 対話式ウィザードを使うと安全に作成できます:
       python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（デフォルト値は以下）:
     - KABUSYS_ENV=development | paper_trading | live (default: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - PAPER_FILL_MODE=instant|partial|never|reject (paper_trading の挙動)
   - .env の自動読み込み:
     - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出し .env を読み込みます。
     - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 初期ディレクトリ
   - data/ (SQLite DB やフラグファイルが置かれる)
   - logs/ (ログファイル。setup_logging が自動作成)
   実行時に自動作成されることが多いですが、権限やパスを確認してください。

使い方（実行例）
----------------
- 設定検証:
    python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いになります。

- .env 作成 / 更新（対話式ウィザード）:
    python -m kabusys.config_setup

- ExecutionEngine 起動:
    python -m kabusys.run_execution
  - 起動時に PID ファイル (data/execution.pid) を使用します。
  - 停止は data/stop_requested.flag の作成や kill.flag によってトリガされます。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

- Monitoring 起動:
    MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60）。
    python -m kabusys.run_monitoring

  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使います（環境にかかわらず）。
  - 監視ループを止めるには data/stop_requested.flag を作成してください（スクリプトはこのファイルを検知して優雅に終了します）。

- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定。
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を出力します。

- AI 機能（プログラム内呼び出し）
  - ニューススコアリング:
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key=None)
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数か OPENAI_API_KEY 環境変数で指定します。未指定だと例外になります。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 機能利用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒。デフォルト 60)
- PAPER_FILL_MODE (paper_trading の注文約定挙動: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (production で危険なためデフォルト 0 を推奨)

監視・停止フラグについて
------------------------
- data/kill.flag — KillSwitch が作成するフラグ。ExecutionEngine に即時停止を要求するために使用されます。KillSwitch はリスク条件を評価してこのファイルを作成します。
- data/stop_requested.flag — run_execution.py / run_monitoring.py がループを抜けるために参照するファイル。手動で作ることで安全にプロセスを終了できます。
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution が使用）。

ログ
----
- ログは logging_setup.setup_logging により統一的に設定されます:
  - コンソール出力: stdout
  - ファイル出力: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30世代保持）
- LOG_DIR 環境変数でログ格納場所を変更できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の抜粋構成（本リポジトリの主要モジュール）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（Settings）
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP / OpenAI 連携
      - regime_detector.py     — 市場レジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 永続化層（監視テーブル）
      - system_monitor.py      — システム状態 / データ鮮度監視
      - trade_monitor.py       — 注文監視（trade_logs の解析）  ※（ファイル一部のみ参照）
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 書き込みロジック
      - alert_manager.py       — アラート送信処理（LINE 等）※（実装存在を想定）
      - monitoring_engine.py   — 各モニタのポーリング統括
    - execution/
      - (ExecutionEngine, order_manager, broker_factory, risk_manager, etc.)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - data/
      - pipeline.py             — データパイプライン / DuckDB 周りユーティリティ（参照）
      - stats.py                — zscore_normalize 等（研究用ユーティリティ）
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

実運用上の注意
--------------
- KABUSYS_ENV=live に設定する場合は事前に validate_config を通し、LINE 通知や kill switch の設定など本番向けガードを必ず確認してください。
- kill.flag や stop_requested.flag などのフラグファイルの扱いには注意してください。特に KILL_FLAG_CLEAR_ON_START が有効（1）だと起動時に自動で kill.flag を消してしまうため、本番では 0 を推奨します。
- データベースのパスやログディレクトリは権限やバックアップ方針を考慮して設定してください。
- OpenAI や外部 API の呼び出しはネットワーク障害やレート制限に備えたリトライロジックがありますが、API キーの管理・課金に注意してください。

トラブルシューティング（ヒント）
--------------------------------
- MONITOR_POLL_INTERVAL に 0 や負の値を設定すると無効扱いでデフォルト 60 秒にフォールバックします（ログで警告が出ます）。
- ログファイルが作られない場合は LOG_DIR 権限・存在を確認してください。失敗するとコンソール出力のみになります。
- psutil による優先度設定や CPU affinity が権限不足で失敗する場合は警告ログが出ますが処理は継続します。
- DuckDB / SQLite による SQL 実行時のエラーは validate_config である程度検出できます（PyYAML が入っていれば config YAML のパース検証も行います）。

ライセンス・貢献
----------------
本ドキュメントではライセンス情報は含めていません。実コードベースの LICENSE ファイルを参照してください。貢献は通常の GitHub ワークフロー（issue / PR）で受け付けてください。

最後に
------
この README は src/kabusys に含まれるコードの主要部分をもとに作成した概要・手引きです。各モジュールの詳細な使い方や実装仕様（Engine の設定項目、ブローカー API の仕様など）は該当ソースコード内ドキュメンテーション（docstring）や別ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要であれば README に追記すべき具体項目（例: 実行フロー図、設定テンプレート、運用手順書）を教えてください。