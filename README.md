KabuSys
=======

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）の簡易 README です。  
この README はリポジトリ内の主要モジュールから抽出した情報を元に作成しています。

概要
----
KabuSys は日本株の自動売買フレームワークです。  
主な役割は以下になります。

- データ（DuckDB / SQLite）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（ブローカー経由の発注ロジック、Paper Trading 対応）
- 監視（System / Trade / Risk モニタ）と Kill Switch（停止フラグ）の仕組み
- AI 支援（ニュースのセンチメント評価、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、検証レポート等）

主な特徴
--------
- 環境別分離:
  - KABUSYS_ENV により "development" / "paper_trading" / "live" を切替
  - paper_trading では MockBrokerClient を使用し、paper_trading 用 DB に記録
- 設定管理:
  - .env / .env.local の自動読み込み（無効化可能）
  - 対話式ウィザード（python -m kabusys.config_setup）で .env を生成
  - 設定検証 CLI（python -m kabusys.validate_config）
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch により重大リスク時に ExecutionEngine を停止
- ポートフォリオ構築:
  - 候補選定、等金額 / スコア重み、リスクベースの株数決定、セクター上限等を純粋関数で実装
- 研究（research）:
  - ファクター（Momentum / Volatility / Value）計算、将来リターン、IC 計測、統計サマリ
  - DuckDB を使った SQL ベース実装
- AI モジュール:
  - news_nlp: OpenAI を用いたニュースの銘柄ごとセンチメント評価（ai_scores）
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して日次レジーム判定
- 運用ツール:
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------

前提
- Python 3.10 以上を想定（typing の | 等を利用）
- SQLite は標準ライブラリで利用
- 推奨外部パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証に使用。必須ではないが推奨）

例（仮想環境を作って依存をインストール）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール
  - pip install duckdb psutil openai pyyaml

プロジェクト初期化
1. リポジトリのルート（.git や pyproject.toml があるディレクトリ）に移動
2. .env を作成:
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
3. 設定を検証: python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit(1)）扱いになります
4. ディレクトリ確認:
   - data/（データベースやフラグファイル）
   - logs/（ログファイルは logs/<app_name>.log）
   必要に応じて作成されますが、パーミッション等で失敗する場合は手動作成してください。

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API
- KABU_API_PASSWORD — （必須）kabuステーション API
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
--------------------

起動スクリプト
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は常に本番の sqlite_path を参照（環境にかかわらず）
  - 停止方法: data/stop_requested.flag を作成するとループが検知して終了

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - Execution は data/stop_requested.flag の存在を検知して停止
  - PID ファイル (デフォルト data/execution.pid) を生成

設定関連
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

運用ツール
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

ライブラリ的な利用（例）
- AI ニューススコアを生成して DB に書き込む（Python から呼ぶ例）:
  from kabusys.ai.news_nlp import score_news
  import duckdb, os
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,1), api_key=os.environ.get("OPENAI_API_KEY"))

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,1), api_key=...)

注意点 / 運用上のポイント
- paper_trading 環境は本番 DB と分離されています。PAPER_TRADING_SQLITE_PATH を利用してください。
- Kill Switch は data/kill.flag を作成すると ExecutionEngine を停止させるための仕組みです。重要な本番設定では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- ログは logs/<app_name>.log（日次ローテーション）とコンソールに出力されます。ログディレクトリが作れない場合はコンソールのみになります。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードをオフにするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API など外部 API を使う箇所はエラーに対してフェイルセーフ設計（リトライ・フォールバック）されていますが、課金・レート制限に注意してください。
- config/*.yaml（system_config.yaml 等）は一部の検証や動作で参照されます。存在しない場合は警告が出ます。生成スクリプト（scripts/generate_config.py 等）がある想定ですが、リポジトリ内に無い場合は手動で用意してください。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の代表的なモジュール一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロードと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化・読み書き
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （取引監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch（flag ファイル管理）
    - monitoring_engine.py   — 各 Monitor を束ねる実行ロジック
    - alert_manager.py       — （LINE など通知管理、存在推定）
  
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig / run_session 等）
    - broker_factory.py      — Broker クライアント生成（Mock / Live 切替）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化（SQLite 等）
    - risk_manager.py        — 実行時のリスク制御（Rate limit / Utilization 等）
    - reconciler.py          — 注文とブローカー状態の整合処理

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算（select_candidates, calc_*）
    - position_sizing.py     — 株数計算（risk_based / equal / score）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄別センチメント算出
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力

（実際のファイル一覧はリポジトリを参照してください。）

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE を参照してください（本 README では未記載）。

最後に
------
この README はコードベース内コメント・ドキュメント文字列から自動的に要約したものです。  
実運用時は .env の設定値や config/*.yaml の内容、ブローカー API の仕様、OpenAI の API キー管理、ログ・DB のバックアップ方針などを十分に確認した上で運用してください。必要であれば README を拡張してデプロイ手順や運用手順を明記することを推奨します。