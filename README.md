KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python パッケージです。
主な役割は以下のとおりです。

- 戦略・ポートフォリオ構成（ファクター計算、ポジションサイズ算出）
- 注文実行エンジン（実口座 / ペーパー取引の分離）
- システム監視（稼働監視、注文・リスク監視、Kill Switch）
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- 研究用ユーティリティ（ファクター評価、IC 計算、レポート）

機能一覧
--------
主な機能（抜粋）：

- execution
  - 実行エンジン起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象／ペーパートレード用の分離
  - 注文管理・リコンサイル・リスク管理の統合

- monitoring
  - 定期ポーリング監視エンジン（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor による各種チェック
  - Kill Switch（data/kill.flag）を使った安全停止
  - 監視ログ永続化（SQLite）: system_status, trade_logs, risk_logs, positions, dashboard

- portfolio / research
  - 銘柄選定・重み算出（等配分・スコア加重）
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン / IC / 統計サマリー等の研究ユーティリティ（DuckDB ベース）

- ai
  - ニュース NLP（OpenAI）を用いた銘柄毎センチメントスコアリング
  - レジーム判定（ETF MA とマクロニュースの LLM 結果を合成）

- tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report.py）

- utils
  - 統一ロギング設定（タイムローテート、コンソール出力）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 環境変数ロード・設定管理（.env 読み込み・Settings クラス）

セットアップ手順
----------------

1. Python バージョン
   - Python 3.10+（ソースに | 型ヒントや modern typing 構文を使用）

2. 必要パッケージ（代表例）
   - pip でインストール（requirements.txt があればそれを使ってください）
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証を行う場合に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. リポジトリルートの準備
   - data/ および logs/ ディレクトリが自動作成される処理が多いですが、必要に応じて手動作成しても OK。
   - .env を作成（下記参照）。対話式ウィザードで作成することも可能（config_setup を使用）。

4. .env の作成（推奨）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 主要環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時）
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - LOG_LEVEL, LOG_DIR など
   - 自動ロード挙動:
     - パッケージ import 時にプロジェクトルートを特定して .env / .env.local を自動ロードします。
     - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにできます

使い方
------

基本的な実行方法（プロジェクトルートで）:

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と完全分離されます。
    - エンジンは data/execution.pid に PID を書きます。
    - 停止フラグ: data/stop_requested.flag が存在すると起動中のエンジンを停止します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
    - 監視プロセスは Settings.sqlite_path（本番の monitoring DB）を使います。Monitoring は KABUSYS_ENV に関係なく sqlite_path を使用します。
    - 停止フラグ: data/stop_requested.flag を検知すると監視ループを終了します。

- .env の対話式セットアップ
  - python -m kabusys.config_setup
  - ウィザードに従って .env を生成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - 環境変数や config/*.yaml の整合性をチェックします（PyYAML があると YAML のパースも検証）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

重要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
  - paper_trading: Mock ブローカ・専用ペーパートレード DB を使用
  - live: 本番モード（実際に発注されるため注意）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必須
- DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR: ログ出力の設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリア (0/1)

Kill Switch / 停止フラグ
-----------------------
- Kill Switch は監視コンポーネントが条件（ドローダウン超過等）を検出した場合に data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag をチェックし、存在すると起動を抑止する / 既存起動中に監視で検出されれば停止されます。
- 手動停止や運用上の一時停止用に data/stop_requested.flag を用います。run_monitoring / run_execution のループはこのファイルを検知して終了します。
- KILL_FLAG_CLEAR_ON_START=1 を本番に設定するのは危険です（自動的に Kill をクリアしてしまうため）。

ログと監査
----------
- ロギングは kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
  - コンソール出力は stdout、ファイルは日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）。
  - LOG_DIR 環境変数でログディレクトリを変更可能。

開発・テストに関する注意
------------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB/SQLite ファイルは相対パスで指定できますが、絶対パスや expanduser が使われます。
- OpenAI 呼び出し部分は外部 API に依存するため、単体テストではモック化が推奨されています（モジュール内の _call_openai_api を patch する等）。

ディレクトリ構成
----------------

（src/kabusys 以下の主要ファイル・ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコア化
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化ラッパ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態 / データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — kill.flag の作成 / 評価
    - （trade_monitor 等の実装ファイルが存在する想定）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - （execution, data, strategy 等のサブパッケージが存在する想定）

補足 / 運用上のヒント
--------------------
- 本番運用時は KABUSYS_ENV=live を必ず確認のうえ設定してください（validate_config が警告を出します）。
- paper_trading モードを活用して、本番と完全に分離した DB（PAPER_TRADING_SQLITE_PATH）で挙動確認を行ってください。
- OpenAI を使う機能は呼び出し回数・レート制限に注意し、API キーの管理を徹底してください。
- 監視・Kill Switch は運用保護の最終ラインです。KILL_FLAG_CLEAR_ON_START を不用意に有効にしないでください。

ライセンス・バージョン
---------------------
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

---

何か追記してほしい項目（例: 必要な requirements.txt の具体的内容、各 CLI の詳細オプション、サンプル .env テンプレートなど）があれば教えてください。