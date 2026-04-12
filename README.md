README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した内部ライブラリ群です。  
主な責務は以下の通りです。

- 注文管理と ExecutionEngine による発注（実運用・ペーパートレード対応）
- 監視（プロセス状態、注文滞留、ドローダウン等）とアラート送信（LINE）
- ポートフォリオ構築（候補選定・重み算出・株数決定・セクター制約）
- 研究用ファクター計算・特徴量評価（DuckDB ベース）
- ニュースの NLP によるセンチメント評価 / 市場レジーム判定（OpenAI 利用）
- ペーパートレード検証レポート出力・監視用 Streamlit ダッシュボード

このリポジトリはライブラリ本体（src/kabusys）と複数の CLI / ツールを含みます。

機能一覧
--------
主な機能（モジュール単位）:

- execution
  - OrderManager, ExecutionEngine（実運用／paper_trading の切替）
  - BrokerClientFactory（本番/モックのブローカークライアント切替）
  - Reconciler（再起動時の注文・ポジション同期）
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセスPID/データ鮮度の監視
  - TradeMonitor：滞留注文 / 約定異常価格検出
  - RiskMonitor：ドローダウン監視・ポジション上限チェック
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）の出力
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringDB：SQLite を用いた監視ログの永続化とマイグレーション
  - Streamlit ダッシュボード（監視データの可視化）
- portfolio
  - 候補選定（select_candidates）、重み計算（等金額 / スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（lot 単位丸め、利用可能現金のスケール調整）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン計算 / IC 計算 / 統計サマリー）
- ai
  - news_nlp：ニュース集合を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector：ETF（1321）MA200 乖離とマクロセンチメントを合成してレジーム判定
- tools
  - paper_verification_report：ペーパートレード DB に対する検証レポート生成

セットアップ手順
--------------
前提
- Python 3.10 以上（PEP 604 型構文を利用）
- SQLite（標準ライブラリに含まれます）
- DuckDB、psutil、requests、openai、streamlit などの外部パッケージ

1. リポジトリを取得
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存関係をインストール
   必要な主なパッケージ（プロジェクトに requirements.txt が無い場合の例）:
   pip install duckdb psutil requests openai streamlit

   （テストや開発ツールがあれば適宜追加してください）

4. Python パスを通す
   - 開発時は PYTHONPATH=src を設定するか、パッケージを editable インストールします:
     export PYTHONPATH=$(pwd)/src
     もしくは
     pip install -e .

5. 環境変数の準備
   プロジェクトルートに .env または .env.local を置くことで自動的に読み込まれます（デフォルト）。
   自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（一部）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading を指定すると MockBrokerClient を使い、データは data/paper_trading.db に記録されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の使用箇所あり）
- KABU_API_PASSWORD: kabuステーション用パスワード
- OPENAI_API_KEY: OpenAI 呼び出しに使用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: ExecutionEngine の PID / kill flag のパス

使い方
------

共通
- ソースを直接実行する場合は PYTHONPATH=src を通すか、pip install -e . 後に実行してください。
- 設定値は .env / 環境変数で制御できます（config.Settings を参照）。

実行エンジン（本番 / ペーパートレード）
- 本番モード（env=live）:
  PYTHONPATH=src python -m kabusys.run_execution
- ペーパートレード:
  KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
  （paper_trading 時は data/paper_trading.db に発注ログが保存され、本番 DB と分離されます）
- ExecutionEngine は起動時にプロセス優先度を "high" に設定し、init_monitoring_db を呼び監視テーブルを準備します。

監視プロセス（Monitoring）
- システム監視をポーリングで実行:
  PYTHONPATH=src python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
- 監視は本番 sqlite_path を参照（KABUSYS_ENV に関わらず監視 DB は本番設定を使います）。

Paper Trading 検証レポート
- 単独スクリプトでレポートを生成します:
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

Streamlit ダッシュボード（監視可視化）
- 起動例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  （-- の後のオプションはアプリ側に渡ります）

