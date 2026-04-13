KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を行うコードベースです。  
主に以下の責務を持つモジュール群で構成されています。

- 注文発行・リスク管理・リコンサイルを行う Execution（実行系）
- 監視・アラート・ダッシュボード（Monitoring）
- ポートフォリオ構築・ポジションサイズ算出（Portfolio）
- DuckDB を用いたファクター計算・研究（Research）
- OpenAI を用いたニュース NLP とレジーム判定（AI）
- 各種ユーティリティ（プロセス優先度設定・環境設定等）

主な特徴
--------
- 実運用向けに設計された監視（SystemMonitor / TradeMonitor / RiskMonitor）
- Paper Trading（分離された SQLite DB と MockBroker）に対応
- DuckDB を用いたオンプレミスな時系列 / ファクター計算
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントとレジーム判定（フェイルセーフ実装）
- LINE へのプッシュ通知によるアラート（クールダウン制御）
- Streamlit を使った監視ダッシュボード（読み取り専用）

必要条件
--------
- Python 3.10 以上（typing の union 演算子などを使用）
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリで利用可）

（依存はプロジェクトの requirements.txt を使用するか、上記パッケージをインストールしてください）

セットアップ
------------
1. リポジトリをクローンする
   - git clone <repository-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトで requirements.txt があれば pip install -r requirements.txt）

4. 環境変数 / .env の準備
   - プロジェクトルートの .env または .env.local に必要な設定を記述できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN            （必須）
     - KABU_API_PASSWORD                （必須）
     - OPENAI_API_KEY                   （AI 機能を使う場合必須）
     - KABUSYS_ENV                      : development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE                  : instant | partial | never | reject（paper_trading 用）
     - PAPER_TRADING_SQLITE_PATH        : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH                      : 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH                      : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知を使う場合）
   - 注意: Settings クラスは .env を自動で読み込みますが、OS 環境変数が優先されます。

初期化
------
- 監視用の SQLite（data/monitoring.db）は多くのスクリプト起動時に自動でテーブルを作成します（init_monitoring_db）。
- DuckDB データ（data/kabusys.duckdb）はファクター計算や research モジュールで使用します。必要なテーブル（prices_daily, raw_financials, raw_news 等）を事前にロードしてください。

使い方（代表的な起動方法）
------------------------

1. ExecutionEngine（実行エンジン）を起動
   - 本番・検証モードは KABUSYS_ENV によって切り替え
     - paper_trading のときは MockBrokerClient を使い、Paper Trading 用 DB に記録されます。
   - 起動コマンド:
     - python -m kabusys.run_execution
   - 実行時にプロセス優先度を "high" に設定します（psutil を使用）。PID ファイルや kill.flag の管理は Settings に従います。

2. Monitoring（監視ループ）を起動
   - 監視ループは polling で各種モニタ（System/Trade/Risk）を定期実行します。
   - 起動コマンド:
     - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
   - 監視は常に本番の sqlite_path を参照する点に注意（KABUSYS_ENV に依存しません）。

3. Streamlit ダッシュボード（監視用）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で監視 DB を参照します。MonitoringEngine を先に起動してください。

4. Paper Trading 検証レポート生成
   - data/paper_trading.db を解析して検証レポートを生成します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション --db で DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）。

5. AI（ニュース NLP / レジーム検出）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date を渡すと ai_scores テーブルに書き込みます。
     - API キーは引数または OPENAI_API_KEY 環境変数で指定。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF ma200 乖離とマクロニュースの LLM 評価を合成して market_regime に保存します。
   - いずれも API 呼び出し失敗時はフェイルセーフ（スコア 0 やスキップ）になっています。

運用上の注意
-------------
- Paper Trading は本番 DB と分離（paper_trading 用 SQLite）されます。KABUSYS_ENV=paper_trading を利用してください。
- Kill Switch: risk モニタが一定条件を満たすと kill.flag（デフォルト: data/kill.flag）を書き、ExecutionEngine に停止指示を出します。ExecutionEngine はこのフラグを監視します。
- Settings は自動で .env / .env.local を読み込みます。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI 利用時は API キー管理を十分に行ってください。リクエスト失敗はリトライロジックがありますが、コスト・レート制限に注意。

ディレクトリ構成
----------------
（主要ファイル・モジュールの説明）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み・Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/
    - order_manager.py
    - reconciler.py
    - (broker_factory, order_repository 等: 注文発行・リポジトリ・リコンシリエーション)

  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — CPU, メモリ, データ鮮度, PID チェック
    - trade_monitor.py        — 滞留注文 / 約定異常の検出
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — LINE push 通知
    - monitoring_engine.py    — 各 Monitor を束ねる
    - streamlit_dashboard.py  — Streamlit ダッシュボード（読み取り専用）

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数算出・ロット丸め・集約制限
    - risk_adjustment.py      — セクター制限・レジーム乗数

  - research/
    - factor_research.py      — momentum/value/volatility 等ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ等

  - ai/
    - news_nlp.py             — ニュースをまとめて OpenAI でセンチメント化し ai_scores に書込
    - regime_detector.py      — ETF MA200 とマクロニュースで市場レジーム判定

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト

  - utils/
    - process_priority.py     — プロセス優先度 & CPU affinity 設定
    - その他ユーティリティ

データベーススキーマ（監視 DB の概要）
-----------------------------------
init_monitoring_db により自動で作成される主なテーブル：
- system_status(cpu_percent, memory_percent, disk_percent, process_ok, recorded_at)
- trade_logs(logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions(code, qty, avg_price, current_price, updated_at)
- risk_logs(logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard(id=1 固定, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

貢献・開発
----------
- コードを読みながらユニットテストや CI を追加してください（現在の配布ではテストファイルは含まれていません）。
- .env.example をルートに置き、必要な環境変数のテンプレートを提供すると導入が容易になります。

補足
----
- 多くの関数は「フェイルセーフ（例外を上げずにログ／フォールバックする）」設計になっています。プロダクションでの安定稼働を優先した実装ポリシーです。
- OpenAI を用いる部分は API コールに依存するため、キー・レート制限・コストの管理に注意してください。

以上が主要な使い方と構成の説明です。セットアップや起動で不明点があれば、利用する環境（OS・Python バージョン・インストールしたパッケージ）を添えて質問してください。