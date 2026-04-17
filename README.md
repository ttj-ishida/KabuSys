# KabuSys

KabuSys は日本株向けの自動売買・研究・監視フレームワークです。本リポジトリは発注エンジン、監視基盤、ポートフォリオ構築ユーティリティ、ファクター計算、ニュース NLP / レジーム判定などのモジュールで構成されています。

- バージョン: 0.1.0
- 主な言語: Python

以下はコードベースの概要、機能、セットアップ方法、基本的な使い方、ディレクトリ構成の説明です。

プロジェクト概要
- 日本株自動売買システムのコアライブラリ。
- 実運用（live）・ペーパー取引（paper_trading）・開発（development）という複数の起動モードをサポート。
- 発注（ExecutionEngine）と監視（MonitoringEngine）を分離し、監視側は本番監視 DB を使用する設計。
- DuckDB を用いた時系列・ファイナンスデータ処理、SQLite を用いた監視/注文ログ保存。
- OpenAI API を使ったニュースセンチメント評価やマクロセンチメントを用いた市場レジーム判定機能を持つ。

主な機能一覧
- Execution（発注）
  - ExecutionEngine の起動スクリプト（run_execution.py）。
  - Broker クライアントを切り替え（live / paper_trading）。paper_trading 時は MockBroker を用い、paper 用 DB（data/paper_trading.db）に記録。
  - OrderManager / OrderRepository / Reconciler による注文ライフサイクル管理と起動時リコンシリエーション。
  - RiskManager による注文レート制御やドローダウン等のリスク管理（設定で制御）。
- Monitoring（監視）
  - SystemMonitor: CPU、メモリ、ディスク、プロセス状態、データ鮮度を定期チェック。
  - TradeMonitor: 滞留注文、約定価格の異常などを検出。
  - RiskMonitor: ドローダウン・保有数上限の監視、ダッシュボード更新。
  - KillSwitch: 指定条件で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送出。
  - AlertManager: LINE Messaging API 経由で監視アラートを送信（クールダウン管理あり）。
  - Streamlit ベースの監視ダッシュボード（簡易 UI）。
- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）、重み計算（等ウェイト／スコア加重）、セクター制約適用、ポジションサイズ計算（単元丸め・リスクベース計算）など。
- Research（研究）
  - DuckDB の prices_daily / raw_financials を参照してファクター（Momentum / Volatility / Value）を計算。
  - 将来リターン、IC（Information Coefficient）、ファクター統計量計算。
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメントの集約スコア化（ai_scores テーブルへ書込）。
  - ETF（1321）とマクロニュースの合成による日次レジーム判定（market_regime テーブルへ書込）。
- Tools
  - paper_verification_report: Paper Trading 用の検証レポート生成スクリプト（稼働率、注文成功率、レイテンシ等を評価）。
- ユーティリティ
  - Settings: 環境変数 / .env ファイルの読み込み、設定値取得。
  - process_priority: Windows / POSIX に対応したプロセス優先度・CPU affinity 設定ユーティリティ。
  - MonitoringDB: 監視ログ用の SQLite スキーマ初期化・読み書きラッパー。

セットアップ手順（開発者向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - （本 README に requirements.txt は同梱されていないため、代表的な依存を示します）
   - pip install duckdb psutil openai requests streamlit

   - （プロジェクトに requirements.txt がある場合は）
     - pip install -r requirements.txt

4. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local を上書きとして追加可能）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（主に Settings で参照）
   - 必須（実運用時）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper trading DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト "instant"
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 監視関係:
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）。既定 60 秒。

5. データディレクトリ作成
   - data ディレクトリを作成しておくと便利:
     - mkdir -p data

基本的な使い方 / 起動方法
- ExecutionEngine（発注エンジン）起動
  - 実行:
    - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番/監視用の監視 DB は別に保持されます。
    - 実行開始時に process priority を "high" に設定します。
    - data/stop_requested.flag が存在すると起動・ループを終了します。
    - 実行中は data/execution.pid に PID を書きます（Settings.pid_file_path 経由で変更可）。
    - ExecutionEngine の停止は kill.flag を書く（KillSwitch か手動）か stop flag を立てることで行います。

- Monitoring（監視ループ）起動
  - 実行:
    - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL によりポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - 監視は Settings.sqlite_path（監視 DB）に対して常に本番の sqlite_path を使います（KABUSYS_ENV に依存しない）。
    - SystemMonitor / TradeMonitor / RiskMonitor を使って各種チェックを実施し、MonitoringDB（SQLite）にログを書き込みます。
    - 監視ループは data/stop_requested.flag を検知すると終了します。

- Streamlit ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 監視用 SQLite を読み取り専用で開いて各種メトリクス・テーブルを表示します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 出力:
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の要約と PASS/FAIL 判定を標準出力に出力します。

運用上の注意
- 環境（KABUSYS_ENV）:
  - development / paper_trading / live の3値をサポート。paper_trading は本番 DB と分離されます。
- データベース:
  - DuckDB は時系列データ（prices_daily, raw_financials 等）に使用。
  - 監視用 SQLite（monitoring.db）は init_monitoring_db() により必要なテーブルを作成します。既存 DB に対する簡易マイグレーション（列追加）も行います。
- フラグファイル:
  - data/kill.flag — KillSwitch により ExecutionEngine 側に停止命令を伝えるために書き込まれるファイル。存在すれば Execution 側は停止します（また明示的に消すこともできます）。
  - data/stop_requested.flag — run_* スクリプトのループを外部から終了させるために使われるフラグ（監視や実行スクリプトで参照）。
- OpenAI 関連:
  - AI 機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフェイルセーフを備え、失敗時はスコアをゼロフォールバックする等の設計になっています。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出して CPU 優先度を上げます。権限不足等で失敗しても警告出力して続行します。

ディレクトリ構成（主要ファイルのみ）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - data/                    — 実行時に使用する DB / フラグ（リポジトリルートに配置）
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py     — （実装ファイルの存在を想定）
    - broker_factory.py
    - ...                     — ブローカー API 等
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - monitoring/ (パッケージ化用 __init__.py など)
  - その他モジュール...

補足（開発者向け）
- Settings はプロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込みます（OS 環境変数が優先され、必要に応じて .env.local で上書きできます）。
- DuckDB 接続は研究・AI 周りの計算で SQL を活用するよう設計されています。ファクター計算はメモリ内でリスト化して返す純粋関数群です。
- 各モジュールは可能な限りフェイルセーフに設計されています（API 失敗時はログを残して継続など）。

よく使うコマンドまとめ
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

お問い合わせ / 貢献
- バグや改善提案は issue を立ててください。設計意図や前提条件に関する質問も歓迎します。

以上がこのコードベースのREADME 相当の概要です。README に追記したい実運用の設定例や .env.example を作成したい場合は、テンプレートを作成して差し上げます。必要であればお知らせください。