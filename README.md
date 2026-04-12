README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買および研究用ライブラリ／実行基盤です。  
本リポジトリには取引実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、ファクター計算・リサーチ機能、ニュース NLP / レジーム判定（OpenAI 利用）などが含まれます。

主要な特徴
-----------
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
  - paper_trading モードではモックブローカーを使用し、発注データを本番 DB と分離
- Monitoring（システム状態・注文滞留・リスク監視）
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ダッシュボード
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用モジュール（DuckDB を使ったファクター計算、将来リターン、IC 計算など）
- ニュース NLP（OpenAI を用いた銘柄別センチメント scoring）
- 市場レジーム判定（ETF とマクロニュースを組み合わせて daily 判定）
- 小規模なユーティリティ（プロセス優先度/CPU affinity 設定など）

セットアップ
------------
前提
- Python 3.10+
  - PEP 604 の union 型（|）等を使用しているため 3.10 以上を想定しています。

推奨手順（例）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて開発用パッケージを追加）

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと、自動でロードされます（既存の OS 環境変数は上書きされません）。
   - 自動ロードを無効化したい場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - .env がない場合は .env.example を参考に作成してください（※本リポジトリに .env.example があれば参照）。

主要な環境変数（Settings で定義されているもの）
- 必須系
  - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
  - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- API / 通知
  - KABU_API_BASE_URL — kabusapi の base URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY — OpenAI API キー（news/regime の機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE）用。未設定時は送信をスキップ
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db） ※Monitoring は常に production sqlite_path を使用
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" で有効）
- Paper Trading
  - PAPER_FILL_MODE — paper_trading 時のモック約定挙動（"instant" | "partial" | "never" | "reject"。デフォルト "instant"）
- モニタリングしきい値
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（% 指定）
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト "development"）
  - LOG_LEVEL — "DEBUG" | "INFO" | ...（デフォルト "INFO"）

アプリケーション起動（使い方）
------------------------------

1) 監視ループを起動（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 説明:
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新します。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 実行時にプロセス優先度を "high" に設定しようと試みます（psutil 必要）。
  - Monitoring は KABUSYS_ENV に関係なく production sqlite_path（Settings.sqlite_path）を使用します。

2) ExecutionEngine を起動（注文実行）
- コマンド:
  - python -m kabusys.run_execution
- 説明:
  - 通常モードは本番 DB を利用しますが、KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時にプロセス優先度を "high" に設定します。
  - 実行中は PID ファイル（Settings.pid_file_path）を更新します。kill.flag（Settings.kill_flag_path）が書かれると停止を受け取る仕組みと連携できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を削除します。

3) Paper Trading 検証レポート生成（ツール）
- コマンド例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合: --db data/paper_trading.db
- 説明:
  - paper_trading の SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・レイテンシなどを集計してテキストレポートを出力します。

4) Streamlit ダッシュボード（監視画面）
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only モードで SQLite を開き、ダッシュボードを表示します。MonitoringEngine が生成する data/monitoring.db を参照してください。

5) AI（ニューススコア / レジーム判定）
- 関数（プログラム経由で呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 必要条件:
  - OPENAI_API_KEY が設定されていること（または引数で渡す）。
  - OpenAI API の呼び出しは冗長対策（リトライ、フェイルセーフ）を含みます。テストでは API 呼び出し関数をモックできます。

監視・リスク関連の挙動
-------------------
- kill.flag:
  - KillSwitch が条件（例: ドローダウン超過・ポジション上限超過）を満たすと Settings.kill_flag_path に reason を書き込みます。ExecutionEngine はこのファイルの存在を検出して安全に停止できます。
  - KillSwitch は既にファイルが存在する場合は再書き込みしません（冪等）。
- RiskMonitor:
  - ダッシュボードの portfolio_value を元にハイウォーターマーク / ドローダウンを算出し、閾値を超えると risk_logs にログを書きます。
- TradeMonitor:
  - 発注レポジトリを参照して滞留注文（stale）や約定価格の異常（anomaly）を検出・ログ化します。
- AlertManager:
  - LINE Messaging API を使って通知。トークン未設定やクールダウン中は送信をスキップします。

データベースとマイグレーション
---------------------------
- Monitoring 用 SQLite スキーマは init_monitoring_db() で作成・移行されます（冪等）。run_monitoring / run_execution 起動時に呼ばれます。
- デフォルトのファイル:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定の読み込みロジック
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト
- ai/
  - __init__.py
  - news_nlp.py                — ニュース NLP / OpenAI 連携
  - regime_detector.py         — 市場レジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py           — SQLite 操作用ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - (order_manager.py, reconciler.py, order_repository.py, broker_factory など)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- utils/
  - process_priority.py        — psutil を使った優先度/affinity 設定
- tools/
  - paper_verification_report.py
  - __init__.py

開発者向けメモ
---------------
- 環境変数自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を起点に .env / .env.local を自動読み込みします。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しのテスト:
  - news_nlp._call_openai_api や regime_detector._call_openai_api をパッチしてモックすることを想定しています。
- ロギング:
  - run_* スクリプトは logging.basicConfig(level=logging.INFO) を使用します。詳細ログが必要な場合は LOG_LEVEL を "DEBUG" に設定してください。
- 互換性:
  - process_priority はプラットフォーム差分（Windows / POSIX）を吸収する実装です。管理者権限が必要な場合があり、失敗時は警告を出して続行します。

トラブルシューティング
---------------------
- DB が開けない（Streamlit 等）:
  - MonitoringEngine を起動して SQLite ファイルが生成されていることを確認してください。streamlit のコマンドは read-only モードで開きます。
- OpenAI キーがない:
  - news_nlp / regime_detector は API キーがない場合に例外を投げます。テストでは api_key 引数にモック値を渡すか、関数呼び出しをモックしてください。
- kill.flag が残って起動できない:
  - KILL_FLAG_CLEAR_ON_START=1 を設定して起動するか、手動で data/kill.flag を削除してください。

ライセンス・貢献
----------------
- 本 README にライセンス文は含めていません。リポジトリの LICENSE を参照してください。貢献はプルリクエストで受け付けます。

以上が本コードベースの利用・開発に必要な概要です。必要であれば「実行例（環境変数の具体例）」「DI（依存注入）やテストの書き方」など、より詳細な使い方ドキュメントを追加します。どの部分を詳しく書きますか？