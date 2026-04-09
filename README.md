KabuSys — README（日本語）
==========================

プロジェクト概要
----------------
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ライブラリ／システムのコア実装です。  
主に以下の領域をカバーします。

- ファクター計算・リサーチ（DuckDB 上の時系列データに対するファクター計算）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制約）
- 実行エンジン（Signal Queue からの発注、WebSocket push ドレイン、リコンシリエーション）
- ブローカー抽象（Protocol による Broker API インターフェース）
- AI 統合（ニュースの NLP によるセンチメント評価、レジーム判定）
- 監視・アラート（システム状態・注文滞留・リスク監視、LINE 通知、Streamlit ダッシュボード）
- 監視ログ永続化（SQLite ベースの MonitoringDB）

主な機能一覧
-------------
- 環境設定管理（.env 読み込み、自動ロード、settings オブジェクト）
- ポートフォリオ構築
  - 候補選定（スコア順）select_candidates
  - 重み計算（等金額 / スコア加重）calc_equal_weights / calc_score_weights
  - ポジションサイズ算出（risk_based / equal / score）calc_position_sizes
  - セクター上限適用 apply_sector_cap
  - レジームに応じた投下資金乗数 calc_regime_multiplier
- リサーチ / ファクター計算（DuckDB を入力）
  - Momentum / Volatility / Value ファクター calc_momentum / calc_volatility / calc_value
  - 将来リターン、IC、統計サマリ（calc_forward_returns / calc_ic / factor_summary）
- AI 機能
  - ニュースのセンチメントスコアリング（OpenAI を用いる）score_news
  - 市場レジーム判定（ETF MA + マクロセンチメント）score_regime
  - 両モジュールは OpenAI API キー必須（フォールバック動作あり）
- 実行（ExecutionEngine）、OrderManager、Reconciler による堅牢な発注フロー
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、AlertManager（LINE）
  - MonitoringDB（SQLite）でログ保管、Streamlit ダッシュボード表示

前提／要件
----------
- Python 3.10+（型注釈に Union | などを利用）
- 必要ライブラリ（代表例）:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit（ダッシュボードを使う場合）
- 実運用時はブローカー実装（BrokerAPIProtocol 準拠）を提供する必要があります。

セットアップ手順（ローカル開発向け）
-----------------------------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux) または .venv\Scripts\activate (Windows)

2. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 直接必要ライブラリを入れる場合:
     - pip install duckdb openai psutil requests streamlit

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

4. データディレクトリ作成
   - mkdir -p data

環境変数 / .env
----------------
設定は環境変数またはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に置かれた .env / .env.local で読み込まれます。
自動ロードの挙動:
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途）
- .env のパースは export KEY=val、クォート、インラインコメント等に対応します

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabu ステーション API）
- OPENAI_API_KEY — 任意（AI 機能を使用する場合必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 任意（監視アラート送信用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH — Paper Trading 設定
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行管理用
- KABUSYS_ENV — environment ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

使い方（ライブラリの主な呼び出し例）
---------------------------------

設定参照
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.kabu_api_base_url などを参照

ポートフォリオ
- 候補選定:
  - from kabusys.portfolio import select_candidates
  - select_candidates(buy_signals, max_positions=10)
- 重み計算:
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
- ポジションサイズ:
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method="risk_based")

リサーチ / ファクター計算（DuckDB 接続が必要）
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")
- from kabusys.research import calc_momentum, calc_volatility, calc_value
- results = calc_momentum(conn, target_date)

AI（ニュース NLP / レジーム）
- OpenAI API キーを環境変数か引数で渡す
- from kabusys.ai import score_news
- written = score_news(conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))

監視 DB 初期化
- Python スクリプトで実行:
  - import sqlite3
  - from kabusys.monitoring import init_monitoring_db
  - conn = sqlite3.connect("data/monitoring.db")
  - init_monitoring_db(conn)

Streamlit ダッシュボード
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

MonitoringEngine（監視ループ）利用例
- SystemMonitor / TradeMonitor / RiskMonitor 等を組み合わせて MonitoringEngine を作成し run() または run_once() を呼ぶ

ExecutionEngine（発注セッション）
- 実行には BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続等が必要
- ExecutionEngine.run_session() が本番セッションのエントリポイント
- テスト時は内部の _process_signals(), _drain_push_queue() を直接呼ぶ設計

注意点・設計上の備考
-------------------
- DuckDB / SQLite をデータ層に使用。SQL スキーマ・テーブル（prices_daily, raw_financials, raw_news, ai_scores, market_regime など）に依存します。
- AI（OpenAI）呼び出しはリトライ・バックオフ・レスポンス検証等を実装。API キーの適切な設定が必須です。
- 実行エンジンは kill.flag / PID 管理・リコンシリエーション（再起動後の整合）・フェイルセーフ（API失敗時のスキップ）を考慮した堅牢設計です。
- .env パーサは複雑なクォートやコメント処理に対応しています。自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py                — パッケージ設定、__version__
- config.py                  — 環境変数 / .env 読み込み、settings オブジェクト

portfolio/
- __init__.py
- portfolio_builder.py       — select_candidates, calc_equal_weights, calc_score_weights
- position_sizing.py         — calc_position_sizes
- risk_adjustment.py         — apply_sector_cap, calc_regime_multiplier

research/
- __init__.py
- factor_research.py         — calc_momentum, calc_volatility, calc_value
- feature_exploration.py     — calc_forward_returns, calc_ic, factor_summary, rank

ai/
- __init__.py
- news_nlp.py                — score_news (ニュースの NLP スコアリング)
- regime_detector.py         — score_regime (市場レジーム判定)

monitoring/
- __init__.py
- monitoring_db.py           — MonitoringDB, init_monitoring_db
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- alert_manager.py
- monitoring_engine.py
- streamlit_dashboard.py     — Streamlit ダッシュボード

execution/
- broker_api.py              — Broker API のデータモデル・Protocol・例外
- order_manager.py
- order_repository.py        — (orders DB 操作、別ファイル)
- order_record.py            — OrderRecord, 状態遷移
- execution_engine.py
- reconciler.py
- risk_manager.py            — (リスク管理ロジック、別ファイル)

その他
- data/ (想定される実データ格納ディレクトリ、DuckDB/SQLite ファイル等)

貢献・テスト
-------------
- 単体テストを用意する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを抑止してください。
- OpenAI 呼び出し等外部依存はモック化してテストしてください（モジュール内で置換可能な呼び出し関数が用意されています）。

最後に
------
この README はコードベースの主要機能と利用方法の概要を示しています。実行や運用のためには DB スキーマ準備、BrokerAPI 実装、各種環境変数の設定が必要です。具体的な運用手順や外部依存のバージョン固定（requirements.txt）はプロジェクトルートで管理してください。必要であれば、サンプル .env.example や起動スクリプトを追加することを推奨します。