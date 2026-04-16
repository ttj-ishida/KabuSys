README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株を対象とした自動売買システムのモジュール群です。本リポジトリには以下の主要機能を提供するコンポーネントが含まれます。

- 注文管理と ExecutionEngine（実売買／ペーパートレード両対応）
- 監視（System / Trade / Risk）および監視ログの永続化（SQLite）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ用ファクター計算（DuckDB を利用）
- ニュースの NLP スコアリング（OpenAI 経由）
- レジーム判定（ETF MA + マクロニュースの LLM 評価）
- 監視ダッシュボード（Streamlit）
- 検証ツール（Paper Trading 検証レポート生成 等）

特徴
----
- 環境切替（development / paper_trading / live）により実 DB とペーパートレード DB を分離
- DuckDB を用いた高速な時系列・財務データ解析モジュール（research/*）
- OpenAI を用いたニュースセンチメント評価（ai/news_nlp, ai/regime_detector）
- 監視コンポーネントが system/trade/risk を定期チェックし、LINE へアラート送信可能
- kill.flag / stop_requested.flag による外部からの安全停止制御
- ほとんどの処理は副作用を抑えた純粋関数／明確な DB 層で設計

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 以下は主な依存パッケージ（プロジェクトに requirements.txt があればそちらを利用してください）。
     pip install duckdb psutil requests openai streamlit

   - 追加でテストや開発用の依存がある場合は適宜インストールしてください。

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai 系機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
     - PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject、デフォルト instant）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）※ run_monitoring の場合に使用

5. data ディレクトリの準備
   - 実行前に data/ ディレクトリを作成しておくとよいです（PID / flag の出力先）。
     mkdir -p data

使い方（主要コマンド）
---------------------

※ package がインストールされているか、プロジェクトルートから PYTHONPATH に src を含めて実行してください。
例: PYTHONPATH=src python -m kabusys.run_monitoring

1. 監視ループを起動（SystemMonitor 単体実行）
   - python -m kabusys.run_monitoring
   - 動作:
     - プロセス優先度を "high" に設定（試み）
     - settings から sqlite_path（監視 DB）と duckdb_path を参照して接続
     - Monitoring DB スキーマを init（冪等）
     - SystemMonitor.check_once をポーリング（間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能、デフォルト 60 秒）
     - data/stop_requested.flag が存在するとループを終了

2. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、データは paper_trading.db に分離
     - 各コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立て、ExecutionEngine を起動
     - data/stop_requested.flag を検知すると安全停止
     - data/execution.pid に PID を書き、stale PID の検出・削除ロジックあり

3. 監視ダッシュボード（Streamlit）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で SQLite を開き、Dashboard / Positions / Orders / System 情報を表示

4. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db path/to/paper_trading.db
   - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可能）
   - 出力: 稼働率・注文成功率・送信率・レイテンシ（P95）等の解析と PASS/FAIL 判定

5. AI / リサーチ機能（ライブラリ関数として利用）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - research モジュール:
     - kabusys.research.calc_momentum / calc_volatility / calc_value
     - kabusys.research.calc_forward_returns / calc_ic など
   - これらは DuckDB 接続を受け取り、prices_daily / raw_financials / raw_news 等のテーブルを参照する設計です。

停止・制御フラグ
----------------
- data/stop_requested.flag: run_monitoring / run_execution のポーリングループを終了させるためのフラグ。存在するとプロセスは終了します（各スクリプトが検知）。
- data/kill.flag: KillSwitch により ExecutionEngine に対して停止シグナルを送る用途（監視で DRAWDOWN 等が検出された場合など）。存在すると Execution 側は停止されます。KillSwitch は冪等にファイルを書き込みます。
- data/execution.pid: ExecutionEngine の PID を記録するためのファイル。stale PID の検出・削除ロジックあり。

設定読み込み
-----------
- kabusys.config モジュールは .env / .env.local をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラスから主要設定（パスやフラグ、しきい値）へアクセスできます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要な構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — 実行時に使うファイル群（DB, flags, pid 等）(project root に置く)
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ初期化 + 永続化 API
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 滞留注文・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成・管理
    - alert_manager.py       — LINE 通知
    - monitoring_engine.py   — 各 Monitor をまとめるループ（テスト用/本番用）
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                    — Broker 抽象・エンジン本体など（実装箇所による）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py

補足 / 運用のヒント
------------------
- ペーパートレードと本番環境は DB を分離しています（Settings.paper_sqlite_path を参照）。本番 DB に対して誤って書き込まないよう KABUSYS_ENV の設定に注意してください。
- OpenAI を利用する機能は API 呼び出しに失敗してもフェイルセーフとなるよう設計されていますが、API キーの管理やレートリミット対策（リトライ・バックオフ）は適切に行ってください。
- run_monitoring/run_execution はプロセス優先度を上げる処理を行います。権限が不足する場合は警告ログが出るのみで継続します。
- monitoring_db.init_monitoring_db() は冪等で実行でき、既存 DB に対する簡単なマイグレーション（カラム追加）を行います。

ライセンス・貢献
----------------
- ライセンス情報や貢献方法はリポジトリのトップレベルに LICENSE / CONTRIBUTING 等のファイルがあればそちらを参照してください。

問題・バグ報告
--------------
- 実行時に何らかのエラーや挙動不審があればログを確認してください。監視系は logging を用いて情報を出力します。
- バグ報告や機能要望は issue を立ててください（リポジトリ管理方針に従ってください）。

以上。必要があれば、各モジュールの使い方（API 仕様）、サンプル .env、運用フロー（起動スクリプトの systemd ユニット例 など）を追記します。どの情報を詳細化したいか教えてください。