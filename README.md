KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のためのライブラリ群です。
主に以下の機能群を提供します。

- ポートフォリオ構築（銘柄選定 / 重み付け / 株数計算 / セクター制約）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- ニュースのLLMによるセンチメント評価（OpenAI API 経由）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 注文管理・実行エンジン（OrderManager / ExecutionEngine）
- 再起動時のリコンシリエーション（Reconciler）
- 監視（System / Trade / Risk）・アラート（LINE 経由）・ダッシュボード（Streamlit）
- 永続化層（DuckDB / SQLite）との連携ユーティリティ

設計方針の要点
- 多くのコア関数は純粋関数（DBに依存しない）で、テストしやすい設計
- DuckDB を主要な分析 DB として使用
- OpenAI（gpt-4o-mini）を用いたニュース/マクロセンチメント評価（APIキー必須）
- 自動的に .env / .env.local をプロジェクトルートから読み込む仕組みを提供

主な機能一覧
- portfolio
  - select_candidates, calc_equal_weights, calc_score_weights（候補選定・配分）
  - calc_position_sizes（株数決定・資金制約・lot 切り捨て・スケーリング）
  - apply_sector_cap（セクター集中抑制）, calc_regime_multiplier（レジーム乗数）
- research
  - calc_momentum, calc_volatility, calc_value（DuckDB 経由でファクター計算）
  - calc_forward_returns, calc_ic, factor_summary（特徴量評価）
- ai
  - score_news（ニュース記事の銘柄別センチメント取得・ai_scores 書込み）
  - score_regime（市場レジーム判定・market_regime テーブルへの書込み）
- execution
  - ExecutionEngine（シグナル処理 / push drain / kill switch）
  - OrderManager（注文状態遷移・送信・同期・キャンセル）
  - Reconciler（起動時の注文・ポジション突合）
  - broker_api（API 用データモデル・Protocol・例外クラス）
- monitoring
  - MonitoringDB（SQLite ベースの監視ログ永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor（監視ロジック）
  - AlertManager（LINE Push 通知）
  - KillSwitch（ファイルによる停止指示）
  - streamlit_dashboard（監視用ダッシュボード）
- config
  - 環境変数を集約した Settings オブジェクト（.env 自動ロード）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 演算子などを使用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
  - sqlite3 （標準ライブラリ）
  - その他、プロジェクトで要求されるパッケージ

例: 仮想環境作成とパッケージインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt がある場合）
   - pip install -r requirements.txt
   ない場合は最低限:
   - pip install duckdb openai requests psutil streamlit

3. パッケージをインストール（編集可能モード）
   - pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を含む場所）にある .env / .env.local を自動読み込みします。
- 自動ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- 主な環境変数（Settings で参照／デフォルトを示すもの）:
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime で使用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager 用
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_FILL_MODE (default "instant") — paper trading の fill モード（instant/partial/never/reject）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時 kill.flag を自動でクリアするか
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 閾値
  - KABUSYS_ENV (development | paper_trading | live), LOG_LEVEL (DEBUG|INFO|...)
- 必須の設定が欠けると Settings のプロパティで ValueError が発生します。

監視 DB の初期化（SQLite）
例: data/monitoring.db を作成してテーブルを準備する
- python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"

DuckDB（分析 DB）
- DuckDB ファイル（デフォルト data/kabusys.duckdb）に以下のようなテーブルが想定されます（コード参照）:
  - prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets, …など
- これらは外部スクリプトや ETL で準備してください（本リポジトリはデータ収集パイプライン実装を含みません）。

使い方（代表例）
----------------

1) ファクター計算（research）
- DuckDB 接続を作成して呼び出す例:
  - from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, date(2026, 3, 20))

2) ニュースセンチメント（AI）
- OPENAI_API_KEY を設定して実行:
  - from datetime import date
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # 書き込み件数を返す

3) 市場レジーム判定
- from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

4) 監視ダッシュボード（Streamlit）
- Streamlit をインストールした上で:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5) 監視エンジン（プログラム的に）
- SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine を組み合わせて利用可能です。
- 例（簡略）:
  - from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, MonitoringDB, init_monitoring_db
  - (各種コネクションと依存オブジェクトを準備して) engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor); engine.run()

6) 注文実行（ExecutionEngine）
- ExecutionEngine は BrokerAPIProtocol 実装（kabu station client 等）、OrderRepository（SQLite 実装）、RiskManager 等の実体が必要です。実運用時はそれらの実装を組み合わせてインスタンスを生成し run_session() を呼び出します。
- 起動時には kill.flag の取り扱いや PID ファイル書き込みを行います（設定は Settings を参照）。

ファイル・ディレクトリ構成
------------------------
主要なファイル・パッケージ（src/kabusys 以下）
- __init__.py
  - バージョン・パッケージ公開
- config.py
  - .env 自動読み込み・環境設定の集約（Settings オブジェクト）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・資金・lot制約
  - risk_adjustment.py — セクターキャップ、レジーム乗数
  - __init__.py
- research/
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー
  - __init__.py
- ai/
  - news_nlp.py — raw_news を LLM でスコアリングして ai_scores 書き込み
  - regime_detector.py — ma200 とマクロニュースの LLM 結果を合成して market_regime 書き込み
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義と MonitoringDB ラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 監視ロジック
  - alert_manager.py — LINE Push
  - kill_switch.py — ファイルフラグによる強制停止
  - monitoring_engine.py — 各監視を束ねるポーリングエンジン
  - streamlit_dashboard.py — 監視用 Streamlit UI
  - __init__.py
- execution/
  - execution_engine.py — Signal Queue 型の発注エンジン
  - order_manager.py — 注文状態遷移と送信フロー
  - reconciler.py — 再起動時リコンシリエーション
  - broker_api.py — Broker 用データモデル・Protocol・例外
  - （その他 OrderRepository / order_record 等は別ファイルに存在する想定）
- その他
  - monitoring/ や ai/ で使用する DuckDB / SQLite のテーブルに依存する処理が多数あります。データスキーマはコード内の SQL を参照してください。

注意点 / 運用上のヒント
- OpenAI API 用キーは機密情報なので .env.local 等で管理してください。
- score_news/score_regime は API 呼び出し失敗時フェイルセーフでスキップまたはフォールバック（0.0）する設計ですが、API レート制限・料金には注意してください。
- ExecutionEngine は実ブローカーと結合する部分が多く、まずはモックの BrokerAPIProtocol 実装でローカル検証（paper_trading）することを推奨します。
- kill.flag による外部停止と PID ファイルによる二重起動防止に対応しています。CI / 自動化環境では KILL_FLAG_CLEAR_ON_START の設定に注意してください。
- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。

開発 / テスト
--------------
- 多くの関数が純粋関数（外部副作用なし）で設計されているためユニットテストが書きやすくなっています。OpenAI 呼び出し部分は _call_openai_api をモックすることでテスト可能です。
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境で便利）。

サンプルスニペット（calc_momentum）
- import duckdb
  from datetime import date
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026,3,20))
  print(len(res), res[:3])

最後に
------
この README はコードベースの主要機能・利用方法をまとめたものです。各機能の詳細やテーブルスキーマ、ブローカー実装・OrderRepository 実装はソースコード内の docstring / SQL を参照してください。追加のセットアップ手順（データ投入スクリプト、broker クライアント）は別途用意してください。