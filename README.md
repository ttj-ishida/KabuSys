README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模フレームワークです。  
主な機能として、注文実行エンジン（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築ユーティリティ、リサーチ（ファクター計算・特徴量探索）、AI を使ったニュースセンチメント評価・レジーム判定、ならびにモニタリング用のストリームリット・ダッシュボードや検証レポート生成ツールを提供します。

特徴
----
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を環境で切替。paper_trading では MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離。
  - リスク管理（RiskManager）、注文管理（OrderManager）、再突合（Reconciler）を組み合わせた起動フローを実装。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/Memory/Disk）、データ鮮度、滞留注文、約定異常、ドローダウンなどを定期的に監視・ログ化。
  - kill.flag を書き込んで ExecutionEngine に停止シグナルを送出する仕組み。
  - LINE へのプッシュ通知（AlertManager）とクールダウン管理。
  - Streamlit ベースの監視ダッシュボードを提供（読み取り専用）。
- Portfolio（portfolio パッケージ）
  - 候補選定、等配分 / スコア加重配分、セクター制限、リスクベースのポジションサイズ計算。
- Research（research パッケージ）
  - DuckDB 上の prices_daily / raw_financials などを使ったファクター計算（モメンタム / ボラティリティ / バリュー）と IC 等の解析ユーティリティ。
- AI（ai パッケージ）
  - ニュース記事をまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込む（news_nlp）。
  - ETF の MA 乖離とマクロセンチメントを合成して市場レジーム（bull/neutral/bear）を判定（regime_detector）。
- ツール
  - paper_trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）。

セットアップ
----------
前提
- Python 3.10+（typing の | 型注釈を使用）
- duckdb, psutil, requests, openai, streamlit などの依存パッケージ

例: 必要パッケージをインストールする
- requirements.txt がない場合は代表的なパッケージをインストールしてください:
  - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込みます（自動ロード）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数（一部、デフォルト値はコード内注記）:
  - KABUSYS_ENV: 起動環境（development | paper_trading | live） — デフォルト: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は通知を行わない）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: Monitoring SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視関連）
- .env の書式は shell 形式に近く、コメント / export 形式に対応します。自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に行われます。

使い方（起動コマンド）
--------------------

1) 監視ループ（Monitoring）
- デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒単位、1 秒以上）。
- 実行例（パッケージ化されている / PYTHONPATH にあることが前提）:
  - python -m kabusys.run_monitoring
  - あるいはスクリプトを直接: python src/kabusys/run_monitoring.py
- 動作:
  - Settings を読み取り、Monitoring 用 SQLite（settings.sqlite_path）を使用して監視ログを永続化します（monitoring は環境にかかわらず本番 sqlite_path を使用）。
  - プロセス優先度を "high" に設定し、SystemMonitor.check_once を定期実行します。

2) 実行エンジン（Execution）
- paper_trading モードの場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録します。
- 実行例:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 動作:
  - BrokerClientFactory によりブローカークライアントを作成。
  - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine.run_session() を実行。
  - Execution 起動時は PID ファイルを書込み（Settings.pid_file_path）プロセス優先度を設定します。

3) Streamlit ダッシュボード（監視）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

4) Paper Trading 検証レポート
- ツール: kabusys.tools.paper_verification_report
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/db
- 出力:
  - 稼働率、注文成功率・送信率、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL を判定します。
- しきい値（コード内定数）:
  - 稼働率 >= 99.0%
  - 注文成功率 >= 90.0%
  - 送信率 >= 95.0%
  - P95 レイテンシ <= 200 ms

5) AI 機能（ニュース NLP / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.DuckDBPyConnection）を渡して対象日のニュースを評価し、ai_scores テーブルへ書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime テーブルへ書き込みます。
- OpenAI API キーは引数で渡すか、環境変数 OPENAI_API_KEY を使用。

設定・挙動のポイント
-------------------
- Settings クラス（kabusys.config.Settings）からアプリケーション設定を取得できます。多くは環境変数ベースです。
- 自動 .env ロード順: OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされません）。
- MONITOR_POLL_INTERVAL（秒）で監視ポーリング間隔を指定できます。無効値（0 以下や非整数）はデフォルト 60 秒にフォールバックします。
- paper_trading モードは本番 DB と完全に分離されるように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Process priority / CPU affinity:
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出します（psutil を使用）。権限不足や未対応 OS の場合は警告ログを出してスキップします。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ / MonitoringDB クラス
    - system_monitor.py             — システム・データ鮮度監視
    - trade_monitor.py              — 注文滞留・約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 制御
    - alert_manager.py              — LINE プッシュ通知
    - monitoring_engine.py          — 各 Monitor を束ねるループ
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine などの実装群)
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
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
    - news_nlp.py                    — ニュースセンチメント評価（OpenAI）
    - regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - data/ (想定：DuckDB/SQLite のファイルを配置するディレクトリ)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

開発・テストのヒント
--------------------
- .env.example を参照して .env を作成してください（プロジェクトルートに置くことで自動ロードされます）。
- Unit テストや一部スクリプトは DB ファイルパスを引数で受け取れる（例: --db）のでテスト専用 DB を用意すると安全です。
- OpenAI 呼び出し部はリトライ・例外処理が入っていますが、テスト時は該当関数 (_call_openai_api 等) をモック化して実行することを推奨します。
- streamlit ダッシュボードは SQLite を読み取り専用で開きます（URI に ?mode=ro を付与）。MonitoringEngine が生成する DB が存在しないとエラー表示になります。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（コード内定義）。

お問い合わせ / 貢献
------------------
バグ報告や機能提案は Issue を立ててください。プルリクエスト歓迎です。README の改善やドキュメント追加も助かります。

以上。