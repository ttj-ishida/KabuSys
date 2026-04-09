# KabuSys

日本株の自動売買・リサーチ基盤ライブラリ（部分実装）。  
ポートフォリオ構築、ポジションサイズ計算、ファクター計算、ニュースの NLP スコアリング、監視機構、発注エンジン周りのユーティリティ群を含みます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（.env）について
- ディレクトリ構成（ファイル一覧と説明）

---

## プロジェクト概要

KabuSys は日本株を想定した自動売買／リサーチ用の内部ライブラリ群です。  
主な設計方針は以下のとおりです。

- データ解析（DuckDB）・取引ロジック・監視を分離したモジュール構成
- LLM（OpenAI）を用いたニュースセンチメント評価の組み込み
- 発注エンジンはクラッシュ耐性（永続化＋リコンシリエーション）を考慮
- 監視（System / Trade / Risk）と LINE 通知を用いたアラート機能
- 多くの処理は「副作用なし」の純粋関数で実装され、テスト容易性を重視

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local、自動ロード）
- ポートフォリオ構築
  - 候補選定（score降順）
  - 重み計算（等配分 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（risk-based / equal / score）
- リサーチ（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）・統計サマリー
- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメント算出（gpt-4o-mini、JSON Mode）
  - マクロニュース + ETF MA200 を使った市場レジーム判定
  - リトライ・バッチ処理・レスポンス検証を実装
- 監視（SQLite）
  - system_status / trade_logs / positions / risk_logs / dashboard
  - System / Trade / Risk 各種モニタ、kill flag（停止シグナル）、LINE 通知
  - Streamlit ダッシュボード（監視用）
- 発注周り（抽象化された BrokerAPI）
  - Order 管理（OrderManager）、永続化（OrderRepository）、Reconciler
  - ExecutionEngine（Signal Pull / WebSocket push drain、Gate チェック）
  - クラッシュ後の自動リコンシリエーション

---

## セットアップ手順

※以下は推奨手順・必要な主要パッケージの例です。実行環境に合わせて調整してください。

1. Python（推奨 3.10+）の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt があればそれを使ってください）

3. データディレクトリ作成（デフォルト経路）
   - data/ （DuckDB / SQLite / PID / kill.flag 等を格納）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を置くと自動的にロードされます（.env.local は .env の上書き）
   - 主な環境変数（下段の「環境変数について」を参照）

5. 監視用 SQLite DB を初期化（任意）
   - Python REPL で例:
     from sqlite3 import connect
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = connect("data/monitoring.db")
     init_monitoring_db(conn)

6. DuckDB ファイルを用意（データ投入済みの想定）
   - デフォルトパス: data/kabusys.duckdb（Settings.duckdb_path）
   - prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime などのテーブルが利用されます（モジュール参照）

---

## 使い方（代表的な例）

- 設定値の取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token  # 必須項目（未設定だと ValueError）
  ```

- リサーチ（モメンタム計算）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  # res は [{"date": ..., "code": "1234", "mom_1m": ..., ...}, ...]
  ```

- 将来リターン / IC 計算
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_5d")
  ```

- ニュースの AI スコアリング（DuckDB と OpenAI API キー必要）
  ```python
  from kabusys.ai import score_news
  from datetime import date
  import duckdb, os

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか OPENAI_API_KEY 環境変数を設定
  written = score_news(conn, date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（AI + ETF MA200）
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
  ```

- 監視ダッシュボード起動（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- 監視 DB 初期化（上記参照）
  ```python
  from sqlite3 import connect
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = connect("data/monitoring.db")
  init_monitoring_db(conn)
  ```

- ExecutionEngine や OrderManager を使った発注は、BrokerAPI 実装（protocol 準拠）と OrderRepository（SQLite）を組み合わせて使用します。実運用では Broker の具象クライアントを注入してください。

---

## 環境変数（.env）について

モジュール起動時にプロジェクトルート（.git または pyproject.toml）を探索し、以下の順で自動ロードします（環境変数が既に存在するキーは保護されます）:

1. OS 環境変数
2. .env.local（存在すれば .env の値を上書き）
3. .env

自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（README 用の代表例）
- JQUANTS_REFRESH_TOKEN — 必須: J-Quants API 用トークン
- KABU_API_PASSWORD — 必須: kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（監視アラート）
- LINE_USER_ID — LINE 送信先ユーザID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading 用の補填モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite DB
- PID_FILE_PATH / KILL_FLAG_PATH — 実行制御ファイルのパス
- KILL_FLAG_CLEAR_ON_START — 起動時に既存 kill.flag を自動クリアする場合は 1 に設定

.env のパースはシェル風のフォーマット（export KEY=val / quoted values / inline comments）に対応しています。

---

## ディレクトリ構成（src/kabusys 以下の主なファイル）

- __init__.py
  - パッケージのメタ情報（__version__）と主要エクスポート

- config.py
  - 環境変数の読み込み / Settings クラス（アプリ設定の取得）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - position_sizing.py: 発注数量計算（calc_position_sizes）
  - risk_adjustment.py: セクターキャップ・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - __init__.py: 便利なエクスポート

- research/
  - factor_research.py: momentum/volatility/value 等のファクター計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー等
  - __init__.py: エクスポート（zscore_normalize 等を含む）

- ai/
  - news_nlp.py: raw_news を OpenAI でスコアリングし ai_scores へ書き込む（score_news）
  - regime_detector.py: ETF MA200 + マクロニュースで市場レジーム判定（score_regime）
  - __init__.py: score_news をエクスポート

- monitoring/
  - monitoring_db.py: SQLite テーブル作成と MonitoringDB ラッパー
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag を扱うユーティリティ
  - alert_manager.py: LINE 通知ラッパー
  - monitoring_engine.py: モニタを束ねるポーリング実行部
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）

- execution/
  - broker_api.py: Broker API のデータモデル・Protocol・例外定義
  - order_manager.py: Order の状態機械を扱う高レベル API
  - reconciler.py: 起動時の自動復旧・リコンシリエーション
  - execution_engine.py: シグナル処理と push ドレインを行うエンジン
  - （OrderRepository / OrderRecord 等の補助モジュールは別ファイルとして存在）

その他の補助モジュールや細かい実装（データパイプライン、stats 等）はソース内に配置されています。

---

## 注意事項 / 運用上のヒント

- OpenAI API を呼ぶ箇所はネットワークや料金に依存します。ローカルテスト時はモック（patch）を使用してください（score_news 内で _call_openai_api を差し替え可能）。
- DuckDB / SQLite のテーブルスキーマはコード内 SQL に記載があるため、データ投入時に合わせてください。
- 発注処理はブローカーの具象実装（BrokerAPIProtocol に準拠）を用意する必要があります。実稼働前に十分なテストを推奨します。
- kill.flag を利用した安全シャットダウン、監視イベントの de-dup（dedup_minutes）等の仕組みを活用してください。

---

この README はソースコードの現在の実装（src/kabusys 以下）を基に作成しています。追加の実行スクリプト・CI・依存関係ファイルがある場合はそれらに従ってください。質問や README の追加項目（例: 詳細な API リファレンス、デプロイ手順）を希望する場合は教えてください。