KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのプロジェクトです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理を担う（本番 / ペーパートレード切替対応）
- 監視コンポーネント（Monitoring）：システム稼働・注文状態・リスク指標の定期チェック、Kill Switch 書き込み
- ポートフォリオ構築モジュール：銘柄選定・重み付け・ポジションサイズ算出・セクター制限などの純粋関数群
- リサーチモジュール：ファクター計算、特徴量探索、IC 計算など DuckDB を用いた分析機能
- AI モジュール：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度制御、ツール類（検証レポート生成等）

主な機能一覧
-------------
- run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading/live を切替）
  - paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離
- run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔を変更可能）
- config_setup: 対話式ウィザードで .env を初期作成 / 更新
- validate_config: .env と config/*.yaml の存在・妥当性チェック CLI
- tools/paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）
- portfolio: 銘柄選定、重み計算、ポジションサイズ算出、セクター上限・レジーム乗数処理
- research: calc_momentum / calc_volatility / calc_value、forward returns、IC、統計サマリー等
- ai: ニュース NLP（OpenAI）で銘柄ごとのセンチメント算出、regime_detector によるレジーム判定
- monitoring: SQLite ベースの永続化層（monitoring_db.py）、RiskMonitor、TradeMonitor、MonitoringEngine、KillSwitch、AlertManager（注：AlertManager 実装ファイルが別にある場合があります）
- utils: logging_setup（コンソール＋日次ローテーションファイル）、process_priority（優先度・CPU affinity）など

前提と推奨環境
----------------
- Python >= 3.10（型注釈に Python 3.10 の union 型構文を使用）
- 推奨依存パッケージ（少なくとも以下をインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の構文検査を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

セットアップ手順
----------------
1. ソースを取得
   - git clone .../kabusys.git
   - リポジトリルートが .git または pyproject.toml を基準に自動検出されます。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合は上記を個別インストールしてください）

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - LOG_LEVEL — デフォルト: INFO
   - OPENAI_API_KEY — AI 機能を利用する場合に必要
   - PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject）

   自動環境読み込み:
   - プロジェクトルートに .env/.env.local があると、起動時に自動で読み込まれます。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

使い方（主要コマンド）
---------------------
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に書き込み（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動しない
    - 実行中に stop flag（data/stop_requested.flag）を作成するとエンジンを停止

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は Settings に従い sqlite_path（data/monitoring.db）にログを残す
  - run_monitoring は stop_requested.flag を見てループを終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

プログラム的な API（例）
-----------------------
多くの機能はモジュール関数として利用できます。例:

- ニュース NLP（AI）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn: duckdb.DuckDBPyConnection, target_date: datetime.date, api_key: str | None)

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

- ファクター計算（リサーチ）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

停止・Kill Switch
-----------------
- run_execution / run_monitoring はプロジェクトルート配下の data/stop_requested.flag を監視して停止します（手動で作成するとプロセスが停止）。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path でパスを変更可能）。
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、エンジン起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ
-----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- コンソールには stdout にも出力されます（StreamHandler）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

ディレクトリ構成（主要ファイル）
---------------------------------
以下はソースツリー（src/kabusys/）の主要ファイル・ディレクトリの抜粋です。

- kabusys/
  - __init__.py
  - config.py                    # 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py              # .env 対話式ウィザード
  - validate_config.py           # 設定検証 CLI
  - run_execution.py             # ExecutionEngine 起動スクリプト
  - run_monitoring.py            # SystemMonitor 起動スクリプト
  - execution/                   # Execution 関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py           # SQLite 永続化層（テーブル作成・ログ記録）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装がある場合)
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
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env に機密情報を含むため絶対に Git にコミットしないでください。
- データベースやログの保存先（data/, logs/）は適切なバックアップ・パーミッション管理を行ってください。
- OpenAI など外部 API を利用する機能は API キーの課金・レート制限を考慮して利用してください。
- run_execution 起動時は KILL_FLAG_CLEAR_ON_START の設定に注意（本番で自動クリアすると危険です）。
- paper_trading モードを使うことで本番 DB と完全に分離して動作検証が可能です。

ヘルプ / その他
----------------
- 主要スクリプトはそれぞれモジュールとして実行可能です（python -m kabusys.<module>）。
- 設定やデータベーススキーマの更新は init_monitoring_db() によってマイグレーションの一部（カラム追加等）を行います。既存データの大幅なスキーマ変更は別途マイグレーション計画が必要です。

お問い合わせ・貢献
-----------------
コードの改善やバグ修正、ドキュメント追加のプルリクエストは歓迎します。README に書かれていない実装の詳細や設計意図については各モジュール内の docstring を参照してください（詳細な設計ドキュメント: PortfolioConstruction.md / StrategyModel.md 等がある場合はそれらも参照）。

--- 
この README はリポジトリ内のソースコード（docstring と実装）を基に作成されています。さらに詳しい運用手順やデプロイ手順（systemd / docker / kubernetes 等）を導入する場合は追記を検討してください。