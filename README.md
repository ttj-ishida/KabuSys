# KabuSys — 日本株自動売買システム

（この README はリポジトリ内のソースコードに基づいて作成された技術ドキュメントです）

概要、使い方、セットアップ方法、主要コンポーネント構成などを日本語でまとめています。

## プロジェクト概要
KabuSys は日本株向けの自動売買システムのコアライブラリ／ランタイムです。  
主な役割は次のとおりです。

- 戦略（ファクター計算・特徴量・ポートフォリオ構築）を提供する research / portfolio モジュール
- ExecutionEngine による発注ロジック（本番／ペーパートレードの切替含む）
- Monitoring 系（システム状態、取引ログ、リスク監視、Kill Switch）
- AI を用いたニュースセンチメントや市場レジーム判定（OpenAI API 利用）
- 解析用 DuckDB、監視用 SQLite などの永続化をサポート
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）

バージョン: __version__ = 0.1.0

---

## 機能一覧
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local、環境変数優先）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行（Execution）
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）
  - paper_trading は専用 SQLite（デフォルト: data/paper_trading.db）に分離
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視プロセス起動スクリプト: python -m kabusys.run_monitoring
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視ログ永続化（SQLite、スキーマは monitoring_db.init_monitoring_db）
- 研究・解析
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・特徴量サマリ
  - DuckDB を利用した収集・計算（prices_daily / raw_financials など）
- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）: raw_news から銘柄別スコアを生成
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API の呼び出しにリトライ/バックオフやレスポンス検証を内包
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提条件 / 必要パッケージ（例）
以下は最低限必要となる主要パッケージの例です（環境や機能利用による）。

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）

インストール例（開発環境）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate（Windows: .venv\Scripts\activate）
- 必要ライブラリを pip でインストール（requirements.txt があればそれを使うのが望ましい）:
  - pip install duckdb psutil openai pyyaml

パッケージのインストール（ローカル開発）:
- pip install -e .  # setup.py/pyproject による editable install が用意されている場合

---

## 環境変数（主なもの）
設定は環境変数または .env ファイルで行います。自動ロード順は OS 環境 > .env.local > .env。（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

必須（起動前に設定すること）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。run_monitoring から環境変数で上書き可能（デフォルト: 60）

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

※ .env は機密情報を含むため Git に絶対にコミットしないでください。

---

## セットアップ手順（推奨フロー）
1. リポジトリをクローンして仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （要件が用意されていれば）pip install -r requirements.txt

3. 初期設定ファイル（.env）の作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードに従って必要な値を入力してください（J-Quants / kabu API 情報などは必須）

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリ作成（必要に応じて）
   - デフォルトで data/, logs/ を使います。os 環境や .env のパスに合わせて作成してください。

---

## 使い方（主要スクリプト・コマンド）
- 環境設定（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 動作: 設定に応じて本番/ペーパートレードを切替。paper_trading の場合は専用 DB に記録。
  - 実行中に data/stop_requested.flag を置くと安全終了。

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - Monitoring はどの KABUSYS_ENV でも sqlite_path（監視 DB）の本番パスを使用します。
  - 実行中に data/stop_requested.flag を置くと監視ループが終了します。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（スクリプト内で呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ
  - 共通ロガー設定: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - 出力場所: logs/<app_name>.log（デイリーローテーション、30日分保持）。コンソールは stdout に出力。

---

## 実行時のファイル／フラグ
- data/execution.pid — ExecutionEngine の PID（起動中に書き込まれます）
- data/kill.flag — Kill Switch が発動したときに作成されるファイル（Execution を停止する合図）
- data/stop_requested.flag — run_*.py がこのファイルを検知すると終了します（手動で停止要求を出すためのフラグ）
- デフォルト DB:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

---

## 主要コンポーネントの説明（概略）
- config.py / config_setup.py / validate_config.py
  - 環境変数読み込み、設定ウィザード、自動検証を担う
- run_execution.py
  - ExecutionEngine の起動スクリプト。プロセス優先度設定や DB 接続、コンポーネント初期化を行う
- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL で間隔を指定可能
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と永続化 API（MonitoringDB クラス）
  - system_monitor.py: CPU / メモリ / ディスク / PID / データ鮮度監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: Kill Switch 判定と kill.flag 書き込み
  - monitoring_engine.py: 各モニタを束ね、アラートや Kill Switch 評価を行う
- execution/
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, BrokerClientFactory など発注周りの実装（詳細はコード参照）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定、重み付け、サイズ計算、セクター上限・レジーム乗数
- research/
  - factor_research.py, feature_exploration.py: ファクター計算、将来リターン、IC、統計サマリー（DuckDB 接続を入力に取る）
- ai/
  - news_nlp.py: ニュース記事を集約して OpenAI でスコアリング、ai_scores テーブルへ保存
  - regime_detector.py: ETF MA とマクロニュースを合成して市場レジームを判定
- utils/
  - logging_setup.py: ログの統一設定（コンソール + 日次ローテーションファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

src/kabusys/ai/
- __init__.py
- news_nlp.py
- regime_detector.py

src/kabusys/monitoring/
- monitoring_db.py
- monitoring_engine.py
- system_monitor.py
- risk_monitor.py
- trade_monitor.py (実装参照)
- kill_switch.py
- alert_manager.py (実装参照)

src/kabusys/execution/
- execution_engine.py
- order_manager.py
- order_repository.py
- broker_factory.py
- reconciler.py
- risk_manager.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py
- __init__.py

（実際のツリーはリポジトリを参照してください）

---

## 運用上の注意 / ベストプラクティス
- .env に機密情報（API トークン、パスワード）を格納する場合は Git 等にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch をクリアしないようにするため）。
- Monitoring はデフォルトで monitoring.sqlite（SQLITE_PATH）を使用します。paper_trading 環境でも監視 DB は本番の sqlite_path を使用する設計です（監視の継続性を保つため）。
- ExecutionEngine の安全停止は data/stop_requested.flag（run_* スクリプト）や Kill Switch（kill.flag）で制御します。手動停止時は適切にフラグを書き込むかプロセスを終了してください。
- OpenAI API を使う場合、レスポンス検証・クリップ・リトライ機構が組み込まれていますが、API キーやコスト管理は運用で注意してください。

---

必要に応じて README を拡張して、より詳細な設計ドキュメント（API 仕様、DB スキーマ、Engine のシーケンス図など）を追加してください。コードにコメントや docstring が豊富に含まれているため、各モジュールの詳細は該当ファイルを参照することを推奨します。