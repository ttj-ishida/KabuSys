README — KabuSys (日本株自動売買基盤)
=================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視基盤の軽量実装です。  
主な目的はアルゴリズム取引のコアロジック（ポートフォリオ構築、ポジションサイジング、リスク制御、
ファクター計算、ニュース NLP によるセンチメント評価、監視・アラート、発注エンジン）を
モジュール化して提供することです。データ永続化には DuckDB（時系列／研究データ）と
SQLite（監視ログ / OrdersDB 等）を使用します。外部 API には kabuステーション（発注）、
OpenAI（ニュース / マクロ NLP）などを想定していますが、クライアントは Protocol で抽象化されています。

特徴（機能一覧）
----------------
- 設定管理
  - .env / .env.local または環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須変数に未設定時は明示的なエラーを出力

- ポートフォリオ構築
  - シグナル選別（スコア降順、タイブレーク処理）
  - 等金額・スコア加重による重み計算
  - セクター集中制限（セクターキャップ適用）
  - レジームに応じた投下乗数（bull/neutral/bear）

- ポジションサイジング
  - リスクベース／等配分／スコア配分の株数決定
  - 単元（lot）丸め、最大ポジション比率・投下比率・手数料バッファの考慮
  - aggregate cap（現金上限）に基づくスケーリング

- リサーチ / ファクター計算
  - Momentum（1M/3M/6M、MA200乖離）
  - Volatility（ATR20、出来高指標、平均売買代金）
  - Value（PER・ROE：raw_financials 参照）
  - 将来リターン計算、IC（Spearman）や統計サマリー

- ニュース & マクロ NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に送信しセンチメント（ai_score）を計算・DBへ書込
  - マクロニュースを評価して市場レジーム（bull/neutral/bear）を判定
  - API エラー（429/タイムアウト/5xx）に対する指数バックオフ・リトライ実装
  - スコアのバリデーション・クリップ（±1.0）や部分失敗時の DB 保護

- 監視（Monitoring）
  - system/trade/risk モニタリング（CPU, メモリ, ディスク, 注文滞留, 約定異常, ドローダウン等）
  - SQLite ベースの永続化（MonitoringDB + 初期化スクリプト）
  - LINE へのプッシュ通知（AlertManager）
  - kill.flag による ExecutionEngine の安全停止
  - Streamlit ベースの監視ダッシュボード（read-only 接続）

- 発注エンジン / 実行系
  - ExecutionEngine：シグナルの読み取り → Gate チェック → 発注（OrderManager） → WebSocket ドレイン
  - OrderManager：DB トランザクションに配慮した二相的永続化（OrderSent の扱い等）
  - Reconciler：起動時の自動復旧（OrderSent 状態の突合・ポジション差分検出）
  - BrokerAPI は Protocol で抽象化（テスト用にモック可能）

セットアップ（開発環境向け）
--------------------------
前提
- Python 3.10+（PEP 604 の '|' 型注釈を使用）
- 仮想環境推奨（venv, pyenv-virtualenv 等）

1) 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 必要パッケージのインストール（例）
   pip install duckdb openai requests psutil streamlit

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用）

3) 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml を起点）に .env/.env.local を置くと自動読み込みされます。
   自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 .env（最低限の項目）
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   その他の設定キー（参考）
   - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
   - PAPER_FILL_MODE (instant|partial|never|reject)
   - PAPER_TRADING_SQLITE_PATH
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

4) MonitoringDB 初期化（SQLite file の作成）
   Python REPL やスクリプトで:
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)

使い方（主な呼び出し例）
-----------------------

- 設定を参照する
  from kabusys.config import settings
  print(settings.duckdb_path)   # Path オブジェクト
  print(settings.log_level)

- DuckDB を使ったリサーチ関数（例: momentum）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]

- OpenAI を使ったニューススコアリング（ai_scores への書込）
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # または OPENAI_API_KEY 環境変数

- 市場レジーム判定（score_regime）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="...")

- MonitoringEngine（単発実行例 / テスト）
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
  import sqlite3, duckdb
  conn = sqlite3.connect("data/monitoring.db")
  duck = duckdb.connect("data/kabusys.duckdb")
  system = SystemMonitor(conn, duck)
  trade = TradeMonitor(conn, order_repo)   # order_repo は OrderRepository のインスタンス
  risk = RiskMonitor(conn)
  ks = KillSwitch(settings.kill_flag_path)
  am = AlertManager(settings.line_channel_access_token, settings.line_user_id)
  engine = MonitoringEngine(system, trade, risk, interval_sec=60, kill_switch=ks, alert_manager=am)
  engine.run_once()  # テスト用に1回だけ実行

- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine（本番的な流れの概要）
  ExecutionEngine は BrokerAPIProtocol 実装（kabu伝送クライアント等）、OrderRepository、RiskManager、OrderManager、DuckDB 接続を受け取りセッションを実行します。実環境では各インターフェースを実装したクラスを注入して run_session() を呼びます。テスト時はモック実装を渡して個別メソッド（_process_signals(), _drain_push_queue()）を呼ぶ設計になっています。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / .env 読み込み、Settings クラス
- portfolio/
  - __init__.py
  - portfolio_builder.py           — 候補選定、等配分・スコア配分
  - position_sizing.py             — 株数決定、aggregate cap
  - risk_adjustment.py             — セクターキャップ、レジーム乗数
- research/
  - __init__.py
  - factor_research.py             — momentum/volatility/value 計算
  - feature_exploration.py         — 将来リターン、IC、統計サマリー
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント取得 & ai_scores 書込
  - regime_detector.py             — マクロ + MA200 合成でレジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py               — SQLite スキーマ / MonitoringDB クラス
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py                  — Broker API のデータモデル / Protocol / 例外
  - order_manager.py               — 発注の高レベル API、DB 永続化戦略
  - execution_engine.py            — Signal → 発注エンジン
  - reconciler.py                  — 起動時の自動復旧 / 突合
  - (その他 OrderRepository, order_record 等が想定)
- monitoring/、ai/、research/ の他に data/ や strategy/ 等のサブパッケージが想定されています（コード内参照あり）。

設計上の注意点 / 運用メモ
-------------------------
- .env 読み込みはプロジェクトルート（.git または pyproject.toml）から探索します。パッケージ配布後も動作するように __file__ を起点に探索します。
- 自動ロードを無効にしたいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 等の外部 API キーは安全に管理してください。テスト時は API 呼び出し関数をモックできます（モジュール内の _call_openai_api を patch）。
- ExecutionEngine / OrderManager はクラッシュ安全性を考慮した永続化シーケンスを採用しています（OrderSent の扱いなど）。Reconciler による起動時突合は重要です。
- Streamlit ダッシュボードは SQLite を read-only URI で開くことが推奨されます（監視中の DB への影響を抑えるため）。

貢献・開発
----------
- 単体テストは外部依存（kabu/API, OpenAI）をモックして実装してください。各モジュールは純粋関数化されている箇所が多く、ユニットテストが容易です。
- 新機能追加時は DB スキーマ変更に対して init / マイグレーションロジックを追加してください（monitoring_db のようなパターン）。

ライセンス
----------
プロジェクトにライセンスファイルがあればそちらを参照してください（ここでは指定なし）。

お問い合わせ
------------
コードベースに関する質問はソース内のドキュメント文字列（docstring）や各モジュールのログ出力を参照してください。具体的なテスト／実行例が必要であれば実行シナリオ（例: ダッシュボード起動、ニューススコアリング、ExecutionEngine のモック実行）を提示します。