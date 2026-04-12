KabuSys — 日本株自動売買システム
================================

このリポジトリは、株式の自動売買エンジン（Execution）と稼働監視（Monitoring）、研究用ファクター計算・解析、AI を使ったニュースセンチメント評価などを含む日本株自動売買システムのコードベースです。本 README はコードベース（src/kabusys 以下）の概要・機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
- 日本株自動売買のコア機能（注文管理、リスク管理、起動時リコンシリエーション）を備えた実行エンジン。
- システム稼働状況・注文ログ・リスクログ等を SQLite に永続化する監視コンポーネント（Monitoring）。
- DuckDB を使った価格・財務データを用いるリサーチ（ファクター計算、将来リターン、IC 計算など）。
- OpenAI（gpt-4o-mini 等）を利用したニュースの NLP スコアリング・市場レジーム判定（AI モジュール）。
- Paper Trading モード（実際のブローカーとは分離された専用 DB を使った検証）をサポート。
- Streamlit ベースの監視ダッシュボードや、Paper Trading 検証レポート等のツール。

主な機能一覧
-------------
- Execution（発注）：
  - OrderManager / ExecutionEngine：Signal を受けて注文生成・送信、状態管理。
  - BrokerClientFactory によるブローカークライアント抽象化（本番 / mock 切替）。
  - Reconciler による起動時の注文・ポジション照合（自動復旧）。
  - RiskManager によるポジション上限・ドローダウン等のリスク判定。
- Monitoring（監視）：
  - SystemMonitor：CPU / メモリ / ディスク / プロセス存否 / データ鮮度監視。
  - TradeMonitor：滞留注文・約定価格異常を検出。
  - RiskMonitor：ドローダウンやポジション上限の監視・alert ログ記録。
  - KillSwitch：条件に応じてフラグファイルを書き、Execution を停止させる仕組み。
  - AlertManager：LINE Messaging API での通知（クールダウン機能付き）。
  - MonitoringEngine：上記モニタをまとで定期実行するポーリングループ。
  - Streamlit ダッシュボード（監視データ可視化）。
- Research（研究）：
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）。
  - 将来リターン計算、IC（スピアマンランク相関）計算、統計サマリ。
- AI：
  - news_nlp.score_news：raw_news を集約して LLM（OpenAI）で銘柄ごとのセンチメントスコアを生成し ai_scores テーブルへ書込む。
  - regime_detector.score_regime：ETF（1321）MA200 とマクロニュースの LLM スコアを合成して market_regime を判定/保存。
- Portfolio（ポートフォリオ構築）：
  - 候補選定、等ウェイト・スコア加重・リスクベースの株数算出、セクター上限・レジーム乗数適用等。
- Tools：
  - paper_verification_report：Paper Trading DB を解析して運用検証レポートを生成。

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 記法、型ヒントの挙動を利用しているため）。
- DuckDB、psutil、requests、openai、streamlit 等の Python パッケージ。

推奨インストール手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （実運用では requirements.txt を用意している場合はそれを使ってください）

環境変数 / .env
- 設定は環境変数かプロジェクトルートの .env / .env.local に配置して読み込みます。
- 自動ロードはデフォルトで有効。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 必須（例）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（使用する場合）
  - KABU_API_PASSWORD — kabuステーション API パスワード（Execution の本番接続で必要）
- 重要なオプション（デフォルトを併記）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: ブローカーはモック、DB は paper_trading 専用 DB を使用
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject (paper trading の約定挙動、デフォルト instant)
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

DB 初期化
- 監視 DB（SQLite）は run_monitoring/run_execution 起動時に init_monitoring_db() でテーブル作成および必要なマイグレーションが実行されます（冪等）。
- DuckDB（時系列データ）は別に用意してください（prices_daily, raw_financials, raw_news 等のテーブルが前提）。

使い方（起動・ツール）
---------------------

実行エントリ（パッケージとして実行可能）
- 監視ポーリング（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL を設定するとポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 起動時にプロセス優先度を high に設定し、SQLite / DuckDB に接続します

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 SQLite に記録します
  - 実行前に .env で KABU_API_PASSWORD や必要な設定を用意してください

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
  - デフォルト DB: data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開き、Overview / Positions / Orders / System を表示

AI 関連
- OpenAI を使う処理（news_nlp.score_news / regime_detector.score_regime）は OPENAI_API_KEY が必要です。
- これらは DuckDB の raw_news / news_symbols / ai_scores 等のテーブルを参照します。
- API 呼び出しはリトライやバックオフ、レスポンス検証を入れてフェイルセーフに設計されています。

モードの違い（paper_trading と live）
- paper_trading:
  - ブローカーはモック実装（実ブローカ接続はしない）
  - DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離
- live:
  - 本番ブローカー接続、実際の注文明細を送信

運用上のポイント
- Execution 起動時に PID ファイル（default data/execution.pid）を生成し、SystemMonitor が生存確認を行います。
- KillSwitch は条件を満たすと data/kill.flag に理由を書き込み、Execution に停止シグナルを与えます（Execution 側で kill.flag を検出して終了処理を行う設計を想定）。
- AlertManager は LINE Push API を使ってアラート通知（channel token / user id を .env 設定）します。未設定時はログのみ。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ローダ、Settings
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化レイヤ（テーブル作成・CRUD ユーティリティ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager / Reconciler / ExecutionEngine 等の実装ファイル群)
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照される)
    - ...（ブローカー抽象 / factory 等）
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
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (想定されるデータディレクトリ、リポジトリに含まれない場合は作成)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)

開発者向けメモ
----------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API の呼び出しは外部に依存するため、ユニットテストでは実際の呼び出しをモックすることを推奨します（コード内でも _call_openai_api を patch できる設計になっています）。
- DuckDB に格納するテーブル（prices_daily / raw_financials / raw_news 等）は想定スキーマがあるため、研究モジュール・AI モジュールを使う場合は事前にデータ投入が必要です。
- ロギングは基本的に logging.basicConfig(level=logging.INFO) で開始します。詳細デバッグが必要な場合は LOG_LEVEL を DEBUG に変更してください。

ライセンス・貢献
----------------
- 本 README ではライセンス情報は記載していません。リポジトリのルートに LICENSE ファイルがあればそちらを参照してください。
- バグ報告や機能改善の提案は issue を立てるかプルリクエストを送ってください。

以上がコードベース（src/kabusys）の README 相当の内容です。必要であれば .env.example のサンプルや、各モジュール（ExecutionEngine、OrderRepository、Broker 实装など）の詳細使用例・API ドキュメントを追加できます。どの部分を詳しく展開しましょうか？