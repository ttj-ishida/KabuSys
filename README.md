KabuSys — README (日本語)
========================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量ライブラリ群です。  
主要コンポーネントとして、ファクター計算・ポートフォリオ構築・ポジションサイジング・実行エンジン・監視ダッシュボード・AI（ニュースのセンチメント）評価などを含みます。  
設計方針として「DB（DuckDB / SQLite）や外部サービスと分離された純粋関数」「ルックアヘッドバイアスに配慮した日時処理」「フェイルセーフな外部API呼び出し（リトライ・フォールバック）」を重視しています。

主な機能
--------
- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数が優先）
  - 必須環境変数チェック（Settings クラス）
- ポートフォリオ構築
  - シグナル選定（スコアベースのソーティング）
  - 等金額配分 / スコア加重 / リスクベースのポジションサイズ計算
  - セクター集中制限・レジーム乗数適用
- リサーチ（DuckDB 参照）
  - モメンタム / ボラティリティ / バリューなどファクター算出
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント評価して ai_scores に書き込む処理（バッチ・リトライ・バリデーション）
  - マクロニュースと ETF（1321）の MA を組み合わせた市場レジーム判定・DB書き込み
- 実行（Execution）
  - OrderManager / OrderRepository を組み合わせた注文状態管理（クラッシュ耐性を考慮）
  - ExecutionEngine: シグナル処理（Gate チェック）と WebSocket push ドレインループ
  - Reconciler: 起動時の注文・ポジション自動リコンシリエーション
- 監視
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE Push）
  - Streamlit ベースの監視ダッシュボード

セットアップ
-----------
前提
- Python 3.9+（typing の一部機能や pathlib を想定）
- 仮想環境推奨

1. リポジトリをチェックアウト
   - 例: git clone ... && cd repo

2. 仮想環境作成・依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install --upgrade pip
   - pip install duckdb openai requests psutil streamlit

   必要に応じてプロジェクトの requirements.txt / pyproject.toml を参照してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env を置くと自動読み込みされます。
   - 自動読み込みは OS 環境変数 > .env.local > .env の優先順位です。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

代表的な環境変数（例）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合、必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (監視通知用・任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等

例 .env
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

初期 DB 作成（監視 DB）
- Python から:
  from pathlib import Path
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()

使い方（代表例）
----------------

1) 設定値取得
- settings オブジェクトを使って環境設定へアクセスできます。
  from kabusys.config import settings
  duckdb_path = settings.duckdb_path
  log_level = settings.log_level

2) リサーチ（DuckDB）: モメンタム計算
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, date(2026, 3, 20))
  # result は [{ "date": ..., "code": "1234", "mom_1m": ..., ...}, ...]

3) AI ニューススコア（DuckDB + OpenAI）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
  written = score_news(conn, date(2026, 3, 20), api_key=None)

  戻り値: 書き込んだ銘柄数（int）

4) レジーム判定（AI + ETF）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20))  # DB に market_regime を書き込む

5) ポートフォリオ構築 / ポジションサイズ
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [{"code":"1234","signal_rank":1,"score":0.8}, ...]
  cands = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(cands)
  sizes = calc_position_sizes(weights, cands, portfolio_value=10_000_000,
                              available_cash=7_000_000,
                              current_positions={}, open_prices={"1234":1200.0})

6) 監視ダッシュボード（Streamlit）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

7) 実行エンジン（概念）
  ExecutionEngine は BrokerAPIProtocol を実装したブローカークライアント、
  OrderRepository（SQLite 実装）、RiskManager 等を渡して起動します。実際の運用では以下を準備してください：
  - BrokerAPIProtocol 実装（kabu station クライアント等）
  - orders DB（OrderRepository 用の SQLite）
  - duckdb 接続（市場データ / signals / portfolio_targets 等）
  - RiskManager の実装
  - Reconciler（あれば起動時リコンシリエーションが行われます）
  実行例（概略）:
    engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, config)
    engine.run_session()

注意点 / 実装上のポイント
-----------------------
- .env 読み込み:
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基に行います。プロジェクトルートが特定できない場合は自動ロードをスキップします。
  - ロード順: OS 環境変数（保護） > .env（未定義のキーのみセット） > .env.local（上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト向け）。
- AI 呼び出し:
  - OpenAI API 呼び出しはリトライやバリデーションを行い、失敗時はフォールバック（例: macro_sentiment=0）します。APIキーは OPENAI_API_KEY を利用。
- DB 書き込み:
  - ai_scores / market_regime 等は部分更新（該当コードのみ DELETE → INSERT）で冪等性と部分失敗時の保護を考慮しています。
- 実行安全性:
  - OrderManager / ExecutionEngine にはクラッシュ耐性（OrderSent の二相永続化・Reconciler による復旧）が組み込まれています。
- 標準ライブラリ依存を優先する実装方針（外部 lib を減らす）が一部の research モジュール設計に反映されています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                - パッケージ定義（__version__ 等）
- config.py                  - 環境変数・設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py              - ニュースの LLM スコアリング & ai_scores 書き込み
  - regime_detector.py       - 市場レジーム判定（MA200 + マクロセンチメント）
- portfolio/
  - __init__.py
  - portfolio_builder.py     - 候補選定・重み算出
  - position_sizing.py       - 株数決定・スケール調整
  - risk_adjustment.py       - セクターキャップ・レジーム乗数
- research/
  - __init__.py
  - factor_research.py       - momentum/value/volatility 等ファクター算出
  - feature_exploration.py   - 将来リターン・IC・統計サマリー
- monitoring/
  - __init__.py
  - monitoring_db.py         - SQLite スキーマ + MonitoringDB ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py            - ブローカー API 型・例外・データモデル
  - order_manager.py         - 注文の状態遷移管理（OrderManager）
  - reconciler.py            - 起動時の自動リコンシリエーション
  - execution_engine.py      - Signal Queue Pull 型発注エンジン
  - ... (order_repository / order_record 等は別ファイルで実装想定)

ライセンス
----------
（この README には記載されていません。リポジトリの LICENSE ファイルを参照してください。）

フィードバック / 貢献
--------------------
バグ報告や提案は Issue を作成してください。設計思想（ルックアヘッド防止・フェイルセーフ性・DB冪等化）を踏まえた変更提案を歓迎します。

以上。必要であれば、README に含めるサンプル .env.example や具体的な起動スクリプト、よく使うユーティリティ（DuckDB / SQLite の初期化スクリプト）を追加で作成します。どの情報を追加したいか教えてください。