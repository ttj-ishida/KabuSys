KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。取引実行（ExecutionEngine）、監視・アラート（Monitoring）、ポートフォリオ構築（Portfolio construction）、ファクター計算やリサーチ機能、LLM を使ったニュースセンチメント評価（AI モジュール）などを含みます。内部では SQLite（監視ログ等）と DuckDB（時系列・ファイナンスデータ）を使い、実運用向けのフェイルセーフ（再起動後のリコンシリエーション、キルスイッチ等）を備えた設計になっています。

主な機能
--------
- Execution
  - Broker 抽象化（実ブローカー / Paper trading の Mock 切替）
  - OrderManager による注文状態管理と二相永続化（クラッシュ耐性）
  - Reconciler による再起動時の注文・ポジション照合
  - RiskManager による発注前リスクチェック（最大ポジション比率、利用率、ドローダウン等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、実行プロセス生存の監視
  - TradeMonitor：滞留注文、約定異常の検出
  - RiskMonitor：ドローダウン・ポジション数上限監視、ダッシュボード更新
  - MonitoringDB：SQLite に永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch：条件に応じてフラグファイルを書き、ExecutionEngine を停止させる仕組み
  - Streamlit ベースの監視ダッシュボード（read-only で monitoring DB を参照）
  - LINE Push によるアラート送信（AlertManager）
- Portfolio Construction（純粋関数群）
  - 候補選定、等重・スコア加重のウェイト計算
  - セクター集中制限、レジーム乗数
  - 発注株数決定（リスクベース／等分配等）、単元株丸め、aggregate cap のスケールダウン
- Research / Data
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - news_nlp: ニュースを LLM に送って銘柄ごとのセンチメントを計算して ai_scores テーブルに保存
  - regime_detector: ETF（1321）MA とマクロニュース LLM を合成して日次レジーム判定
  - 冪等性・フェイルセーフ（API エラー時は安全なフォールバック）
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ（Windows / POSIX 対応）
  - .env ロード機能（.env / .env.local 自動読み込み。無効化可）

セットアップ手順
--------------
前提
- Python 3.10+ を推奨（型注釈に union 型や Path 機能を使用）
- SQLite は標準ライブラリに含まれます
- DuckDB, psutil, requests, streamlit, openai などが必要

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は少なくとも下記をインストールしてください）
   - pip install duckdb psutil requests streamlit openai

4. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置いて設定可能。自動読み込みはデフォルトで有効。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等（外部 API 連携時に必要）
     - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper trading 用 DB（デフォルト data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 時の約定挙動）

5. データディレクトリの作成
   - mkdir -p data

基本的な使い方
--------------
- 監視ループを起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を "high" に設定し、MonitoringDB（SQLite）と DuckDB に接続して SystemMonitor のポーリングを繰り返します。

- ExecutionEngine（取引エンジン）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB（data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - data/paper_trading.db を読み、期間指定で検証レポートを標準出力へ出力します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - デフォルト DB は data/paper_trading.db。--db で別パス指定可。

- Streamlit ダッシュボード（監視）
  - 実行方法:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - ダッシュボードは monitoring DB を読み取り専用（URI に ?mode=ro を付与）で表示します。MonitoringEngine が書き込んでいる必要があります。

- AI モジュール
  - ニューススコアリング（news_nlp.score_news）やレジーム判定（regime_detector.score_regime）は OpenAI API キーが必要です。コード内関数をスケジューラや手動実行から呼び出すことを想定しています（例: スケジューラが日次に score_news を呼ぶ）。
  - OpenAI の呼び出しはバックオフやリトライ、レスポンスバリデーションを実装しています。

環境変数の注意点
- 自動 .env ロードの優先順位:
  - OS 環境 > .env.local (override) > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テストなどで便利）。
- MONITOR_POLL_INTERVAL: 監視ループの秒数（1 以上の整数、無効値は 60 秒にフォールバック）

ディレクトリ構成
----------------
以下は主要ファイル / モジュールのサマリ（src/kabusys 以下）:

