KabuSys — 日本株自動売買システム
=================

概要
----
KabuSys は日本株向けの自動売買／研究基盤です。戦略（ファクター計算・ポートフォリオ構築）、注文実行エンジン、監視・アラート、Paper Trading 向け検証ツール、そしてニュース系の NLP（OpenAI を利用）などを含みます。設計方針として「本番 DB と Paper Trading の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API 失敗時は継続）」を重視しています。

主な特徴（機能一覧）
-----------------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて本番 / ペーパートレードを切替
  - BrokerClientFactory によるブローカ抽象化
  - RiskManager / OrderManager / Reconciler 等を組み合わせて注文実行
- 監視プロセス（run_monitoring）
  - システム状態（CPU/メモリ/ディスク）・データ鮮度・プロセス生存などのポーリング
  - Kill Switch（条件により data/kill.flag を書き込み ExecutionEngine を停止）
  - 各種モニタ・アラート統合（MonitoringEngine）
- 監視用永続化（SQLite）
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard を管理
  - 起動時にスキーマ作成・簡易マイグレーションを実行
- Research / データ処理（DuckDB）
  - ファクター計算（momentum / value / volatility など）
  - 将来リターン・IC 計算、統計サマリ（pandas に依存せず実装）
- Portfolio 構成ロジック（純粋関数）
  - 候補選定、スコア重み／等金額、単元株丸め、セクター上限、レジーム乗数
- AI（OpenAI）連携
  - news_nlp: ニュース記事の銘柄別センチメントを LLM で評価し ai_scores に書き込み
  - regime_detector: ETF（1321）MA + マクロニュースで市場レジーム判定
  - LLM 呼び出しはリトライ/バックオフ・レスポンスバリデーションを実装
- コマンドラインユーティリティ
  - .env を対話生成する config_setup.py
  - 設定を検証する validate_config.py
  - Paper Trading の検証レポートを生成する tools/paper_verification_report.py

セットアップ手順
----------------
必須前提
- Python 3.10 以上（型注釈や最新ライブラリを想定）
- システムに duckdb, psutil, openai 等がインストール可能であること

1. リポジトリを取得
   - git clone ...（またはソースを展開）

2. 依存関係をインストール
   - requirements.txt / pyproject.toml がある場合はそれに従ってください。例:
     - pip install -r requirements.txt
     - あるいは、プロジェクトを編集可能インストール:
       pip install -e .

   主要依存（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）

3. データ / ログディレクトリ作成（手動で準備しても自動作成されます）
   - data/ — SQLite DB / PID / kill.flag / stop_requested.flag を配置
   - logs/ — 日次ローテーションログがここに保存されます

4. 環境変数（.env）を準備
   - 対話式ウィザードで作成可能（下記参照）
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を設定

.env の作成（対話式）
- python -m kabusys.config_setup
  - .env を対話式で作成/更新します
  - 生成後は python -m kabusys.validate_config で検証してください

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant, partial, never, reject）

使い方（実行例）
----------------

1) 設定の作成 / 検証
- .env 作成:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いで exit(1)

2) 監視プロセス起動
- 環境変数で間隔を変更可能:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- run_monitoring は data/stop_requested.flag の存在をチェックし、あればループを終了します。
- 監視は常に「本番用の sqlite_path」を使用（KABUSYS_ENV に依存しない）。

3) 実行エンジン起動
- 本番 / Paper 切替は KABUSYS_ENV による:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading 時は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録します。
- 起動時、data/stop_requested.flag が既に存在する場合は起動をスキップします。
- 停止は data/stop_requested.flag を作成するか kill.flag により制御されます。

4) Paper Trading 検証レポート
- DB が存在する状態で:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db（--db で上書き可）

5) AI / Research 機能の利用（Python API）
- DuckDB 接続を作り、モジュール関数を呼ぶ例:
  import duckdb
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026, 4, 11))

- ニュース NLP（OpenAI 必須）を呼ぶ例:
  from kabusys.ai import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 11), api_key="sk-...")

ログ・ファイル配置
------------------
- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - run_execution は app_name="execution"
  - run_monitoring は app_name="monitoring"
- SQLite / DuckDB:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - SQLite(監視): data/monitoring.db（デフォルト）
  - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID デフォルト）
  - data/stop_requested.flag（手動でプロセス停止リクエストを通知する旗）
  - data/kill.flag（Kill Switch により自動作成される停止フラグ。Settings.kill_flag_path から参照）

停止・Kill Switch の仕組み
------------------------
- Monitoring が RiskMonitor 等の結果を評価し、条件（例: ドローダウン閾値超過、ポジション上限超過）に該当すると KillSwitch が data/kill.flag を書き込みます。
- ExecutionEngine は起動時 / 実行中に kill.flag や stop_requested.flag を見て安全に停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0（クリアしない）を推奨します。

データベース・スキーマ
--------------------
- monitoring_db.init_monitoring_db() が必要なテーブルを作成します（冪等）。
  - system_status, trade_logs, positions, risk_logs, dashboard
- マイグレーション: 起動時に不足カラム（例: peak_value, latency_ms）があれば追加します。

ディレクトリ構成（主要ファイル）
----------------------------
以下は主要モジュールとその目的の抜粋です。プロジェクトルートはパッケージ配布後も .env 自動ロード等で正しく検出されます。

- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — Settings クラス（環境変数取り扱い・自動 .env ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py        — システム状態・データ鮮度チェック
    - risk_monitor.py          — ドローダウン監視等
    - trade_monitor.py         — （発注ログ監視等; ファイル内の実装参照）
    - monitoring_engine.py     — Monitor を束ねる実行ループ
    - kill_switch.py           — kill.flag 編集ロジック
    - alert_manager.py         — （LINE などで通知する責務; 実装参照）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py               — ニュースセンチメント評価（OpenAI）
    - regime_detector.py        — 市場レジーム判定（OpenAI + ETF 指標）
    - __init__.py
  - data/                      — （ランタイムで使用する DB / PID / flag を配置）
  - logs/                      — ログ出力先（デフォルト）

開発者向けメモ
--------------
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テスト時など自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LLM の呼び出し箇所はリトライ・バックオフ・レスポンスバリデーションを含みます。ユニットテストでは _call_openai_api 等をモックすることを想定しています。
- DuckDB / SQLite への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）を明示的に扱う箇所があります。部分失敗時のデータ保護に注意してください。

よくある質問（FAQ）
------------------
- Q: Paper Trading と本番の DB は分離されていますか？
  A: はい。KABUSYS_ENV=paper_trading 時は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視（monitoring）は常に本番の sqlite_path を使用します。

- Q: 監視のポーリング間隔を変更したい
  A: 環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます。デフォルトは 60 秒。0 以下や不正値は無視されデフォルトにフォールバックします。

- Q: OpenAI の API キーはどこで設定しますか？
  A: 環境変数 OPENAI_API_KEY（もしくは ai 関数の api_key 引数）を使用してください。

ライセンス / 貢献
-----------------
- 本 README に記載の通り、.env は機密情報を含むため絶対に Git にコミットしないでください。
- 貢献は Pull Request を通じて行ってください（詳細はリポジトリの CONTRIBUTING.md を参照してください（存在する場合））。

補足
----
この README はリポジトリ内のモジュール設計・スクリプトを元にまとめた概要ドキュメントです。詳細実装や追加設定（例えば LINE 通知の設定やブローカ実装の切替）は該当モジュール内の docstring を参照してください。もし特定の使い方（例: AI モジュールの実行例、ExecutionEngine の設定項目解説）をより詳しく知りたい場合は、その点を指定して質問してください。