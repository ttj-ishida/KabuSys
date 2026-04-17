# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。戦略の研究・ファクター計算、ポートフォリオ構築、発注実行、監視・アラート、AI を用いたニュースセンチメント評価などのコンポーネントを含みます。  
このリポジトリは主にライブラリ / 実行スクリプト群を提供し、実運用および検証（Paper Trading）に対応しています。

主な特徴
- DuckDB と SQLite を用いた時系列・メタデータ処理
- ファクター（モメンタム / バリュー / ボラティリティ）計算モジュール（research）
- ポートフォリオ構築（候補選別、重み付け、ポジションサイズ計算）
- Execution エンジン周辺ユーティリティ（OrderManager、Reconciler 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE push）
- AI（OpenAI）を使ったニュースセンチメント評価 / レジーム判定
- Paper Trading 向けの専用 DB 分離と検証レポート生成ツール
- streamlit ベースの監視ダッシュボード

以下に、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

----------------------------------------
プロジェクト概要
----------------------------------------
KabuSys は取引ロジックそのもの（戦略モデル）のほかに、以下の運用周辺機能を提供します。
- データ基盤向けのファクター計算（DuckDB）
- ポートフォリオ構築パイプライン（候補選定・重み付け・単元丸め）
- 実行周り（Order 管理、ブローカークライアントの抽象化、再起動時リコンシリエーション）
- 監視（CPU / メモリ / ディスク、データ鮮度、滞留注文や約定異常）
- アラート（LINE Messaging API）
- AI モジュール：ニュース NLP（OpenAI）で銘柄ごとのスコアを計算、market regime 判定
- 開発 / 検証用ツール（paper trading レポート、streamlit ダッシュボード）

----------------------------------------
機能一覧
----------------------------------------
- config: .env 自動読み込み（.env / .env.local）、環境変数管理（Settings クラス）
- utils: プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
- research: ファクター計算（momentum/value/volatility）、特徴量解析（IC、forward returns 等）
- portfolio: 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- execution: OrderManager、OrderRepository、Reconciler、RiskManager、BrokerFactory（ブローカー抽象）
- monitoring: MonitoringDB（SQLite テーブル定義 / マイグレーション）、System/Trade/Risk Monitor、KillSwitch、AlertManager（LINE）
- ai: news_nlp（OpenAI でニュースをスコアリング）、regime_detector（マクロ + MA200 によるレジーム判定）
- tools:
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: streamlit による監視ダッシュボード
- 実行スクリプト:
  - run_execution.py: ExecutionEngine を起動（paper_trading 環境時は MockBroker を使用し専用 DB に記録）
  - run_monitoring.py: SystemMonitor をポーリングで実行（MONITOR_POLL_INTERVAL により間隔調整可能）

----------------------------------------
セットアップ手順
----------------------------------------
前提:
- Python 3.10+（typing / match 等の利用状況により環境を合わせてください）
- システムに DuckDB, psutil などのネイティブ依存が入る場合があります

1. リポジトリをクローン / ソースを用意
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（必要なパッケージの例）
   - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください
4. 設定（環境変数 / .env）
   - プロジェクトルートに .env または .env.local を配置することで自動読み込みされます（デフォルト）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=your_jquants_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=development   # development | paper_trading | live
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
5. データディレクトリの作成（例）
   - mkdir -p data
   - touch data/.keep  （必要に応じて）
6. 初回 DB 初期化は各スクリプトが起動時に実行します（init_monitoring_db が呼ばれます）

注意:
- Paper Trading 環境では SQLite データベースが分離されます（paper_trading の場合は Settings.paper_sqlite_path を使用）。
- Settings は .env の自動読み込みを行いますが、テスト時などで無効化可能です（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

----------------------------------------
使い方（主要な起動 / ツール）
----------------------------------------
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）。
    - プロセス優先度を "high" に変更しようとします（psutil により失敗した場合は警告）。
    - data/stop_requested.flag が存在すると起動を中止または停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）
    - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依らず本番監視用 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）でループを終了できます。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などのサマリと PASS/FAIL 判定

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します

- AI モジュール（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news から記事を取得し OpenAI で銘柄ごとのスコアを ai_scores テーブルへ書き込む
    - OPENAI_API_KEY が必要（api_key 引数で渡すことも可）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 1321（ETF）の MA200 とマクロニュースの LLM センチメントを合成して market_regime を更新

