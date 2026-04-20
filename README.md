KabuSys — 日本株自動売買システム（簡易 README）
======================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング用ライブラリ兼実行スクリプト群です。本プロジェクトは以下の主要機能を備えています。

- 実行エンジン（ExecutionEngine）: 発注、注文管理、リスク管理などの実装（paper_trading モードを含む）
- 監視（Monitoring）: システム状態、注文ログ、リスク指標の定期ポーリングと永続化（SQLite）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制約
- リサーチ: ファクター計算（モメンタム / ボラティリティ / バリュー）や特徴量解析
- AI モジュール: ニュース NLP（OpenAI を使ったセンチメント）、市場レジーム判定
- 運用補助ツール: .env 設定ウィザード、設定検証、ペーパートレード検証レポート生成

主な機能一覧
-------------
- 実行環境切り替え: KABUSYS_ENV により development / paper_trading / live を切替
- Paper Trading 分離: paper_trading 時は MockBrokerClient を使用し専用 SQLite（data/paper_trading.db）に記録
- 監視 DB: SQLite に system_status / trade_logs / positions / risk_logs / dashboard を保持（init 関数あり）
- ポートフォリオ構築: 候補選定（スコア順）、等重・スコア重み、リスクベースの株数算出
- リサーチ: DuckDB 接続を受けて prices_daily / raw_financials を使ったファクター算出
- AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai_scores）およびレジーム判定（market_regime）
- ロギング: stdout + 日次ローテートファイル（logs/<app_name>.log、30日分保持）
- プロセス優先度設定: psutil を用いて優先度・CPU affinity を制御
- 運用ツール:
  - python -m kabusys.config_setup : .env の対話式作成/更新
  - python -m kabusys.validate_config : 環境変数 / config/*.yaml の事前検証
  - python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成

前提・依存関係
----------------
- Python 3.10+（| 型注釈などを使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- 任意: SQLite は標準ライブラリで OK

セットアップ手順
----------------
1. リポジトリをクローン／展開し、作業ディレクトリをプロジェクトルートにする。

2. 仮想環境を作成してアクティベート（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は手動で）
   - pip install duckdb psutil openai PyYAML

4. 初期 .env を対話式で作成
   - python -m kabusys.config_setup
   - ウィザードは必須項目（J-Quants トークン, Kabu API password など）を聞いて .env を生成します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（実行例）
----------------

基本的な起動スクリプト
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中の停止は data/stop_requested.flag を作成することで行えます。

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
  - デフォルトで 60 秒毎にポーリング。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能。
  - 監視は常に settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。

運用補助
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB の指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

AI / 研究系関数（プログラム内呼び出し）
- ニューススコア付与: kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
  - api_key 引数なしだと OPENAI_API_KEY 環境変数を使用
  - 書き込み先: ai_scores テーブル
- レジーム判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出し時の API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 本番での kill.flag 自動クリア（0 推奨）

停止・キルフラグ
----------------
- run_execution や run_monitoring はプロジェクトの data/stop_requested.flag（および Kill Switch は data/kill.flag）を監視します。フラグファイルの作成で外部から停止・強制停止を指示できます。
- KillSwitch クラスは条件（ドローダウン等）に応じて data/kill.flag を作成します。

ログ
----
- setup_logging により stdout と logs/<app_name>.log（日次ローテート、30日保持）へ出力します。
- ログディレクトリは環境変数 LOG_DIR で変更可能。作成失敗時はコンソール出力のみになります。

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内部の主要なファイル/モジュール構成（src/kabusys）です。実際のツリーはプロジェクトルートに src/ を含む想定です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/               — 発注・エンジン関連（Engine/OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用されるデータ/DB/flag 用ディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid など

開発・デバッグに関する注意
-------------------------
- .env の自動読み込み: config.py はプロジェクトルートにある .env / .env.local を自動で読み込みます（OS 環境変数を上書きしない）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Paper Trading は本番 DB を汚さないよう専用の SQLite を使用します。デフォルト挙動を理解して運用してください。
- AI 呼び出しは外部 API（OpenAI）を使います。API 呼び出しはリトライやフォールバックを組んでいますが、API キーとレート制限に注意してください。
- ローカルテストでは PyYAML がないと config/*.yaml の中身検証をスキップします。必要なら pip install PyYAML。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンスや配布ポリシーはリポジトリ側の LICENSE を参照してください（本 README には含めていません）。

問い合わせ・貢献
----------------
- バグ報告や機能改善提案はリポジトリの Issue を使ってください。
- 大きな設計変更や外部 API 仕様の変更がある場合は事前に Issue で相談ください。

以上が本リポジトリの概要・セットアップ・使い方・構成の説明です。必要があれば「実行例の詳しいコマンド」や「.env のサンプルテンプレート」などを追加で作成します。どの情報を詳しく出力しましょうか？