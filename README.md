# KabuSys

日本株向け自動売買システムのコアライブラリ群。バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、発注エンジン起動スクリプト、監視（Monitoring）・Kill Switch・LINE 通知などの運用用ユーティリティを含みます。

この README はリポジトリ内の主要コンポーネントと起動／セットアップ手順、使い方の概要をまとめたものです。

- 対応 Python: 3.10+
- 主要依存（最低限）: duckdb, psutil, openai, PyYAML（YAML 検証は任意）
  - インストール例:
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ python -m pip install --upgrade pip
    $ pip install duckdb psutil openai PyYAML

注意: 実運用では依存バージョンを固定した requirements.txt を用意して pip install -r でインストールすることを推奨します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 環境変数（主要）
- ディレクトリ構成（概要）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのコアライブラリ群です。
- ファクター計算・リサーチ（DuckDB ベース）、ポートフォリオ構築、発注ロジック、監視・リスクモニタ、AI を利用したニュースセンチメント評価等のモジュールを含みます。
- 実行スクリプトは KABUSYS_ENV に応じて挙動を変更（例: paper_trading であればモックブローカーを用いる等）。

機能一覧
- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト（本番 / ペーパートレード切替対応）。
  - process 優先度設定、PID ファイル出力、stop flag チェック機能を備えます。
- 監視関連
  - run_monitoring.py: SystemMonitor をポーリングして監視を行う起動スクリプト。
  - MonitoringDB（SQLite）にシステムステータス / 取引ログ / リスクログ / ダッシュボード等を永続化。
  - KillSwitch により条件を満たすと data/kill.flag を書いて Execution を停止可能。
- ポートフォリオ関連（純粋関数）
  - 銘柄選定、等分配／スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数。
- リサーチ
  - DuckDB を使ったファクター計算（momentum / volatility / value 等）、将来リターン・IC 計算、特徴量サマリ。
- AI 関連
  - news_nlp: OpenAI を用いたニュースの銘柄ごとのセンチメントスコア付与（ai_scores テーブルへ保存）。
  - regime_detector: ETF（1321）MA 乖離＋マクロニュースセンチメントを合成して市場レジーム判定を行う。
- ツール
  - config_setup.py: .env の対話式作成ウィザード
  - validate_config.py: 起動前に環境変数・config/*.yaml の妥当性チェック
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成

セットアップ手順（簡易）
1. リポジトリをクローンし Python 仮想環境を作成
   $ git clone <repo>
   $ cd <repo>
   $ python -m venv .venv
   $ source .venv/bin/activate

2. 必要パッケージをインストール
   $ pip install duckdb psutil openai PyYAML

3. .env の初期作成（推奨）
   - 対話ウィザードで .env を作成:
     $ python -m kabusys.config_setup
   - 手動で作成する場合はリポジトリの .env.example を参考にしてください。

4. 設定検証
   $ python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ等の作成（必要に応じて）
   - デフォルトでは data/ フォルダに SQLite / PID / kill.flag 等を配置します。
   - logs/ にログファイルが出力されます（setup_logging が自動で作成を試みます）。

主要な使い方（コマンド例）
- 実行エンジン起動（本番/ペーパーは KABUSYS_ENV で切替）
  $ python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db にログを保存します。

- 監視ループ起動
  $ python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - run_monitoring は KABUSYS_ENV に関係なく production（settings.sqlite_path）を監視 DB として使用します。

- .env を対話式に作る（再掲）
  $ python -m kabusys.config_setup

- 設定検証（再掲）
  $ python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  $ python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

プログラムからの利用例（ライブラリ呼び出し）
- DuckDB 接続を渡してファクター計算を行う例:
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 4, 1))

- AI ニューススコア付与（プログラム呼び出し）
  from kabusys.ai import score_news
  # duckdb_conn: duckdb connection (duckdb.DuckDBPyConnection)
  # target_date: datetime.date
  n_written = score_news(duckdb_conn, target_date, api_key="xxxx")

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- ログ
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector が参照）
- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - PID_FILE_PATH, KILL_FLAG_PATH: Settings 経由で上書き可能
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

簡単な .env の例
  KABUSYS_ENV=development
  JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  OPENAI_API_KEY=sk-...

ディレクトリ構成（主要ファイル・パッケージ）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理・自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 取引ログ監視（存在）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み・評価
    - monitoring_engine.py   — 各 Monitor をまとめる
    - alert_manager.py       — アラート送信（LINE 等の実装想定）
  - execution/               — ExecutionEngine・OrderManager 等（参照あり）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

運用上の注意
- KABUSYS_ENV が live の場合は実際に発注が行われます。設定（特に API キー類・Kill Switch・LINE 通知設定）を慎重に確認してください。
- run_monitoring / run_execution は data ディレクトリ内の stop_requested.flag / kill.flag を監視/生成します。運用時はこれらのフラグファイル操作を理解してください。
- process_priority（高優先度設定）は OS 権限により失敗する場合があります（警告ログが出ますが処理は継続します）。
- OpenAI を使う機能は OPENAI_API_KEY が必要です。API 呼び出しは課金対象になるため、本番での利用は注意してください（レート制限・リトライロジックあり）。
- DuckDB / SQLite のパスは .env で調整可能。データファイルはバックアップ・権限管理を行ってください。

---

さらに詳しい情報
- 各モジュールの docstring に設計意図・引数仕様・返り値が記載されています。実装をカスタマイズする場合はそちらを参照してください。
- config/*.yaml を使う構成であれば、scripts/generate_config.py（存在する場合）でテンプレート生成が可能です（validate_config からも参照）。

この README はリポジトリ内の現行コードから生成しています。実際の運用手順や依存バージョンはプロジェクトのポリシーに合わせて調整してください。