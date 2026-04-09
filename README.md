KabuSys — 日本株自動売買フレームワーク
=================================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
ポートフォリオ構築、リスク調整、株数決定、注文管理・再同期、監視・アラート、ニュースの自然言語処理（LLM を用いたセンチメント評価）など、実運用に向けたコンポーネントを純粋関数／副作用分離の設計で提供します。DuckDB / SQLite をデータ層に利用し、外部 API（kabu station / OpenAI / LINE）との連携を想定しています。

主な機能
--------
- 環境変数 / .env 読み込みと設定管理（kabusys.config.Settings）
  - 自動でプロジェクトルート（.git または pyproject.toml）を検出し .env / .env.local を読み込む（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効化する環境変数あり。
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定 (select_candidates)
  - 等金額・スコア加重 (calc_equal_weights / calc_score_weights)
  - ポジションサイズ算出（等配分 / スコア / リスクベース）(calc_position_sizes)
  - セクターキャップ適用、レジーム乗数 (apply_sector_cap / calc_regime_multiplier)
- ファクター計算・リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）に問い合わせ、銘柄ごとにセンチメントスコアを ai_scores テーブルへ登録
  - バッチ、リトライ、レスポンス検証、スコアクリップ等の実装あり
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 とマクロニュース LLM センチメントを合成して daily の regime を判定・保存
- 監視エンジン（kabusys.monitoring）
  - System / Trade / Risk モニタ、監視 DB（SQLite）への永続化、LINE 通知（AlertManager）、kill.flag による停止シグナル、Streamlit ダッシュボード
- 実行エンジン（kabusys.execution）
  - Signal Queue を取り出して発注、push ドレイン、OrderManager / OrderRepository による状態遷移、起動時リコンシリエーション（Reconciler）、Gate ベースのリスクチェック、PID / kill.flag 管理

セットアップ
-----------
前提
- Python 3.10+（注: typing 機能や型注釈に依存）
- 仮想環境の利用を推奨

依存パッケージ（最低限）
- duckdb
- openai
- requests
- psutil
- streamlit (ダッシュボード利用時)
- （標準ライブラリ）sqlite3, logging, json, datetime, 等

インストール例（pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb openai requests psutil streamlit

環境変数 / .env
- プロジェクトでは環境変数で多くの設定を渡します。主なキー:
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring）ファイルパス（デフォルト: data/monitoring.db）
  - PAPER_FILL_MODE — Paper Trading の fill_mode（instant/partial/never/reject）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite
  - PID_FILE_PATH — 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag ファイルパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に既存 kill.flag を自動消去する場合 "1"
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
  - KABUSYS_ENV — development | paper_trading | live
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを止める ("1")
- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主な利用例）
--------------------

1) 設定を利用する
- Python コード内で settings をインポートして使用します。
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path 等

2) 監視 DB の初期化
- SQLite 接続を開いてスキーマを作成します（初回のみ）。
  - import sqlite3
    from kabusys.monitoring.monitoring_db import init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

3) Streamlit ダッシュボード起動
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) ニュース NLP（AI スコアリング）の実行例
- DuckDB 接続を渡して指定日分のニューススコアを ai_scores テーブルへ書き込みます。
  - import duckdb, datetime
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, datetime.date(2026, 3, 20), api_key="sk-xxxx")
    print(f"wrote {n} scores")

  - api_key を None にすると環境変数 OPENAI_API_KEY が使用されます。
  - OpenAI 呼び出し失敗時はフェイルセーフでスコアを 0 にするか該当チャンクをスキップします。

5) 市場レジーム判定の実行
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)

6) 実行エンジン（ExecutionEngine）
- 実際の発注ルーティンを動かすための高レベル API。Broker API 実装、OrderRepository、RiskManager 等を組み合わせてインスタンス化し run_session() を呼びます。PID / kill.flag の取り扱い、起動時のリコンシリエーション、WebSocket push ドレインなどを含む。

注意点・運用上のポイント
-----------------------
- kill.flag 機構:
  - KillSwitch はファイル（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 でなければ起動を拒否します。
- PID ファイル:
  - ExecutionEngine は起動時に PID を出力し終了時に削除します。PID ファイルが不正または stale な場合は自動削除して警告を出します。
- DuckDB / SQLite:
  - DuckDB はファクター計算やリサーチで参照される prices_daily / raw_financials 等のテーブルを格納します。
  - monitoring DB（SQLite）は監視系の永続化に使用します。
- OpenAI 呼び出し:
  - rate limit / network error / 5xx などに対して指数バックオフをとり、最大リトライ回数に達すると該当チャンクをスキップするなどのフェイルセーフが組み込まれています。
- テスト性:
  - OpenAI 呼び出しは _call_openai_api をモジュール内で抽象化しており、テスト時は unittest.mock.patch で差し替えることを想定しています。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env 読み込みと Settings
  - portfolio/
    - portfolio_builder.py — 候補選定、配分重み
    - position_sizing.py — 株数計算、スケールダウン
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン、IC、summary
  - ai/
    - news_nlp.py — ニュース集約 → OpenAI → ai_scores 書込み
    - regime_detector.py — MA200 + マクロ NLU によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各モニタ
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 全モニタのポーリングとアラート連携
    - streamlit_dashboard.py — Streamlit ベースの監視 UI
  - execution/
    - broker_api.py — Broker API 型定義 / Protocol / 例外
    - order_manager.py — 注文ステートマシン外向き API
    - reconciler.py — 起動時リコンシリエーション
    - execution_engine.py — Signal Queue ベースの発注エンジン
    - （その他）order_repository.py, order_record.py, risk_manager.py 等（ファイルは同階層に存在すると想定）
  - monitoring/（上記）
  - その他モジュール: data パイプラインや stats ユーティリティ等（コードベースに依存）

貢献・拡張ポイント
------------------
- 単元株（lot_size）を銘柄毎に扱う拡張（現状はグローバル lot_size）
- price のフォールバック（前日終値/取得原価）を用いたエクスポージャーの過小評価対応
- ファクター追加・Z スコア正規化の改善
- BrokerAPI の具象実装（kabu station クライアント）およびテスト用モックの整備
- 運用向けのコマンドラインツール / systemd / コンテナ化の導入

ライセンス
----------
（ここにプロジェクトのライセンス情報を記載してください）

サンプル .env（例）
------------------
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

最後に
-----
この README はコードベースの主要設計・使い方の要点をまとめたものです。各モジュールの詳細な仕様やパラメータは該当ソースの docstring を参照してください。質問や補足があれば用途に合わせて README を拡張します。