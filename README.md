# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ / 起動スクリプト群）。  
このリポジトリは、戦略の研究・ポートフォリオ構築・発注エンジン・監視・AI支援（ニュースNLP / レジーム判定）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 初期設定（.env）
  - 設定検証
  - 実行（ExecutionEngine / Monitoring）
  - ペーパートレード検証レポート
  - AI 機能に関する注意
- 環境変数（主要）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システム用ユーティリティ群です。  
  主なコンポーネントは戦略研究（DuckDBを用いたファクター計算）、ポートフォリオ構築、発注・リスク管理の実行エンジン、そしてシステム監視・アラート機能です。  
- 起動スクリプトは application レイヤ（run_execution.py, run_monitoring.py など）として提供され、環境に応じた挙動（paper_trading / live / development）をサポートします。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを区別し、ペーパートレード時は MockBrokerClient と別データベース（data/paper_trading.db）を使用
  - リスク管理（RiskManager）、注文管理（OrderManager）、差戻し（Reconciler）などの組み立て
  - 停止フラグ（data/stop_requested.flag）による安全停止
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor 等をポーリングし監視データを SQLite に記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話的に .env を生成・更新
- 設定検証 CLI（validate_config.py）
  - .env / config/*.yaml の基本検査（--strict で警告をFAIL扱いに）
- Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・成功率・レイテンシ等を集計し PASS/FAIL を判定
- 研究モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（情報係数）、統計サマリーなど
- ポートフォリオ構築（portfolio）
  - 候補選定、スコア重み・等配分、セクター上限適用、ポジションサイズ計算（単元株丸め等）
- AI モジュール（ai）
  - news_nlp: ニュースを OpenAI に送り銘柄ごとのセンチメントスコアを生成して DuckDB に書き込む
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントを合成して市場レジーム判定
- ユーティリティ
  - logging_setup: 標準化されたログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity の簡易設定
- 監視（monitoring）
  - MonitoringDB: SQLite テーブル定義と CRUD
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - kill.flag による ExecutionEngine 強制停止（Kill Switch）

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境の用意（推奨: 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 実行環境により他の依存が必要になる場合があります（requests等はここに含まれていないが利用するブローカー実装に依存）。
4. ディレクトリ準備
   - data/ と logs/ は自動作成されますが、手動で作る場合:
     - mkdir -p data logs
5. 初期設定（対話式）
   - python -m kabusys.config_setup
     - .env を作成／更新します（J-Quants / kabuステーション のトークン等を設定）
6. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 問題があれば .env や config/*.yaml を修正
7. DB（DuckDB / SQLite）
   - デフォルトでは data/kabusys.duckdb と data/monitoring.db（ペーパートレードは data/paper_trading.db）を使用します。必要に応じて .env でパスを上書きしてください。

使い方（主要なコマンド）
- 実行エンジンを起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動時に execution.pid を data/ に書きます。停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl+C）を送ることで行います。
  - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し DB は paper_sqlite_path（デフォルト data/paper_trading.db）に分離されます。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番 sqlite_path（.env の SQLITE_PATH）を参照して監視ログを書き込みます（環境に依らず本番 path を使う設計）。
  - 停止は data/stop_requested.flag を作るか Ctrl+C。
- .env の作成（対話）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
- AI 機能（news_nlp / regime_detector）
  - OpenAI の API キーが必要です。環境変数 OPENAI_API_KEY を設定するか、関数呼び出しで api_key を渡します。
  - news_nlp.score_news(), regime_detector.score_regime() は DuckDB 接続と target_date を与えて呼び出します。
  - API 呼び出し時のリトライやフォールバックが用意されていますが、API キー未設定時は ValueError になります。
- 強制停止 / Kill Switch
  - KillSwitch は監視結果により data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを与えます。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の挙動を考慮します（.env で制御）。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — default: development
  - paper_trading の場合、ExecutionEngine は MOCK ブローカーを用い DB を分離
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存先（default: logs）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。run_monitoring で参照）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。productionでは 0 推奨）

自動 .env ロードについて
- モジュール読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば、.env と .env.local を自動読み込みします。
- OS 環境変数は上書きされません。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

停止 / フラグファイル
- data/stop_requested.flag: run_* スクリプトによるポーリングループの安全停止判定に使用（存在するとループ終了）
- data/kill.flag: KillSwitch により書き込まれる停止指示（ExecutionEngine での扱いに注意）
- data/execution.pid: ExecutionEngine の PID ファイル（デフォルト）

ログ
- ログはコンソール（stdout）とログファイル（logs/<app_name>.log、日次ローテート）に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging による統一的な管理。

例: 最小 .env（参考）
- .env.example がない場合は下記を最低限設定してください（機密値は実際の値に置換）。
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるが実装は別ファイル)
  - execution/                 — Execution 関連（BrokerFactory, Engine, OrderManager, Reconciler, RiskManager 等）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時の DB / フラグ / PID 等（作成される）

補足・運用上の注意
- KABUSYS_ENV が live のときは設定を慎重に確認してください。validate_config は本番向けの追加警告を出します。
- 実行時プロセス優先度は起動直後に高優先度に設定されます（psutil を使用）。権限不足で設定不可の場合は警告が出ますが処理自体は継続します。
- AI 機能を利用する際は API 利用料金とレート制限に注意してください。news_nlp と regime_detector はリトライバックオフを備えていますが、完全な故障耐性ではありません。
- DuckDB / SQLite のパスは .env で変更可能です。ペーパー/本番 DB を混在させないように設計されています（paper_trading は paper_sqlite_path を使用）。

ライセンス・貢献
- README に記載が無い場合はリポジトリのルートにある LICENSE を参照してください。貢献方法は PR と Issue を通じて行ってください。

---

この README はコードベースの説明を要約したものです。より詳しい実装や運用ルール、設定項目の説明は各モジュールのドキュメンテーション（ソース内 docstring）をご参照ください。必要であれば起動例や systemd / supervisor 用のユニット定義等のテンプレートも提供します。どの項目を追加で詳細化しますか？