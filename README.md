KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
本リポジトリには取引実行（Execution）、監視（Monitoring）、ポートフォリオ構築／サイズ決定、リサーチ（ファクター計算）、および AI（ニュース NLP / レジーム判定）関連のユーティリティが含まれます。  
各機能はできるだけ純粋関数／副作用を分離して設計されており、SQLite / DuckDB をデータ永続化層として使用します。

主な特徴
--------
- Execution（発注）スタック
  - Broker クライアントの抽象化と OrderManager / ExecutionEngine（起動スクリプトあり）
  - 再起動時のリコンシリエーション（Reconciler）
  - RiskManager によるポジション・利用率制御
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite）と簡易ダッシュボード（Streamlit）
  - KillSwitch（条件に応じて flag ファイルを書き Execution を停止）
  - LINE 通知用 AlertManager（クールダウン管理付き）
- Portfolio（銘柄選定・重み・株数決定）
  - 候補選定、等配分・スコア配分、リスク調整、単元丸めまでの一連の純粋関数
- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value ファクターの DuckDB ベース計算
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースの銘柄別センチメント算出（ai_scores への書き込み）
  - マクロニュース + ETF (1321) MA200 乖離を使った日次レジーム判定（market_regime への書き込み）
- 開発運用向けツール
  - Paper Trading の検証レポート生成スクリプト
  - Streamlit 監視ダッシュボード

前提 / 依存
------------
主な外部依存（例）
- Python 3.10+
- duckdb
- psutil
- requests
- openai (OpenAI Python SDK)
- streamlit（ダッシュボードを使う場合）

pip インストール例:
pip install duckdb psutil requests openai streamlit

設定（環境変数）
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（読み込みの自動化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な設定項目（デフォルトや有効値は Settings クラス参照）:
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。paper_trading では MockBroker を用い、paper 専用 SQLite を使います。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う処理（news_nlp / regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト data/kill.flag）
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring 起動時のポーリング間隔（秒、デフォルト 60）

セットアップ手順
--------------
1. リポジトリをクローンし、Python 環境を用意します。
2. 依存パッケージをインストール：
   pip install -r requirements.txt
   （requirements.txt が無い場合は上記の主要パッケージを個別にインストール）
3. 環境変数の用意：
   - プロジェクトルートに .env を作成するか、環境変数で設定します。
   - 例（.env）:
       KABUSYS_ENV=development
       JQUANTS_REFRESH_TOKEN=your_token
       KABU_API_PASSWORD=your_password
       OPENAI_API_KEY=sk-...
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
4. data ディレクトリを作成：
   mkdir -p data
5. DuckDB / SQLite の初期化は多くの実行スクリプトが自動的に行うため、通常は追加操作不要です。
   （init_monitoring_db() が必要なテーブルを作成します）

使い方（主要スクリプト）
----------------------
- 監視ループ（Monitoring）を起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に sqlite_path（本番 DB）を使用します（KABUSYS_ENV に依存しない）
  - 起動時にプロセス優先度を "high" に設定しようと試みます（権限によってはスキップ）

- ExecutionEngine（発注処理）を起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 実行前に .env で必要な API キー／資格情報を設定してください。

- Streamlit ダッシュボード（監視）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開きます。MonitoringEngine がデータを書き込んでいることが前提です。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。--db で上書き可能。
  - 統計（稼働率、注文成功率、レイテンシ等）を集計して標準出力にレポートを表示します。

- AI 関連（プログラムから呼び出す例）
  - ニュース NLP スコア生成（プログラム呼び出し）:
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect('data/kabusys.duckdb')
      score_news(conn, date(2026, 4, 1), api_key='sk-...')
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026, 4, 1), api_key='sk-...')

設計上のポイント / 注意事項
------------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探す）を基準に行われます。CWD に依存しません。
- MONITORING 系の DB 初期化（テーブル作成）は起動スクリプトが自動で行います（init_monitoring_db）。
- paper_trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しはリトライ・バックオフを内包し、致命的エラー時はフェイルセーフ的にスコアを 0 またはスキップする設計です（例外をシステム全体に波及させない）。
- ExecutionEngine / Monitoring の起動時にプロセス優先度や PID / kill.flag を使った監視・停止制御が行われます。運用時はこれらのファイルパスに十分注意してください。
- PAPER_FILL_MODE（instant / partial / never / reject）で PaperTrading の約定挙動を制御できます。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py                — パッケージ定義
- config.py                  — 環境変数 / 設定管理（Settings）
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

/monitoring
- monitoring_db.py           — monitoring SQLite テーブル定義 + MonitoringDB ラッパ
- system_monitor.py          — システム状態 / データ鮮度監視
- trade_monitor.py           — 注文滞留・約定異常監視
- risk_monitor.py            — ドローダウン・ポジション上限監視
- monitoring_engine.py       — 各 monitor を束ねるループ
- alert_manager.py           — LINE 通知
- kill_switch.py             — kill.flag 制御
- streamlit_dashboard.py     — Streamlit ダッシュボード

/portfolio
- portfolio_builder.py       — 候補選定・重み付け
- risk_adjustment.py         — セクターキャップ・レジーム乗数
- position_sizing.py         — 株数計算（単元丸め・キャップ・スケーリング）

/research
- factor_research.py         — Momentum / Volatility / Value 等のファクター計算（DuckDB）
- feature_exploration.py     — 将来リターン・IC・統計サマリ等

/ai
- news_nlp.py                — ニュースを LLM でスコアリングして ai_scores に書き込む
- regime_detector.py         — 市場レジーム判定（MA200 + マクロ NLP）

/execution
- order_manager.py
- reconciler.py
- ...（Execution 関連の他モジュール）

/tools
- paper_verification_report.py — Paper Trading の検証レポート生成ツール

テスト／開発メモ
----------------
- 多くの関数は副作用を抑えた純粋関数で実装されているためユニットテストが容易です（DuckDB 接続をモックしてファクター計算等を検証）。
- OpenAI 呼び出しや外部 API 呼び出しは内部関数を patch してテスト可能です（コード中にパッチ対象を想定した注記あり）。
- ローカル検証時は KABUSYS_ENV=paper_trading を使い、デフォルトの paper DB に対して動作を確認してください。

ライセンス / バージョン
---------------------
パッケージバージョンは kabusys.__version__ に定義されています（現在: 0.1.0）。  
ライセンス情報はリポジトリの top-level ファイルを参照してください（この README はコードベースのドキュメント生成を目的とした要約です）。

付記
----
この README はコード内の docstring と設計コメントをもとに作成しています。運用時の詳細な手順や運用ポリシー（デプロイ手順、監視アラートの受信設定、バックアップ、権限周り）は運用ドキュメントに別途まとめてください。質問や追加で欲しいセクション（例: デプロイ手順、詳しい .env 例、API モックの説明など）があれば教えてください。