- 設定の注意点
  - KABUSYS_ENV: development | paper_trading | live（Settings.env）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動を制御）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（整数、1 以上）
  - kill.flag（Settings.kill_flag_path）: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを与える（ファイルを置くことで停止を指示）

----------------------------------------
データファイル / フラグ
----------------------------------------
- data/monitoring.db: デフォルトの監視 SQLite DB（Settings.sqlite_path）
- data/kabusys.duckdb: DuckDB のメイン DB（Settings.duckdb_path）
- data/paper_trading.db: Paper Trading 用 SQLite（Settings.paper_sqlite_path）
- data/execution.pid: ExecutionEngine の PID（Settings.pid_file_path）
- data/stop_requested.flag: 手動停止フラグ（存在すると run_* スクリプトは停止 / 起動中断）
- data/kill.flag: KillSwitch が書き込み、ExecutionEngine に強制停止シグナルを送る

----------------------------------------
ディレクトリ構成（主要ファイルの説明）
----------------------------------------
src/kabusys/
- __init__.py
  - パッケージバージョン等
- config.py
  - Settings クラス（環境変数 / .env ロード・検証）
- utils/
  - process_priority.py: psutil を使った優先度/affinity 設定
- research/
  - factor_research.py: calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算）
  - feature_exploration.py: forward returns, IC, factor summary 等の統計ユーティリティ
- portfolio/
  - portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights
  - position_sizing.py: calc_position_sizes（単元丸め、aggregate cap）
  - risk_adjustment.py: apply_sector_cap, calc_regime_multiplier
- ai/
  - news_nlp.py: raw_news を OpenAI に投げて ai_scores を書き込むロジック
  - regime_detector.py: MA200 + マクロニュースで market_regime を判定・書込み
- monitoring/
  - monitoring_db.py: SQLite schema / MonitoringDB（ログ書込みユーティリティ・マイグレーション）
  - system_monitor.py: CPU/メモリ/ディスク、データ鮮度、PID チェック
  - trade_monitor.py: 滞留注文・約定異常の検出
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: kill.flag の書き込み / 管理
  - alert_manager.py: LINE Push を用いた通知
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py: streamlit ベースの監視 UI
- execution/
  - order_manager.py: Order の生成 / 管理（Order state machine 入口）
  - reconciler.py: 再起動時に注文・ポジションをブローカーと突合
  - （その他: broker_factory / execution_engine / order_repository 等 — 実行周りのコア）
- tools/
  - paper_verification_report.py: Paper Trading DB の検証レポート生成ツール
- monitoring/run_monitoring.py: SystemMonitor ポーリング起動スクリプト
- run_execution.py: ExecutionEngine 起動スクリプト（トップレベルからも実行可能）

----------------------------------------
運用上の注意 / ベストプラクティス
----------------------------------------
- 環境（KABUSYS_ENV）は本番/live と paper_trading を明確に分離すること。Paper Trading は専用 DB に記録され、本番 DB を汚しません。
- OpenAI API を呼ぶモジュール（news_nlp, regime_detector）は API キーとレート制限対策が必要です。環境変数 OPENAI_API_KEY を設定してください。
- プロセス優先度や CPU affinity の設定は psutil に依存し、権限不足で失敗する場合があります（警告ログのみ）。
- kill.flag / stop_requested.flag / PID ファイル等のフラグファイルは、運用スクリプトが存在チェック・削除を行います。運用手順書に明記して慎重に扱ってください。
- MonitoringDB のスキーマは init_monitoring_db() により冪等で作成・マイグレーションされます。バックアップを定期的に取得してください。
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news 等）は研究・ファクター計算の入力となります。データの更新タイミング（データ鮮度）が重要です（SystemMonitor はそれをチェックします）。

----------------------------------------
貢献 / 変更履歴
----------------------------------------
- 現在のバージョンは __version__ = "0.1.0"
- 新しい機能追加やバグ修正は各モジュールの責務を分けた上で PR をお願いします。

----------------------------------------
問い合わせ / ライセンス
----------------------------------------
- この README はコードベースから生成されたドキュメントです。実際の運用時は pyproject.toml / LICENSE / CONTRIBUTING を参照してください。

以上。必要に応じて、README にサンプル .env テンプレートや起動スクリプトの systemd / supervisord サンプル、依存パッケージの正確なバージョンリストを追加できます。希望があれば追記します。