KabuSys — 日本株自動売買フレームワーク
==================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視基盤を想定した Python ライブラリです。  
主な機能はシグナルからポートフォリオ構築・発注、モニタリング、ファクター計算、ニュースの NLP スコアリング、再起動時のリコンシリエーションなどを含みます。  
このリポジトリは純粋関数群と永続化層、外部 API（kabu/station, OpenAI）とのインターフェースを分離した設計になっています。

特徴（主な機能）
----------------
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git や pyproject.toml で検出）
  - 必須環境変数チェック
- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 等金額配分／スコア加重配分
  - セクター上限フィルタ（セクター集中制限）
  - レジーム乗数（bull/neutral/bear）
  - 株数決定（risk-based / equal / score）、lot 単位丸め、aggregate cap 調整
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由、prices_daily/raw_financials）
  - 将来リターン計算、IC（Spearman）や基本統計量
- AI（LLM）連携
  - ニュース記事の銘柄別センチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（OpenAI 補助）
  - API エラー時のリトライ・フェイルセーフ設計
- 実行・発注（Execution）
  - Signal Queue からの発注エンジン（ExecutionEngine）
  - OrderManager（状態遷移、二相コミット風設計）と Broker API 抽象化（Protocol）
  - 起動時の Reconciler による自動復旧・ポジション突合
  - リスクゲート（Gate1/2/3）や kill.flag による即時停止
- 監視（Monitoring）
  - SQLite による system / trade / risk / positions / dashboard 永続化
  - RiskMonitor / SystemMonitor / TradeMonitor（ドローダウン・滞留注文・価格異常検知）
  - LINE 通知用 AlertManager（クールダウン管理）
  - Streamlit ダッシュボード（read-only 接続で可視化）

セットアップ手順
----------------
前提:
- Python 3.9+（またはプロジェクトの pyproject.toml に準拠）
- DuckDB, SQLite を利用
- OpenAI を使う機能を使う場合は API キーが必要

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt / pyproject.toml がある想定です。一般的には:
     - pip install -e .      （プロジェクトを開発モードでインストール）
     - pip install duckdb openai requests psutil streamlit

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   - 読み込み順: OS 環境 > .env.local > .env
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知はスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: paper trading の fill mode（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（抜粋）
----------------

1) 設定値にアクセスする（Python）
- 設定は kabusys.config.settings 経由で参照できます。
  - 例: from kabusys.config import settings; print(settings.duckdb_path)

2) DuckDB ベースのファクター計算（研究用途）
- 例:
  - import duckdb
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - records = calc_momentum(conn, target_date)

3) ニュース NLP スコアリング（OpenAI 必須）
- 例（DB 接続を渡して実行）:
  - from kabusys.ai import score_news
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, target_date, api_key="sk-...")

4) 市場レジーム判定（OpenAI 補助）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date, api_key=...)

5) モニタリング DB 初期化（SQLite）
- import sqlite3
- from kabusys.monitoring import init_monitoring_db
- conn = sqlite3.connect("data/monitoring.db")
- init_monitoring_db(conn)

6) Streamlit ダッシュボード起動
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

7) ExecutionEngine（発注セッション）を使う（簡単な流れ）
- 必要なコンポーネント（Broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続、Reconciler）を組み合わせて ExecutionEngine を生成し、run_session() を呼びます。
- ExecutionEngine は PID ファイル管理、kill.flag チェック、WebSocket プッシュ受信のドレイン、発注シグナル処理などを内包します。

注意点 / 運用上のヒント
- .env の自動読み込みはプロジェクトルートを基準に行われます（CWD に依存しない）。
- OpenAI API 呼び出しに失敗した場合、多くの処理はフェイルセーフ（0.0 フォールバックやスキップ）を採っています。ログを確認してください。
- ExecutionEngine は kill.flag を検出したら即座に停止（設定により起動拒否も可能）します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD や KILL_FLAG_CLEAR_ON_START を活用してください。
- プロダクション接続前に MonitoringDB の初期化と DuckDB のデータ品質（prices_daily 等）を確認してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / 設定管理
- __version__ 参照: 0.1.0

サブパッケージ:
- kabusys/portfolio/
  - portfolio_builder.py      — 候補選定 / 重み計算
  - risk_adjustment.py       — セクター制限 / レジーム乗数
  - position_sizing.py       — 株数決定・aggregate cap
  - __init__.py

- kabusys/research/
  - factor_research.py       — Momentum/Volatility/Value 計算
  - feature_exploration.py   — 将来リターン / IC / 統計
  - __init__.py

- kabusys/ai/
  - news_nlp.py              — ニュース記事の LLM ベーススコアリング
  - regime_detector.py       — マクロ + ETF でレジーム判定
  - __init__.py

- kabusys/monitoring/
  - monitoring_db.py         — SQLite スキーマ & CRUD（MonitoringDB）
  - system_monitor.py        — システム・データ鮮度監視
  - trade_monitor.py         — 注文滞留 / 約定異常検知
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - alert_manager.py        — LINE push 通知
  - kill_switch.py          — フラグファイルによる停止
  - monitoring_engine.py    — 各モニタのポーリング（run / run_once）
  - streamlit_dashboard.py  — Streamlit ダッシュボード
  - __init__.py

- kabusys/execution/
  - execution_engine.py     — 発注エンジン（Signal → 発注 / push ドレイン）
  - order_manager.py        — OrderState Machine 外向け API
  - reconciler.py           — 起動時の注文・ポジション照合
  - broker_api.py           — Broker API の Data model / Protocol / 例外
  - ...（他モジュールが連携）

- kabusys/monitoring、/portfolio、/research、/ai、/execution の各 __init__.py は外部公開 API を定義しています。

開発 / テスト
--------------
- 単体関数群は副作用を持たない設計（Pure functions）で実装されている箇所が多く、ユニットテストが書きやすくなっています（DuckDB/SQLite のモック接続を渡してテスト可能）。
- OpenAI 呼び出し部分は _call_openai_api をパッチしてモックしやすい設計です（unittest.mock.patch を利用）。

最後に
------
この README はリポジトリ内のコード構成に基づく概要ガイドです。実行や接続先（kabu API、DuckDB データ、OpenAI）に依存する部分は運用環境に合わせて設定してください。実運用前にローカルでの検証（monitoring DB 初期化、データ鮮度、kill.flag 動作確認、LLM 呼び出しのモック）を強く推奨します。