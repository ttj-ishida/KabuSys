KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買を想定した小型のシステム群です。下記の主要機能を持ち、実運用・モニタリング・検証（Paper Trading / Research）用途をサポートします。

特徴（ざっくり）
- 注文作成・送信・状態同期（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）とアラート（LINE Push）
- Paper Trading 用の分離された SQLite DB（data/paper_trading.db）
- DuckDB ベースの市場データ処理（ファクター計算、リサーチ）
- ニュースを GPT 系モデルでスコアリングする AI モジュール（news_nlp）と
  マクロ＋MA によるレジーム判定（regime_detector）
- 監視用 Streamlit ダッシュボード、Paper Trading 検証レポート生成ツール

主な機能一覧
--------------
- 実行（Execution）
  - Broker クライアント抽象化（実運用 / モック切替）
  - OrderManager による発注フロー管理（Duplicate 検出、2 相永続化など）
  - Reconciler による起動時リコンシリエーション（注文・ポジションの突合）
- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス存否 / データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ記録
  - MonitoringEngine：上記を束ねたポーリングループ、KillSwitch による停止フラグ
  - AlertManager：LINE push による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（監視 DB の可視化）
- ポートフォリオ構築（Portfolio）
  - 候補選定、等分配／スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（Research）
  - ファクター（momentum / volatility / value）計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI 経由）
  - ニュースセンチメントスコアの算出（銘柄別）
  - マクロセンチメント + ETF MA200 による市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
-----------------
前提
- Python 3.9+（コードは型ヒント等で新しめの構文を使用）
- sqlite3 は標準で付属
- DuckDB、OpenAI SDK、psutil、requests、streamlit などが必要

推奨インストール例
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai psutil requests streamlit

   （プロジェクトに requirements.txt があればそれを使ってください。）

設定（環境変数 / .env）
- プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
- 主な環境変数（必須・任意）:
  - JQUANTS_REFRESH_TOKEN (必須; J-Quants 用)
  - KABU_API_PASSWORD (必須; kabuステーション API パスワード)
  - OPENAI_API_KEY (AI 機能を使う場合必須)
  - KABUSYS_ENV (動作モード: development / paper_trading / live) — デフォルト: development
  - LOG_LEVEL (DEBUG/INFO/...)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視DB のデフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading の DB: data/paper_trading.db)
  - PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject; デフォルト: instant)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （LINE 通知を使う場合）
  - PID_FILE_PATH / KILL_FLAG_PATH 等（監視・制御用のファイルパス）
- 例（.env）
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_kabu_password
  OPENAI_API_KEY=sk-...
  KABUSYS_ENV=paper_trading

DB 初期化
- 監視用 SQLite DB schema は init_monitoring_db() により冪等的に作成されます。実行スクリプトが自動で初期化します。

使い方
--------
起動・実行
- 実行エンジン（ExecutionEngine）を起動する:
  - KABUSYS_ENV を設定してから:
    - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行開始時にプロセス優先度を "high" に設定します（psutil の権限によってはスキップされます）。

- 監視ループを起動する:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を参照します（環境に関わらず）。

- Streamlit ダッシュボードを起動する:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI モジュール（ニューススコア / レジーム判定）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（prices_daily などのテーブルがあること）、target_date を渡して銘柄ごとのニューススコアを ai_scores テーブルに書き込みます。
  - api_key が None の場合は環境変数 OPENAI_API_KEY を使用します。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを組み合わせて market_regime テーブルへ書き込みます。

監視 / Kill switch の挙動
- RiskMonitor がドローダウンやポジション上限を検出すると risk_logs に記録し、KillSwitch が条件に合致すれば data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine 側は起動時に kill.flag をクリアするオプション（Settings.kill_flag_clear_on_start）があります。

Config（Settings）
- 設定は kabusys.config.Settings 経由で取得します。プロジェクトルートの .env / .env.local と OS 環境変数から読み込みます。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければエラーになります。

ディレクトリ構成（主要ファイル説明）
-----------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数読み込み・Settings クラス（各種パス・閾値・フラグ）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により Mock/real broker 切替）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）

- ai/
  - news_nlp.py
    - ニュース記事を OpenAI でセンチメント解析し ai_scores に書き込む
  - regime_detector.py
    - ETF MA200 とマクロニュースで市場レジームを判定
  - __init__.py

- monitoring/
  - monitoring_db.py
    - SQLite スキーマ作成・監視ログ操作クラス（MonitoringDB）
  - system_monitor.py
    - CPU/Mem/Disk/プロセス存在/データ鮮度監視
  - trade_monitor.py
    - 注文滞留・約定異常検出
  - risk_monitor.py
    - ドローダウン・ポジション上限監視
  - kill_switch.py
    - data/kill.flag による停止トリガー
  - alert_manager.py
    - LINE Push 通知（クールダウン付き）
  - monitoring_engine.py
    - 複数 Monitor を束ねるエンジン
  - streamlit_dashboard.py
    - Streamlit ベースのダッシュボード
  - __init__.py

- execution/
  - order_manager.py
    - 発注ワークフロー（作成・送信・同期）
  - reconciler.py
    - 起動時リコンシリエーション（注文・ポジション突合）
  - order_repository.py, order_record.py, broker_factory.py, broker_api.py, ...（実行周りの補助モジュール）
  - （※一部ファイルはここに含まれている想定。コードベースに依存）

- portfolio/
  - portfolio_builder.py
    - 候補選定・スコアソート
  - position_sizing.py
    - 発注株数算出・単元丸め・集計キャップ
  - risk_adjustment.py
    - セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py
    - 将来リターン・IC・統計サマリー
  - __init__.py

- tools/
  - paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI
  - __init__.py

- utils/
  - process_priority.py
    - プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

その他 / データ
- data/
  - data/kabusys.duckdb (DuckDB のデータベースファイル — デフォルト)
  - data/monitoring.db (監視用 SQLite)
  - data/paper_trading.db (Paper Trading 用 SQLite)

運用上の注意
-------------
- Paper Trading は本番 DB と完全分離されます（Settings.is_paper 判定で paper_sqlite_path を使用）。
- OpenAI を呼び出す機能は API キーが必要です。失敗時はフォールバックやスキップする実装が多くありますが、API 利用コストに注意してください。
- psutil を使った優先度変更は権限依存です。権限がないと設定に失敗する可能性があります（警告ログのみ）。
- DuckDB 操作・executemany の空リストバインドなど、バージョン差異に敏感な箇所があります（コード中に互換性対策あり）。

問い合わせ / 貢献
-----------------
- この README はコードベースから抽出した設計意図・利用方法をまとめたものです。実際のデプロイ前に .env の内容や Broker クライアント設定、権限（psutil・ファイル書き込み）などを確認してください。
- バグ報告・機能提案があれば issue を作成してください（リポジトリ運用ポリシーに従ってください）。

以上です。必要であれば README に入れるコマンド例や .env.example のテンプレートを出力できます。どの形式（短縮版 / 詳細版）を希望しますか？