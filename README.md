KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究基盤です。  
主な目的は以下です。

- 売買シグナル生成・ポートフォリオ構築・発注ロジック（ExecutionEngine）
- 実行・監視のためのモニタリング（System / Trade / Risk）
- リサーチ用ファクター計算・特徴量解析（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- ペーパートレード向けの分離 DB、検証レポート生成ツール

機能一覧
--------
- 設定管理
  - .env 自動読込（プロジェクトルートの .env / .env.local）
  - 対話式環境設定ウィザード（kabusys.config_setup）
  - 起動前チェックツール（kabusys.validate_config）
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用して paper_trading DB に記録
  - Monitoring ポーリング（run_monitoring.py）
    - System / Trade / Risk の各モニタを定期実行しアラート・Kill Switch 評価を行う
- 監視・ログ永続化
  - SQLite ベースの monitoring DB（init_monitoring_db がスキーマを作成）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル
- ポートフォリオ構築（純関数）
  - 候補選定、等比率／スコア加重配分、ポジションサイズ算出、セクター上限、レジーム乗数など
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI（OpenAI）連携
  - ニュース記事を集約して銘柄ごとのセンチメントスコアを ai_scores に書き込む（news_nlp）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（regime_detector）
  - API 呼び出しは堅牢にリトライ処理・バリデーションを実装
- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Linux / macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - 主な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 内容チェックを行う場合、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成するのが簡単です:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考にしてください）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. DB ディレクトリ/ファイルの準備
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

主要な環境変数
---------------
（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API 用パスワード

（推奨 / 任意）
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH           : duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 本番通知用（任意）
- OPENAI_API_KEY        : OpenAI API キー（AI モジュールを利用する場合必須）

その他（モニタリング制御）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : 本番で kill.flag 自動クリアを許可するか（0/1、デフォルト 0）

使い方
------
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作: KABUSYS_ENV によって paper_trading モードでは専用 DB を使う（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了する
  - 実行中は data/execution.pid に PID を書きます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 動作: SystemMonitor.check_once() を指定間隔で呼び出す
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するとループが終了します

- 設定ウィザード / 検証
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI / Research のプログラム的利用（例）
  - ニューススコア化:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    results = calc_momentum(duckdb_conn, date(2026,4,1))
  - ポートフォリオ関数:
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

監視 DB スキーマ（自動作成）
--------------------------
init_monitoring_db(conn) により作成されるテーブル（主なカラム）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id (常に 1), updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity

- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py       — （trade_monitor 実装あり）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （アラート送信ロジック）

- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

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

- monitoring_db / data / logs:
  - data/ (stop_requested.flag, execution.pid, kill.flag 等)
  - logs/ (日次ローテーションされたログファイル)

注意事項 / 運用上のメモ
--------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知等の設定を確認してください。
- kill.flag / stop_requested.flag による停止機構があります。運用時は誤ってフラグを動かさないよう注意してください。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）とコスト管理が必要です。API 呼び出しはリトライ処理を行いますが、失敗時はフェイルセーフで続行します（デフォルトはスコア 0.0 など）。
- PyYAML がない場合、validate_config は YAML の中身検証をスキップします（警告）。

貢献 / 開発
------------
- 新しい機能を追加する場合はユニットテスト・DuckDB のクエリ検証を行ってください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- ログは logs/ 配下に日次ローテーションで保存されます。ディスク容量に注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で確認できます（現状 0.1.0）。

以上が主要な README 内容です。追加で具体的なコマンド例、requirements.txt、デプロイ／systemd ユニット例などが必要であれば教えてください。