KabuSys — 日本株自動売買システム
=============================

本ドキュメントはサンプルコードベース（src/kabusys）向けのREADMEです。システムの目的、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。主要な機能は以下の通りです。

- 注文作成・送信・状態管理（ExecutionEngine、OrderManager、OrderRepository 等）
- 監視・アラート（SystemMonitor、TradeMonitor、RiskMonitor、AlertManager）
- ポートフォリオ構築・ポジションサイズ計算（portfolio パッケージ）
- ファクター計算・リサーチ（research パッケージ）
- ニュースの NLP スコアリング / レジーム判定（AI モジュール: news_nlp, regime_detector）
- Paper Trading 向け検証ツール（tools.paper_verification_report）
- 監視ダッシュボード（Streamlit 実装）

主な設計方針：
- DB（SQLite / DuckDB）を使用した履歴管理・分析
- 設定は環境変数（.env/.env.local サポート）で管理（kabusys.config）
- Paper trading と本番データは分離可能
- 外部 API（kabuステーション、OpenAI など）は抽象化して呼び出す

機能一覧
--------
- Execution
  - 起動スクリプト: python -m kabusys.run_execution
  - Broker クライアントファクトリにより本番/紙トレード（mock）を切替
  - Reconciler による起動時の注文/ポジション同期
  - RiskManager による発注前リスクチェック
- Monitoring
  - 起動スクリプト: python -m kabusys.run_monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、kill flag 発行
  - AlertManager: LINE Push による通知（設定されていれば）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- AI
  - news_nlp.score_news: OpenAI を用いたニュースセンチメント集約と ai_scores 書込
  - regime_detector.score_regime: MA200 とマクロニュースで市場レジーム判定
- Research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - feature_exploration: 将来リターン計算、IC（Spearman）等
- Portfolio
  - 候補選定、重み計算、セクター制限適用、ポジションサイズ計算
- Tools
  - paper_verification_report: Paper Trading 実行結果の期間レポート（コマンドライン）

セットアップ手順
----------------

1. ソースを取得
   - git clone ... （リポジトリによる）

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必要な主要ライブラリ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （パッケージ管理ファイルがある場合は pip install -r requirements.txt または pip install -e . を利用してください）

4. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（kabusys.config が実装）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （AI 機能を使う場合は必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用、未設定なら通知は行われません）
     - PID_FILE_PATH / KILL_FLAG_PATH（デフォルト: data/execution.pid、data/kill.flag）

   - 例 .env:
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=paper_trading

5. データディレクトリ
   - デフォルトで data/ 以下にファイルが置かれます（例: data/kabusys.duckdb, data/monitoring.db）。
   - 監視 DB（SQLite）や paper_trading DB は実行時にテーブルが自動作成されます（init_monitoring_db）。

使い方
------

1. ExecutionEngine の起動
   - 本番または paper_trading 環境を指定して実行します。
   - 簡単なコマンド:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に保存（本番 DB と分離）。
     - 起動時にプロセス優先度を High にしようとします（権限がない場合は警告が出ます）。

2. Monitoring の起動（ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
   - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します（KABUSYS_ENV に関わらず）。

3. Streamlit ダッシュボード
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で接続し、Overview/Positions/Orders/System タブで各種情報を確認できます。

4. Paper Trading 検証レポート
   - 使用方法:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - 出力内容: システム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）など。基準値を満たすか PASS/FAIL 判定を行います。

5. AI 機能（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を与え、指定日に対するニュースのセンチメントを ai_scores テーブルに書き込みます。
     - api_key が None の場合 OPENAI_API_KEY 環境変数を参照します（未設定だと例外）。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF 1321 の MA200 とマクロニュースを組み合わせて market_regime に書き込みます。
   - 注意:
     - OpenAI API 呼び出しに対してはリトライ/フォールバックロジックが実装されていますが、API キーは必須です。

設定・挙動に関するポイント
--------------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）が特定できる場合、起動時に .env と .env.local を自動ロードします。
  - OS 環境変数は保護され、.env.local は上書き許可（override）されます。
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- KABUSYS_ENV:
  - 有効値: development, paper_trading, live
  - paper_trading の場合、Execution は paper_sqlite_path を使いブローカーは MockBrokerClient になります。
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を設定（秒）。0 以下や不正値は無視されデフォルト 60 秒に戻ります。
- PID / kill flag:
  - ExecutionEngine は pid_file を作成することが想定されています。Monitoring は pid_file の存在／生存チェックを行い stale PID を検出して削除します。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止のトリガーを送る設計です（KillSwitch.clear() で削除可能）。
- プロセス優先度・CPU affinity:
  - 起動スクリプトは set_process_priority("high") を最初に試みます。権限がない場合は警告を出して続行します。

よくあるトラブルシューティング
----------------------------
- psutil.AccessDenied（プロセス優先度や CPU affinity の設定失敗）
  - 管理者権限が必要な場合があります。権限なしでも動作は継続します（警告ログ）。
- OpenAI エラー／API キー未設定
  - AI 機能を使うには OPENAI_API_KEY を設定してください。API のエラーはリトライ／フォールバック処理がありますが、キー未設定は例外になります。
- SQLite / DuckDB ファイルが見つからない
  - monitoring の DB は init_monitoring_db により必要テーブルを作成しますが、ファイルパスが正しいか確認してください。report ツールは DB が存在しないとエラー表示します。
- MONITOR_POLL_INTERVAL の設定が反映されない／不正値
  - 整数かつ 1 以上を与えてください。不正値はデフォルト 60 秒にフォールバックします。

主要ディレクトリ構成
--------------------
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py  (パッケージ定義、__version__)
  - config.py  (環境変数 / .env 自動ロード、Settings クラス)
  - run_execution.py  (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

- src/kabusys/monitoring/
  - monitoring_db.py  (SQLite スキーマ定義 / MonitoringDB)
  - monitoring_engine.py (複数 Monitor の束ね)
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py

- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (DB 層: orders)
  - execution_engine.py  (Engine 本体)  ※（コード断片では一部）
  - broker_factory.py / broker_api.py など（ブローカー抽象化）

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - process_priority.py

補足（開発者向け）
-----------------
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成し、既存テーブルへカラム追加の簡易マイグレーションも含みます。
- ログ: 各スクリプトは logging.basicConfig(level=logging.INFO) で起動します。LOG_LEVEL 環境変数で Settings.log_level を管理できます（値は DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- テスト: 多くの関数は純粋関数（副作用なし）で実装されており、単体テストが容易です。OpenAI 呼び出しなどは内部関数をモックできるように設計されています（例: _call_openai_api を patch）。

ライセンス・貢献
----------------
- （ここにプロジェクトのライセンス情報、貢献方法、連絡先などを追記してください）

以上。必要に応じて README にサンプル .env や requirements.txt、実行例スクリプト（systemd unit, docker-compose 等）を追加すると運用が楽になります。