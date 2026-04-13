# KabuSys

KabuSys は日本株向けの自動売買システム用ライブラリ群です。注文生成・約定・リコンシリエーション（復旧）、リスク管理、ポートフォリオ構築、監視（ログ永続化・アラート・ダッシュボード）、および研究/AI 支援（ファクター計算、ニュースセンチメント、レジーム判定）を含みます。

以下はこのリポジトリの README（日本語）です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 主要環境変数（簡易一覧）
- 備考

---

プロジェクト概要
- 日本株自動売買システムのコアコンポーネント群をモジュール化したコードベース。
- 発注ロジック（OrderManager / ExecutionEngine）、ブローカー抽象化（BrokerClientFactory 等）により本番・ペーパートレードを切替可能。
- 監視（MonitoringEngine）でプロセス死活、注文滞留、約定異常、ドローダウンなどを検出・ログ化。LINE による通知や streamlit ダッシュボード表示をサポート。
- DuckDB を用いた時系列データ / ファクター計算、OpenAI（gpt-4o-mini）を用いたニュース NLP、レジーム判定の実装を含む。

機能一覧
- Execution
  - 注文作成・送信・状態同期（OrderManager, Reconciler）
  - RiskManager による発注制約（最大ポジション比率、利用率など）
  - Paper trading 用の MockBroker をサポート（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション数上限の監視
  - KillSwitch: フラグファイルにより ExecutionEngine を停止させる仕組み
  - AlertManager: LINE へのプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視データ表示）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重の重み付け
  - セクターキャップ適用、レジームに応じた乗数
  - ポジションサイズ計算（単元丸め、aggregate cap、コストバッファー）
- Research（研究用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースセンチメント（OpenAI を使った銘柄別スコア化）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- Tools
  - paper_verification_report: Paper Trading データの検証レポート出力
  - streamlit_dashboard: 監視 DB を可視化する UI

セットアップ手順（ローカルで実行する場合）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境
   - Python 3.10 以降を推奨（型演算子 | を使用しているため）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数 / .env
   - 設定は環境変数またはプロジェクトルートの .env / .env.local で行います。
   - 自動ロード: config モジュールは .git または pyproject.toml を基準にプロジェクトルートを特定し、.env/.env.local を自動で読み込みます（ただし OS 環境変数が優先されます）。
   - 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な必須変数（例）
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
     - KABU_API_PASSWORD — 必須（kabuステーション API）
     - OPENAI_API_KEY — ニュース NLP / レジーム判定を使う場合必須
     - KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
   - その他の設定は「主要環境変数」セクション参照。

注意:
- Paper Trading（KABUSYS_ENV=paper_trading）では専用の SQLite DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。Execution 起動スクリプト内に明記されています。
- Monitoring は環境（KABUSYS_ENV）にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。

使い方（代表的なコマンド）
- 実行エンジン（Execution Engine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使い data/paper_trading.db に記録します。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring DB を読み取り専用で開き、Positions/Orders/System/Overview を表示
- AI 機能（プログラムから）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - どちらも DuckDB 接続と target_date を渡して実行します（API キーは引数または環境変数 OPENAI_API_KEY）。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (存在)
    - broker_factory.py
    - broker_api.py
    - ...（発注関連）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — OpenAI によるニュースセンチメント
    - regime_detector.py      — レジームスコア算出と DB 書き込み
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py     — psutil を用いた優先度 / CPU affinity 設定
  - data/                    — デフォルト DB 等（git 管理外想定）
    - kabusys.duckdb (default path: data/kabusys.duckdb)
    - monitoring.db (default path: data/monitoring.db)
    - paper_trading.db (default for paper trading)
  - その他多数の補助モジュール（order_record, order_repository など）

主要環境変数（簡易一覧）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
- PAPER_FILL_MODE: paper trading の fill 挙動（instant | partial | never | reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID 書き込みファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）で通知する場合に必要

備考 / 運用上の注意
- 自動で .env/.env.local を読み込む仕組みがありますが、OS 環境変数が優先されます。.env.example がある場合はそれを参考に .env を用意してください。
- Monitoring の DB 初期化（テーブル作成・マイグレーション）は init_monitoring_db() によって冪等に行われます。run_monitoring/run_execution の起動時に自動実行されています。
- OpenAI を使う処理は外部 API 呼び出しのため、API 利用料金・レート制限に注意してください。score_news / score_regime はリトライやフェイルセーフの仕組みを備えていますが、API キー管理は厳重に。
- process priority / CPU affinity の設定は psutil の権限に依存します。権限不足時には警告が出てスキップされます。
- Paper trading は本番 DB と完全に分離することを意図しています。設定を確認して誤って本番 DB を上書きしないよう注意してください。

必要に応じて README に追記できる内容
- requirements.txt の明示
- .env.example のサンプル
- 実際の ExecutionEngine の CLI フラグや設定項目（EngineConfig 等）
- CI / テストの実行方法、カバレッジ基準

---

上記はこのコードベースの主要点をまとめた README です。必要なら README.md のテンプレート化（.env.example サンプル、requirements.txt など）や、各モジュールの使い方をコマンドやコード例付きでさらに詳細に追記しますか？