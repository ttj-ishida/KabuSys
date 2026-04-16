KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の主要モジュール群を含みます。
本 README はコードベースの主要概念、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

要点
-----
- Python製（モジュールは src/kabusys 配下）
- SQLite（監視ログ等）と DuckDB（時系列・分析用）を使用
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）モードを区別
- OpenAI API を利用したニュースセンチメント／レジーム判定機能を搭載（オプション）
- 監視（MonitoringEngine）、実行（ExecutionEngine）、ポートフォリオ構築、研究用ツール等を提供

機能一覧
--------
主要な機能（モジュール）：
- execution
  - ExecutionEngine 起動（run_execution.py）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理（OrderManager / OrderRepository / Reconciler）
  - リスク管理（RiskManager）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（システム稼働・データ鮮度・注文滞留・ドローダウン監視）
  - MonitoringDB（SQLite による永続化）
  - MonitoringEngine（各 Monitor を束ねてポーリング）
  - AlertManager（LINE Push による通知）
  - KillSwitch（停止フラグ生成による ExecutionEngine 停止）
  - Streamlit ダッシュボード（監視情報の可視化）
- ai
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector: ma200 とマクロ記事の LLM センチメントを合成して市場レジームを判定
- portfolio
  - 銘柄選定・重み計算・ポジションサイズ計算・セクター制限などの純粋関数群
- research
  - ファクター計算（momentum, volatility, value）や特徴量解析ユーティリティ
- tools
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

セットアップ手順
----------------

前提
- Python 3.9+（推奨）  
- SQLite（Python 標準に同梱）
- システムレベルでは psutil（プロセス優先度／CPU affinity）に root/管理者権限が必要な場合あり

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例:
     - git clone <repo_url>
     - cd <repo_root>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ（抜粋）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くことで自動読み込みされます（自動読み込みはデフォルトで有効）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（一部）
- KABUSYS_ENV: 起動環境（development, paper_trading, live）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabusapi のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant | partial | never | reject）
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視関連設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（実行例）
----------------

1. 実行エンジン（ExecutionEngine）を起動
   - 本番モード（例）
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   - ペーパートレード（DB を分離）
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 注意:
     - paper_trading の場合、settings.paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離されます。
     - 起動時に data/execution.pid が作成されます。停止は kill.flag/stop flag により制御できます。

2. 監視プロセス（MonitoringEngine）を起動
   - python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL を設定してポーリング間隔を秒単位で変更（例: export MONITOR_POLL_INTERVAL=30）
   - モニタは常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を用いて監視テーブルを記録します。

3. Streamlit ダッシュボード（監視画面）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザで監視データを閲覧できます（read-only 接続）。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで別 DB を指定できます（デフォルト data/paper_trading.db）。

5. AI（ニューススコア / レジーム判定）
   - Python API として呼び出し可能:
     - from kabusys.ai.news_nlp import score_news
       - score_news(conn, target_date, api_key=...)
     - from kabusys.ai.regime_detector import score_regime
       - score_regime(conn, target_date, api_key=...)
   - OpenAI API キー（OPENAI_API_KEY）が必須です。通信エラーや 5xx 時はリトライ/フォールバック処理があります。

停止 / フラグ制御
----------------
- 停止フラグ:
  - data/stop_requested.flag: run_* スクリプトはこのファイルを監視してループを終了します（運用用の外部停止トリガ）。
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る役割を担います（監視の結果に基づく自動停止）。
- 実行中の PID 管理:
  - ExecutionEngine は data/execution.pid（または Settings.pid_file_path）を作成して PID 管理を行います。
  - SystemMonitor は stale PID 検出時に PID ファイルを削除してログ・リスクイベントを記録します。

内部の挙動・設計上の注意
-----------------------
- Settings（kabusys.config）は .env/.env.local の自動読み込みを行います（プロジェクトルート自動検出）。
- Monitoring の init_monitoring_db() は起動時にテーブルと必要なマイグレーションを行います（冪等）。
- Paper Trading は本番 DB と完全に分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する処理は外部 API に依存するため、API失敗時は安全側のフォールバック（スコア 0.0 等）を行う設計となっています。
- process priority / cpu affinity の設定は psutil を使用します。権限不足で失敗する場合は警告ログを出してスキップします。

ディレクトリ構成（主なファイル）
--------------------------------
src/
  kabusys/
    __init__.py                — パッケージ定義（__version__ 等）
    config.py                  — 環境変数 / 設定管理
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py — Paper Trading レポート生成ツール
    ai/
      __init__.py
      news_nlp.py              — ニュース NLP（OpenAI）によるスコアリング
      regime_detector.py       — 市場レジーム判定
    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      execution_engine.py      —（エンジン本体の実装がある想定）
      broker_factory.py
      broker_api.py
      order_record.py
      order_repository.py
    monitoring/
      __init__.py
      monitoring_db.py         — SQLite スキーマ／読み書き層
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      streamlit_dashboard.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    utils/
      process_priority.py
    data/                      — 実行時に使用するデータディレクトリ（例: .pid/.db/.flag）

（実際のリポジトリにはさらに多数の補助モジュールが含まれます。上は代表例です。）

運用上のヒント
----------------
- 開発環境では KABUSYS_ENV=development を使用。ペーパートレードでの安全な動作確認には KABUSYS_ENV=paper_trading を使用してください。
- 監視はデフォルト 60 秒間隔（MONITOR_POLL_INTERVAL で調整可）。短くするとログ増加や API/DB 負荷に注意。
- OpenAI 呼び出しはレート制限・コストが発生するため、本番では適切なキー管理とコスト管理が必要です。
- プロセス優先度の設定（set_process_priority）は OS によっては権限を要するので、実行環境のポリシーを確認してください。
- データ保存先（data/ 以下）とバックアップ方針を事前に決めておくこと（特に本番）。

トラブルシューティング
---------------------
- DB が見つからない / 開けない:
  - path や権限、ファイルロック（同時接続）を確認。Streamlit は read-only URI を使うことを推奨。
- OpenAI 呼び出しでエラーが頻発する:
  - API キー、ネットワーク、レート制限を確認。設定したリトライ回数・バックオフが動作しているかログで確認。
- プロセス優先度設定で例外が出る:
  - psutil の AccessDenied 等。権限を付与するか設定をスキップする（ログに警告が出ます）。

ライセンス / 貢献
-----------------
（リポジトリに LICENSE がある場合はそちらを参照してください）

最後に
------
この README はコードベースの主要な使い方と設計の要点をまとめたものです。詳細な実装や追加の実行オプションは各モジュールの docstring / ソースコメントを参照してください。必要であれば README を拡張して具体的な運用手順・設定例・CI/CD の案内を追加できます。