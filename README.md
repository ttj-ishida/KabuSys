KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買フレームワーク「KabuSys」の実装（ライブラリ＋運用スクリプト群）です。
戦略のファクター計算、ポートフォリオ構築、ポジションサイズ算出、ExecutionEngine（発注実行）、
監視（Monitoring）・Kill Switch、AI を用いたニュース評価・レジーム判定などの機能を含みます。

要点
- モジュール式で戦略・実行・監視を分離
- Paper trading（ペーパートレード）と Live（本番）を環境変数で切替可能
- DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／レジーム判定機能を有する
- ロギング、プロセス優先度設定、簡易 CLI ウィザード／検証ツールを提供

主な機能
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に記録
  - PID ファイル管理、停止フラグの監視
- 監視（Monitoring）ポーリングループ（run_monitoring.py / MonitoringEngine）
  - CPU/メモリ/ディスク監視、データ鮮度チェック、プロセス生存確認
  - RiskMonitor（ドローダウン／ポジション上限監視）、TradeMonitor、KillSwitch、AlertManager と連携
- 環境設定ウィザード（config_setup.py）
  - .env の対話的作成・更新を支援
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック（--strict オプションあり）
- Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ペーパートレード DB を参照して稼働率、注文成功率、レイテンシ等をレポート化
- ポートフォリオ構築ユーティリティ（portfolio/*）
  - 候補選定、等金額／スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出
- 研究用モジュール（research/*）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリー
- AI モジュール（ai/*）
  - ニュースを LLM でスコア化し ai_scores テーブルへ書込む（news_nlp.score_news）
  - マクロニュース＋ETF MA を使った日次レジーム判定（regime_detector.score_regime）
- ユーティリティ（utils/*）
  - ログ設定、プロセス優先度／CPU affinity 設定など

前提／依存関係（代表）
- Python 3.10+（型注釈に Union | 演算子等を使用）
- pip install で次をインストールする想定:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルの検証を行う場合）
（requirements.txt は本リポジトリに含まれていないため、使用する機能に応じて上記をインストールしてください）

セットアップ手順（ローカル開発）
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （用途に応じて他パッケージを追加）

4. データ / ログ ディレクトリを作成
   - mkdir -p data logs

5. 環境変数設定（.env）
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照（リポジトリに example がない場合は下表を参考）

主要な環境変数（代表、デフォルト）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — news_nlp / regime_detector を使う場合に必要
- KABUSYS_ENV — 有効値: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）を利用
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH — ファイルパスの上書き可能

自動 .env 読み込み
- config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出し、
  .env を自動で読み込みます（.env.local は .env を上書き）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

実行方法（代表）
- ExecutionEngine（実行エンジン）を起動:
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid（デフォルト）等を使用し、data/stop_requested.flag が作られると停止します。
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB に記録され、本番 DB と分離されます。

- Monitoring を起動（デフォルト 60 秒ポーリング、環境変数 MONITOR_POLL_INTERVAL で変更可）:
  - python -m kabusys.run_monitoring
  - 監視は常に設定ファイルの sqlite_path（本番 monitoring.db）を使用します（KABUSYS_ENV に依存しない）。
  - 停止: data/stop_requested.flag を作成するか Ctrl+C

- 環境ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

ライブラリ API（簡単な使い方）
- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - 候補選定 → 重み計算 → ポジションサイズ算出の順で呼ぶ

- 研究用（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - DuckDB 接続を作成し prices_daily / raw_financials 等のテーブルを用意して呼び出す

- AI スコアリング（ニュース）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)  # api_key が None の場合 OPENAI_API_KEY 環境変数を参照

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

重要な運用ファイルと挙動
- data/stop_requested.flag — run_execution.py / run_monitoring.py が存在を検知して安全停止
- data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（存在する場合は起動時に警告／停止）
- PID ファイル（data/execution.pid 等） — 実行スクリプトがプロセス管理に使用
- ログ: デフォルト logs/<app_name>.log（utils.logging_setup が設定。LOG_DIR 環境変数で変更可）

運用上の注意
- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を設定することを推奨
- KILL_FLAG_CLEAR_ON_START=1 は本番では危険（Kill Switch が自動でクリアされるため）
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能。0 以下の値は無効でデフォルト 60 秒にフォールバック
- run_execution は paper_trading の場合 DB を分離（settings.paper_sqlite_path）するためテストと本番のデータが混ざらない

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込み含む）
  - config_setup.py           — .env 対話型ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py, alert_manager.py 等が想定される)
  - utils/
    - logging_setup.py
    - process_priority.py

トラブルシューティング（よくある事例）
- DuckDB / SQLite ファイルが見つからない:
  - .env の DUCKDB_PATH / SQLITE_PATH を確認、必要ならディレクトリを作成
- OpenAI API 関連エラー:
  - OPENAI_API_KEY が設定されているか確認。API 呼び出しはリトライ・フォールバック実装があるが、
    連続失敗時は機能が使えない（news/regime のスコアは省略またはデフォルトにフォールバック）
- プロセス優先度設定に失敗（アクセス拒否等）:
  - utils.process_priority は権限不足時に警告を出してスキップします（安全策）

開発／拡張メモ
- DuckDB をデータソースとしてファクター計算を行う設計のため、prices_daily / raw_financials 等のテーブル整備が重要
- ExecutionEngine / Broker クライアントは抽象化されており、ブローカーや注文ロジックの差替えが可能
- AI 関連は OpenAI の JSON mode を使用し、レスポンス検証を厳密に行うことで LLM の出力揺らぎに対応

最後に
- まずは python -m kabusys.config_setup で .env を用意し、python -m kabusys.validate_config で検証してください。
- 開発環境では KABUSYS_ENV=development を使い、本番運用前に paper_trading で動作確認することを推奨します。

必要であれば、この README をベースに「デプロイ手順」「systemd サービス定義」「詳しい CLI リファレンス」「config/*.yaml のフォーマット仕様」などの追補ドキュメントを作成します。どの項目を優先して詳細化するか指示してください。