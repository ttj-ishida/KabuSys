KabuSys — 日本株自動売買システム
================================

このリポジトリは、銘柄選定・ポジションサイズ算出、発注エンジン、監視および検証ツールを含む日本株自動売買システムのコア実装です。各モジュールはできるだけ副作用を避け、テスト容易性・再現性を重視して設計されています。

要点
- Python パッケージ名: kabusys
- DB: DuckDB（マーケットデータ等）と SQLite（監視・発注ログ）
- 外部 API: kabuステーション（注文） / J-Quants（データ） / OpenAI（ニュース NLP）
- 実行モード: development / paper_trading / live

機能一覧
- ポートフォリオ構築
  - 候補選定（score / rank）
  - ウェイト計算（等金額・スコア加重）
  - ポジションサイズ計算（リスクベース、上限、単元丸め）
  - セクター集中制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ
- 実行（Execution）
  - Broker クライアント抽象化（本番 / モックの切替）
  - OrderManager（状態遷移・DB 永続化）
  - Reconciler（起動時リコンシリエーション）
  - RiskManager（発注前リスクチェック）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度監視
  - TradeMonitor: 滞留注文 / 約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出とリスクログ
  - KillSwitch: フラグファイルによる ExecutionEngine 停止指示
  - AlertManager: LINE PUSH による通知（クールダウンあり）
  - Streamlit ダッシュボード（監視用）
  - 監視 DB の初期化・マイグレーション機能
- AI / NLP
  - ニュースセンチメント集計（OpenAI を用いた銘柄別スコア化）
  - 市場レジーム判定（ETF とマクロニュースの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（trade logs などを集計）

セットアップ手順（ローカル実行向け）
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は少なくとも以下をインストールしてください）
   - pip install duckdb psutil requests openai streamlit

4. データディレクトリ作成（任意）
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートの .env / .env.local（自動ロードされます）か、OS 環境変数で設定してください。
   - 自動ロードを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境（development / paper_trading / live） デフォルト: development
  - paper_trading: MockBroker を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
- JQUANTS_REFRESH_TOKEN: J-Quants のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60） — run_monitoring で使われます
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（代表コマンド）
- 監視ループ（SystemMonitor の単体起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、paper DB に記録されます。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、最新の監視情報を表示します。

- AI / レジーム・ニューススコアリング（ライブラリ関数の利用例）
  - OpenAI API キーを設定した上で、Python インタプリタやスクリプトから呼び出します（直接の CLI は提供していません）。
  - 例（簡易）:
    - python -c "import duckdb, datetime; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1)))"

重要な挙動・注意点
- run_monitoring は Settings.env に依らず「監視用 SQLite は本番の SQLITE_PATH を使う」設計になっています（監視は常に本番 DB を監視する前提）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って DB を分離します（本番 DB と完全分離）。
- process priority の設定: 起動時に set_process_priority("high") を試みます。権限不足などで失敗してもログを出して続行します。
- .env ファイルのパースは多くのシェルスタイルをサポート（export あり・引用符あり・コメント処理など）。OS 環境変数が優先され、.env.local は .env を上書きします。
- KillSwitch は data/kill.flag 書き込みで ExecutionEngine に停止指示を出します。存在を検知すると ExecutionEngine 側で停止処理を行う想定です。
- MonitoringDB（SQLite）は init_monitoring_db() でスキーマ作成・最低限のマイグレーション（カラム追加）を行います。初回起動で自動生成されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py  (パッケージ定義、__version__)
  - config.py    (Settings: 環境変数読み込み・バリデーション・デフォルト)
  - run_monitoring.py  (SystemMonitor のポーリングループエントリ)
  - run_execution.py   (ExecutionEngine の起動エントリ)
  - tools/
    - paper_verification_report.py  (paper_trading の検証レポート生成)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py         (ニュース NLP スコアリング)
    - regime_detector.py  (市場レジーム判定)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (他: broker_factory, execution_engine, order_repository など 想定)
  - utils/
    - process_priority.py

開発・運用時のヒント
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして自動的な .env のロードを抑制できます。
- DuckDB と prices_daily / raw_financials テーブルは research モジュールの入力です。これらが正しく入っていることを確認してください（テスト用データを用意）。
- OpenAI を使う機能は API 呼び出しを行うため、API キーの設定とネットワーク接続が必要です。呼び出しは冪等性やリトライ（指数バックオフ）を実装していますが、失敗時はフォールバックやスキップ処理があります。
- streamlit ダッシュボードは SQLite を読み取り専用で開きます。MonitoringEngine を起動してデータが入っていることを確認してください。

ライセンス・貢献
- README の末尾にライセンス情報や貢献ガイド（CONTRIBUTING.md）を置くことをおすすめします（本リポジトリには含まれていないため、必要に応じて追加してください）。

問題があれば、どの部分を詳しくドキュメント化したいか（例: 環境変数一覧を詳細に、各モジュールの API 仕様、実行例など）を教えてください。必要に応じてサンプル .env.example や起動スクリプトのユースケースも作成します。