AI モジュール（ニューススコア / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None) を呼んで ai_scores に書き込み
  - api_key を None にすると OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None) は market_regime テーブルへ書き込み
- 両方とも OpenAI API キーが必要（未設定時は ValueError を送出）

ログと DB
- 監視用 SQLite は init_monitoring_db() によって自動作成・必要カラムのマイグレーションを行います
 （例: trade_logs.latency_ms, dashboard.peak_value などの追加処理あり）。
- DuckDB は価格・財務データ等の集計用として使用されます（パフォーマンスを意識した設計）。

ディレクトリ構成
----------------
src/kabusys/
- __init__.py
  - パッケージ定義・バージョン
- config.py
  - 環境変数読み込みと Settings クラス（.env 自動読み込みロジック含む）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV 切替対応）
- run_monitoring.py
  - SystemMonitor 単独ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
- ai/
  - news_nlp.py
    - ニュースを OpenAI でセンチメント評価し ai_scores テーブルへ反映
  - regime_detector.py
    - マクロニュース + ETF MA200 乖離で市場レジーム判定
- execution/
  - reconciler.py
    - 再起動時の注文・ポジションリコンシリエーション
  - order_manager.py
    - 注文ライフサイクル管理（作成・送信・同期等）
  - （その他 execution 関連クラス群: broker_api, order_repository 等）
- monitoring/
  - monitoring_db.py
    - SQLite ベースの監視ログ永続化・マイグレーション
  - system_monitor.py, trade_monitor.py, risk_monitor.py
    - 各種監視ロジック（System / Trade / Risk）
  - kill_switch.py
    - 停止フラグ管理
  - alert_manager.py
    - LINE 送信ユーティリティ（クールダウン管理）
  - monitoring_engine.py
    - 3つの Monitor を束ねるポーリング Engine
  - streamlit_dashboard.py
    - Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py
    - 候補選定・重み計算
  - risk_adjustment.py
    - セクター制約・レジーム乗数
  - position_sizing.py
    - 株数計算・lot 単位丸め・aggregate cap ロジック
- research/
  - factor_research.py
    - momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py
    - 将来リターン計算 / IC / 統計サマリ
- tools/
  - paper_verification_report.py
    - ペーパートレード DB に対する検証レポート生成スクリプト
- utils/
  - process_priority.py
    - プラットフォームを吸収したプロセス優先度・CPU affinity 設定

開発メモ / 注意事項
------------------
- .env のパースはシェル形式の多くをサポートします（export プレフィックス、クォート、インラインコメント等）。
- config.Settings は起動時に必須の環境変数が未設定だと ValueError を投げます（必須項目は使用箇所に依存）。
- OpenAI を呼ぶ箇所は外部 API のため、ネットワークエラーやレート制限に対してリトライ戦略を備えていますが、APIキー未設定時は実行できません。
- Monitoring 周りは監視 DB（SQLite）を前提とします。運用時は適切なファイルパーミッションとディスク空き容量を確保してください。
- ExecutionEngine / Broker クライアントは未公開の実装（kabusys.execution.broker_*）に依存します。本番接続を行う場合は本実装の確認・設定が必要です。

サンプルコマンドまとめ
---------------------
- 仮想環境作成・依存インストール（例）
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil requests openai streamlit

- 実行（開発時）
  export PYTHONPATH=$(pwd)/src
  # ExecutionEngine（paper_trading）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # Monitoring
  python -m kabusys.run_monitoring

  # Paper trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

お問い合わせ・拡張
-----------------
- 新しいブローカー接続やマスター情報（銘柄ごとの lot_size、手数料モデルなど）を追加する場合は execution と portfolio 周りのインターフェースに沿って実装してください。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）は research / ai モジュールの前提です。データ投入スクリプトは別途用意してください。

以上。必要であれば README に付け加える内容（例: requirements.txt の生成、CI 実行方法、実運用チェックリストなど）をご指定ください。