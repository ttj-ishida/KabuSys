KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python 製ライブラリ兼実行フレームワークです。本リポジトリには以下の主要機能を持つコンポーネントが実装されています。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由での発注、リスク管理、リコンシリエーション
- 監視（Monitoring）: システム稼働状況・データ鮮度・注文滞留・リスク監視、LINE プッシュ通知、kill.flag による停止シグナル
- ポートフォリオ構築: 候補選定、配分重み計算、ポジション決定ロジック（単元丸め・リスク制限）
- リサーチ: ファクター計算（モメンタム / ボラティリティ / バリュー）、特徴量解析（IC 等）
- AI 補助: ニュースの NLP センチメント（OpenAI）、市場レジーム判定（MA + LLM）
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード
- 設定管理: .env / 環境変数読み込み、環境モード切替（development / paper_trading / live）

主な機能一覧
-------------
- Settings（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）
  - 各種環境変数のラップ（DB パス、API トークン、閾値など）
- Execution（kabusys.execution）
  - Broker 抽象化、OrderManager、RiskManager、Reconciler（再起動時同期）
  - paper_trading モードでは MockBroker を使用し DB を分離
- Monitoring（kabusys.monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite に監視ログを永続化（スキーマ初期化・簡易マイグレーション対応）
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - KillSwitch: data/kill.flag 書込みで ExecutionEngine 停止を通知
  - streamlit_dashboard: 監視結果の可視化（read-only 接続）
- Portfolio（kabusys.portfolio）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（kabusys.research）
  - DuckDB を使ったファクター計算・将来リターン・IC 計算・統計サマリ
- AI（kabusys.ai）
  - news_nlp: OpenAI でニュースを銘柄ごとにスコアリング
  - regime_detector: ETF MA とマクロセンチメントでレジーム判定
- ユーティリティ
  - process_priority/set_cpu_affinity（psutil を用いたプロセス優先度・CPU affinity 設定）

必要要件
--------
- Python: 3.10 以上（typing の Union 演算子（|）使用のため）
- 主な Python ライブラリ:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（LINE / OpenAI / ブローカー API 利用時）

環境変数（主なもの）
--------------------
（Settings クラスや各モジュールの docstring を参照）
- KABUSYS_ENV: launch mode（development / paper_trading / live）
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須箇所で参照）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒・デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読込を無効化

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロダクション向けに requirements.txt があればそれを利用）
4. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
5. データディレクトリ作成（必要なら）
   - mkdir -p data

起動 / 使い方
------------
- 監視ループを起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path（本番 DB）を常に参照するため、環境にかかわらず同じ監視 DB を使います

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます
  - 起動時にプロセス優先度を High に設定しようとします（権限不足なら警告ログ）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only URI で開いてダッシュボード表示します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能）

- AI モジュール（プログラム呼び出し）
  - 例: ニューススコアを生成して ai_scores に書き込む
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

自動設定読み込み挙動
-------------------
- デフォルトでプロジェクトルート（.git または pyproject.toml を探索）を起点に .env を読み込みます
- 読み込み順序:
  - OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

注意事項 / 実運用メモ
-------------------
- process_priority / set_cpu_affinity は OS と権限に依存し、設定に失敗した場合は警告ログを出してスキップします
- OpenAI / LINE / ブローカー API を使う操作はそれぞれの API キーや接続先設定が必要です
- MonitoringDB の init_monitoring_db は冪等であり、起動時にスキーマの初期化・簡易マイグレーション（peak_value, latency_ms カラム追加）を行います
- KillSwitch は data/kill.flag を作成して ExecutionEngine の停止を指示します。既存ファイルがある場合は上書きしません
- Paper Trading モードは本番 DB と分離する設計です。実際のブローカー接続や本番資金でのテストは慎重に行ってください

主要ディレクトリ構成
-------------------
（抜粋: src/kabusys 以下）
- __init__.py
- config.py
  - Settings クラス (.env 自動読み込み・各種設定ラッパー)
- run_monitoring.py
- run_execution.py

- ai/
  - news_nlp.py        # ニュースセンチメント（OpenAI）と ai_scores 書込
  - regime_detector.py # MA + LLM による日次レジーム判定

- monitoring/
  - monitoring_db.py   # SQLite スキーマ & MonitoringDB クラス
  - system_monitor.py  # CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py   # 注文滞留 / 約定異常監視
  - risk_monitor.py    # ドローダウン / ポジション上限監視
  - kill_switch.py     # kill.flag 書込みロジック
  - alert_manager.py   # LINE 通知
  - monitoring_engine.py
  - streamlit_dashboard.py

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - execution_engine.py
  - broker_factory.py
  - broker_api.py
  - order_record.py
  - (その他ブローカー関連)

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py        # calc_momentum / calc_volatility / calc_value
  - feature_exploration.py    # forward returns / IC / summary

- data/
  - pipeline.py, stats.py (DuckDB 関連ユーティリティ: prices_daily, raw_financials などを参照)

- tools/
  - paper_verification_report.py

利用例（簡単なコードスニペット）
--------------------------------
- ファクター計算（Research API）
  - from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    conn = duckdb.connect("data/kabusys.duckdb")
    target = date(2026, 4, 10)
    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    val = calc_value(conn, target)

- ポートフォリオ構築（メモリ内演算）
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_score_weights(candidates)
    sizes = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=10_000_000, ...)

貢献 / 開発
-----------
- 新しい機能追加やバグ修正の際はユニットテストと簡単な動作確認を追加してください
- .env.example を用意して主要な環境変数のサンプルを示すことを推奨します

ライセンス
---------
- 本 README では明示していません。リポジトリルートの LICENSE を確認してください。

以上がリポジトリの主要な概要・セットアップ・使い方のまとめです。必要であれば README に含める環境変数の完全リストや実行時ログ例、運用手順（systemd / supervisor 用の起動スクリプト例）を追加できます。どの情報を追記したいか教えてください。