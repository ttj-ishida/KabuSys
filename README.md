KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
戦略用のリサーチ・ファクター計算、ポートフォリオ構築、ポジションサイズ決定、実発注（本番／ペーパートレード）、監視（Monitoring）、およびニュースを使った AI スコアリング等の機能を含みます。  
設計方針として「本番口座への直接アクセスを伴わない研究機能」「環境変数／.env による設定」「安全なフェイルセーフ（Kill Switch 等）」を重視しています。

主な機能
--------
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上の prices_daily / raw_financials から計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、リスクベース配分
  - セクター集中抑制、レジームに応じた投下資金乗数
  - ポジションサイズ決定（単元株丸め、aggregate cap の調整）
- Execution（発注エンジン）
  - 本番 / ペーパートレードの分離（KABUSYS_ENV に依存）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient）
  - RiskManager、OrderManager、Reconciler、ExecutionEngine の統合
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch によるフラグファイル停止（安全停止）
- AI モジュール
  - ニュースの LLM（OpenAI）を用いたセンチメントスコアリング（news_nlp）
  - マクロ＋ETF MA を組み合わせた市場レジーム判定（regime_detector）
  - OpenAI API 呼び出しはリトライやレスポンス検証を備え安全に実装
- ツール
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）
- ユーティリティ
  - 統一ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対話ウィザード・設定検証 CLI

セットアップ
----------
前提:
- Python 3.10 以上を推奨（型アノテーションや最新パッケージを想定）
- DuckDB と SQLite（SQLite は標準で利用可能）

推奨的な手順:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - optional: pip install PyYAML  （config/*.yaml のパース検証を行う場合）
   - 追加で必要になるライブラリは実行環境に応じてインストールしてください

3. .env の作成
   - 対話ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは直接 .env をプロジェクトルートに作成
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定（news_nlp / regime_detector で使用）
   - 主要な設定項目（例、デフォルト値）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（例）
     - KILL_FLAG_CLEAR_ON_START: 0/1
     - PAPER_FILL_MODE: instant | partial | never | reject

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます

初回起動補足:
- DB（DuckDB/SQLite）は必要に応じて自動生成・初期化されます。config に指定したディレクトリを作成できるように権限を確認してください。
- 本番（KABUSYS_ENV=live）では kill flag の自動クリア等の設定に注意してください（デフォルトで自動クリアは無効推奨）。

使い方（主要スクリプト）
------------------------
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作: 設定に従って DB に接続し BrokerClient を生成、ExecutionEngine をデーモンスレッドで実行します
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を利用します
  - 停止: プロセスは data/stop_requested.flag の存在を検知して停止します。監視から Kill Switch が発動すると data/kill.flag が書かれます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は本番 sqlite_path を使用（環境にかかわらず）
  - 停止: data/stop_requested.flag による停止検出

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db で指定、環境変数 PAPER_TRADING_SQLITE_PATH からも参照

主要環境変数一覧（抜粋）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログファイル保存場所)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか、0/1)

停止・Kill Switch
-----------------
- run_execution / run_monitoring はプロセス中に data/stop_requested.flag を検出すると終了します（停止フラグ）。
  - stop flag のデフォルトパス: project_root/data/stop_requested.flag
- KillSwitch（監視コンポーネント）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止を促します。
- 注意: 本番運用時は KILL_FLAG_CLEAR_ON_START を 0 にして、誤った自動クリアを防いでください。

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトは src/kabusys 以下にモジュールが配置されています。主要な構成は以下の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュースの LLM センチメントスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化・読み書き層
    - system_monitor.py      — システム／データ鮮度監視
    - trade_monitor.py       — 発注ログ・滞留注文検出 等（実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — フラグファイルを書いて停止シグナルを送る
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — LINE 等への通知管理（実装に依存）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — BrokerClient の生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・スケールダウンロジック
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（Momentum / Value / Volatility）
    - feature_exploration.py — IC / 将来リターン / 統計
  - data/                    — データファイル（デフォルトパス: data/ 以下）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

補足 / 運用上の注意
------------------
- DB ファイル（DuckDB / SQLite）はデフォルトで data/ 以下に作成されます。自動作成に失敗する場合はパスや権限を確認してください。
- OpenAI を使う機能は外部 API に依存します。APIキーやコスト、レートリミットに注意してください。エラー耐性は組み込まれていますが、運用ポリシーを事前に決めてください。
- 本番環境（KABUSYS_ENV=live）では設定や通知（LINE）等を厳重に確認してください。validate_config の live 特有の警告を参照してください。
- ロギングは stdout と logs/<app_name>.log（日次ローテート）に出力されます。LOG_DIR 環境変数で変更可能です。

Contact / 開発
--------------
この README はコードベースの主要機能と運用手順のサマリです。実装の詳細や API の挙動は各モジュールの docstring を参照してください（例: kabusys/ai/news_nlp.py、kabusys/portfolio/position_sizing.py 等）。開発・拡張の際はユニットテストや設定検証を先に実行することを推奨します。

以上。必要であれば README に含めるサンプル .env テンプレートや起動例、よくあるトラブルシュートを追記します。どの情報を追加しますか？