- __init__.py
  - パッケージのメタ情報（__version__ 等）

- config.py
  - 環境変数読み込み / Settings クラス（.env 自動読み込み、各種設定の取得）

- run_monitoring.py
  - SystemMonitor を定期実行するエントリポイント（MONITOR_POLL_INTERVAL で間隔制御）

- run_execution.py
  - ExecutionEngine の起動スクリプト（paper_trading モード対応）

- monitoring/
  - monitoring_db.py : SQLite スキーマ初期化と CRUD ヘルパ（MonitoringDB）
  - system_monitor.py : CPU/MEM/DISK、プロセス生存、データ鮮度監視
  - trade_monitor.py  : 滞留注文・約定異常の検出
  - risk_monitor.py   : ドローダウン・ポジション上限の監視
  - monitoring_engine.py : 複数 Monitor を束ねるエンジン
  - kill_switch.py    : フラグファイルによる強制停止機構
  - alert_manager.py  : LINE push 通知クライアント
  - streamlit_dashboard.py : Streamlit ベースの監視 UI

- execution/
  - order_manager.py  : 注文状態遷移 API（create/send/cancel 等）
  - order_repository.py: SQLite ベースの注文永続化（OrdersDB）
  - reconciler.py     : 再起動時の Order / Position 照合
  - risk_manager.py   : 発注前のリスクチェック（設定あり）
  - broker_factory.py : Broker クライアント生成（実ブローカー / Mock 切替）

- portfolio/
  - portfolio_builder.py : 候補選定、等重／スコア重み
  - position_sizing.py   : 株数計算、aggregate cap のスケーリング
  - risk_adjustment.py   : セクター上限、レジーム乗数

- research/
  - factor_research.py   : Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- ai/
  - news_nlp.py         : ニュースを LLM でスコアリングして ai_scores に書込む
  - regime_detector.py  : ETF MA とマクロニュースから市場レジームを判定して保存
  - __init__.py         : ai の公開 API（score_news など）

- data/  (運用時に使用されるパス。デフォルト)
  - kabusys.duckdb (DuckDB)
  - monitoring.db (SQLite)
  - paper_trading.db (Paper trading 用 SQLite)

- tools/
  - paper_verification_report.py : Paper trading DB から検証レポートを生成するスクリプト

運用上の注意
------------
- Paper trading モード（KABUSYS_ENV=paper_trading）は本番 DB と明示的に切り離すため PAPER_TRADING_SQLITE_PATH を利用します。テスト／検証時は必ず paper_trading モードを使って実データを書き換えないようにしてください。
- AI（OpenAI）を利用する機能は外部 API 呼び出しであり、API キー漏洩やコスト管理に注意してください。API エラー時は安全側のフォールバックが入りますが、意図しない欠損データが発生することがあります。
- 実稼働時はプロセス優先度や CPU affinity の設定が必要な場合があります（utils/process_priority.py を参照）。権限がない環境では警告を出してスキップします。
- MonitoringDB のスキーママイグレーションは一部簡易対応（カラム追加など）を行いますが、大規模な変更は別途マイグレーションを検討してください。

貢献・開発
----------
- 開発用に src をパッケージとしてインストールする場合:
  - pip install -e .
- 単体モジュールのテストや CI を導入するときは、環境変数読み込みを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）か、テスト用の .env を用意してください。

サポート / ドキュメント
---------------------
- 各モジュール内の docstring に詳細な設計意図・入出力仕様が記載されています。実装や拡張の際はまずモジュールの docstring を参照してください。
- 主要な設計参照: PortfolioConstruction.md / StrategyModel.md（リポジトリ内に存在する場合）

以上がこのコードベースの概要と導入・運用ガイドです。必要であれば環境変数テンプレート（.env.example）や requirements.txt 生成、運用例（systemd / supervisor 用のユニットファイル）などの追補ドキュメントを作成できます。どの部分を優先してドキュメント化するか教えてください。