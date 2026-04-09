KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのライブラリ群／ミニフレームワークです。
主に以下の責務を持つモジュール群で構成されています。

- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ファクター計算・リサーチ（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュースセンチメント、マクロレジーム判定、OpenAI 統合）
- 注文実行エンジン（発注・同期・再コンシリエーション）
- 監視（システム／注文／リスク監視、LINE 通知、Streamlit ダッシュボード）
- 環境設定の読み込み（.env / 環境変数対応）

特徴（機能一覧）
----------------
- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化可能

- ポートフォリオ構築
  - シグナルのスコア降順選定（select_candidates）
  - 等重配分 / スコア加重配分（calc_equal_weights / calc_score_weights）
  - セクター集中制限の適用（apply_sector_cap）
  - レジームに応じた投下資金乗数（calc_regime_multiplier）
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分）（calc_position_sizes）

- リサーチ（DuckDB を前提）
  - モメンタム、ボラティリティ、バリューファクター計算（prices_daily / raw_financials）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ機能

- AI（OpenAI）
  - ニュース記事を LLM でセンチメント化し ai_scores テーブルへ保存（score_news）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（score_regime）
  - API 呼び出しは堅牢なリトライ・バリデーション実装

- 注文実行
  - OrderManager / ExecutionEngine による堅牢な注文フロー（DB 永続化・2相コミット設計）
  - Reconciler による再起動時の自動同期とポジション差分検出
  - Gate チェック（シグナル検査・レート制限・ドローダウン監視）と KillSwitch による安全停止

- 監視・アラート
  - MonitoringDB（SQLite）でのログ永続化
  - RiskMonitor / SystemMonitor / TradeMonitor による定期チェック
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード（read-only 接続）

導入・セットアップ手順
----------------------
以下は一般的な開発環境向けの手順例です。プロジェクトに requirements.txt / pyproject.toml があればそちらに従ってください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージインストール（例）
   - pip install duckdb openai psutil requests streamlit
   - もしプロジェクトがパッケージ化されていれば: pip install -e .

   ※ 実際の依存はプロジェクトの requirements ファイルを参照してください。

4. 環境変数 / .env の準備
   - ルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動読み込みされます。
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY  (AI 機能を使う場合必須)
   - その他（任意／デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|...) — default: INFO
     - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など
   - .env 自動読み込みを無効にする:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 監視 DB 初期化（SQLite）
   - Python REPL / スクリプトで init_monitoring_db を呼ぶ:
     from kabusys.monitoring import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

使い方（主要な API と実行例）
----------------------------
ここでは代表的な利用例を示します。詳細は各モジュールを参照してください。

- 設定を取得する
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path

- DuckDB 接続を作ってリサーチ関数を呼ぶ
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  from kabusys.research import calc_momentum
  res = calc_momentum(conn, date(2026, 3, 20))

- ニュースセンチメントのスコアリング
  import sqlite3, duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  dconn = duckdb.connect(str(settings.duckdb_path))
  sconn = sqlite3.connect(str(settings.sqlite_path))
  # score_news は ai_scores テーブルへ書き込みます
  score_news(dconn, date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

- 市場レジームスコア算出
  from kabusys.ai.regime_detector import score_regime
  score_regime(dconn, date(2026, 3, 20))

- 監視ダッシュボード（Streamlit）
  # コマンドラインから起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine の起動（概要）
  実運用は broker 実装・OrderRepository・RiskManager 等の具象実装が必要です。テスト時はモック broker / repo を用意して以下を呼び出せます。
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
  engine.run_session()

注意点・運用上のポイント
- Kill Switch:
  KillSwitch は kill.flag（settings.kill_flag_path）を作成することで ExecutionEngine に停止シグナルを送ります。起動時に既存の kill.flag があると起動を拒否する挙動（設定でクリア可）です。

- .env パース:
  .env は export KEY=val 形式やクォート・エスケープ・コメント（#）を考慮してパースされます。.env.local は .env を上書き可能（OS 環境変数は保護される）。

- LLM 呼び出しと耐障害性:
  OpenAI 呼び出しは 429 / ネットワーク / 5xx に対して指数バックオフ・リトライを実装しています。API 失敗時はフェイルセーフとしてゼロや既定値で継続する設計です。

- DB 書き込みはトランザクション管理あり:
  ai_scores / market_regime 等のテーブルへの書き込みは冪等性を考慮して DELETE→INSERT や BEGIN/COMMIT を使用します。Rollback や例外時の挙動に注意してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                 — パッケージメタ情報
- config.py                   — 環境変数 / .env 読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py               — ニュースセンチメント（OpenAI 統合）
  - regime_detector.py        — マクロ + MA200 でレジーム判定
- portfolio/
  - __init__.py
  - portfolio_builder.py      — 候補選定・重み計算
  - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - position_sizing.py        — 発注株数決定
- research/
  - __init__.py
  - factor_research.py        — Momentum / Volatility / Value 計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリ
- monitoring/
  - __init__.py
  - monitoring_db.py          — SQLite スキーマ / MonitoringDB
  - risk_monitor.py
  - system_monitor.py
  - trade_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py             — Broker API のデータモデル & Protocol
  - order_manager.py          — 注文状態マシンの外向き API
  - execution_engine.py       — Signal Pull / Push ドレインの実行エンジン
  - reconciler.py             — 再起動時リコンシリエーション
  - (その他: order_repository, order_record, risk_manager など想定)
- research/, portfolio/, monitoring/... といった実装モジュールが上記に分かれています。

補足（環境変数一覧 - 代表）
---------------------------
主要な環境変数（コード中で参照されているもの）:

必須（機能により必須）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY  — AI 機能を使用する場合

任意／デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PID_FILE_PATH — default: data/execution.pid
- KILL_FLAG_PATH — default: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 1 で起動時に既存 kill.flag を自動クリア
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知に使用
- PAPER_FILL_MODE — paper trading の fill 動作 (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB パス

ライセンス / コントリビューション
--------------------------------
README には含まれていません。リポジトリの LICENSE ファイルや CONTRIBUTING 指針を参照してください。

最後に
------
この README はコードベース（src/kabusys/*.py）から読み取れる設計・機能をまとめたものです。実際の運用やビルド手順はプロジェクトの pyproject.toml / requirements.txt / CI 設定に従ってください。追加で CLI、ユーティリティ、または導入手順（systemd ユニット、コンテナ化など）の例が必要であれば教えてください。