KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたコードベースです。  
DuckDB（分析用）と SQLite（監視／注文ログ）を使ったデータ処理、ExecutionEngine による発注制御、Monitoring によるシステム監視／Kill Switch、ファクター計算やポートフォリオ構築ロジック、LLM を使ったニュースセンチメント評価（OpenAI）などの機能を含みます。

主な機能
-------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード（KABUSYS_ENV に依存）を切り替え可能
  - Paper Trading 時は MockBrokerClient を使用し、本番 DB と分離（data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch により一定条件で Execution を停止（data/kill.flag）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）
  - セクター制約、レジーム乗数、ポジションサイズ計算（単元株丸め）
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算・統計サマリー
- AI（OpenAI）連携
  - ニュース記事のセンチメントスコアリング（news_nlp）
  - マクロニュース + ETF ma200 乖離から市場レジーム判定（regime_detector）
  - レート制限 / 5xx などのリトライ実装
- ユーティリティ
  - ロギングセットアップ（コンソール＋日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード、設定検証 CLI、ペーパートレード検証レポート生成

必要条件
-------
- Python 3.9+（コードは型アノテーション等を使用しています）
- 依存パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルチェック時に使用、任意）
- SQLite（標準ライブラリで利用可能）
- ネットワーク（OpenAI / API を使う場合）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt が用意されている場合は pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（例は下記参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合は --strict を付与

6. データディレクトリ
   - デフォルトでは data/ 配下に SQLite / DuckDB / PID / flag ファイルを作成します。自動作成されますが、権限に注意してください。

主要な環境変数（主なもの）
-------------------------
以下は主要な .env キー（.env.example を参照して作成してください）。

- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabus api のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使用する場合）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合は MockBrokerClient を使用し、別 DB に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種ファイルパス（必要に応じて上書き）

簡単な .env 例
---------------
KabuSys 用の最小例（実運用時は秘密情報は適切に取り扱ってください）:

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方
------

主要なエントリポイント（モジュールとして実行）:

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（例: MONITOR_POLL_INTERVAL=30）
    - 監視はどの環境でも sqlite_path（デフォルト data/monitoring.db）を使用して記録します
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が既に存在する場合は起動をスキップ
    - Execution 側も stop_requested.flag を監視し、存在したら安全停止を試みます
    - Kill Switch は data/kill.flag を書き込むことで Execution を停止させる仕組みです
    - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を消去します（本番での自動クリアは危険）

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit(1)）として扱います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定できます。環境変数 PAPER_TRADING_SQLITE_PATH も参照されます。

- AI / リサーチ関数（ライブラリ利用）
  - ai.score_news(conn, target_date, api_key=None) — raw_news を集約して ai_scores を書き換えます
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジームを算出して market_regime に書き込み
  - research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等は DuckDB 接続を渡して使用します

ロギング
-------
- kabusys.utils.logging_setup.setup_logging(app_name="execution") を各スクリプトで呼び出して統一的にログ出力を行います
- コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力
- LOG_DIR / LOG_LEVEL 環境変数で調整可能

停止フラグ / Kill Switch
-----------------------
- 停止要求（run_monitoring / run_execution のループ停止）:
  - プロジェクトルートの data/stop_requested.flag を作成すると実行ループが検知して停止します
- Kill Switch（リスク条件で Execution を停止）:
  - kabusys.monitoring.KillSwitch が判定すると data/kill.flag を書き込みます
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨

開発者向けメモ
--------------
- 設定の自動ロード:
  - config.Settings は .env/.env.local を自動で読み込みます（プロジェクトルートの検出は .git または pyproject.toml を基準）
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は存在しないカラムの追加などの簡易マイグレーションを行います
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI API の RateLimit / 5xx に対してリトライを実装しています
  - テスト時は _call_openai_api をパッチすることで外部 API 呼び出しを差し替え可能

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイル一覧（説明コメントから要約）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor のポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — （注文ログ監視、該当実装ファイルあり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各モニタを束ねるループ
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （通知管理、実装参照）

  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション制御）
    - broker_factory.py      — Broker クライアントのファクトリ（ペーパートレード/本番切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算・スケールダウン・単元丸め
    - risk_adjustment.py     — セクター制約・レジーム乗数

  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — ETF ma200 + マクロニュースでレジーム判定

  - portfolio, research, ai のテスト用ユーティリティや補助関数が関連

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

補足
----
- 本 README はコード内のコメント・ドキュメントを基に要約しています。詳細な挙動（SQL スキーマやアルゴリズムの細かい仕様）は各モジュールの docstring コメントを参照してください。
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知等の設定を十分に確認してください（validate_config が live 時のチェック・警告を実施します）。
- セキュリティ: .env ファイルは決して Git にコミットしないでください（config_setup も同旨の注意を出力します）。

問題や改善提案があればリポジトリの Issue に報告してください。