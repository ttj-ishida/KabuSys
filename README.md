# KabuSys

日本株向けの自動売買 / データプラットフォーム向けライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメントスコア算出
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム / ボラティリティ / バリュー 等）
- 取引フローの監査テーブル（signal → order_request → execution のトレーサビリティ）
- 設定管理（.env 自動読込、環境切替）

設計上の特徴として、ルックアヘッドバイアス防止、冪等性、APIリトライ・レート制御、フェイルセーフ（API失敗時の継続）などに配慮されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（差分・ページネーション・保存関数）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 収集・前処理と raw_news 保存のためのユーティリティ
  - audit: 監査ログ（signal_events, order_requests, executions）テーブル初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で解析し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースで市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - 環境変数の自動ロード (.env/.env.local) と Settings オブジェクト（settings）

---

## 要件

- Python 3.10+
- 必要な外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）

（実際には pyproject.toml / requirements.txt を参照してください。ここでは主要依存のみ列挙しています。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements / pyproject がある場合はそちらを使用してください）
   ```
   pip install duckdb openai defusedxml
   # 開発用:
   pip install -e .
   ```

4. 環境変数 (.env) を用意
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（module: kabusys.config）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須／推奨の環境変数（一例）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
   - OPENAI_API_KEY (または api_key 引数) — OpenAI 呼び出しに必要
   - KABU_API_BASE_URL (省略可, デフォルト http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用, 任意)
   - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (監視DB, デフォルト data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development / paper_trading / live)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN="xxxxx"
   OPENAI_API_KEY="sk-xxxxx"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベースの初期化（監査用の例）
   Python REPL やスクリプトで:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # あるいは既存接続にスキーマを追加する:
   # conn = duckdb.connect("data/kabusys.duckdb")
   # from kabusys.data.audit import init_audit_schema
   # init_audit_schema(conn)
   ```

---

## 使い方（主要ユースケース）

※ ここでは代表的な呼び出し例を示します。実運用ではログ設定、例外処理、監視、スケジューラ等を併用してください。

1. 日次 ETL 実行
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュース NLP スコアリング（ai_scores への書き込み）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   n_written = score_news(conn, date(2026, 3, 20))
   print("書き込み銘柄数:", n_written)
   ```

3. 市場レジーム判定
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, date(2026, 3, 20))
   ```

4. 研究用ファクター計算
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

   conn = duckdb.connect(str(settings.duckdb_path))
   momentum = calc_momentum(conn, date(2026, 3, 20))
   volatility = calc_volatility(conn, date(2026, 3, 20))
   value = calc_value(conn, date(2026, 3, 20))
   ```

5. カレンダー / 営業日ユーティリティ
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.calendar_management import is_trading_day, next_trading_day

   conn = duckdb.connect(...)
   is_trade = is_trading_day(conn, date(2026,3,20))
   nxt = next_trading_day(conn, date(2026,3,20))
   ```

6. RSS フィード取得（ニュース収集）
   ```python
   from kabusys.data.news_collector import fetch_rss

   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
   for a in articles:
       print(a["id"], a["datetime"], a["title"])
   ```

---

## 設計上の注意・実運用ヒント

- Look-ahead bias を防ぐため、関数は内部で date.today() を直接参照しない設計が意識されています（target_date を明示してください）。
- J-Quants 呼び出しはレート制御とリトライを行います。大量取得時は API レートに配慮してください。
- OpenAI の呼び出しは JSON モードを利用し、レスポンスパース失敗時はフェイルセーフでスコアを 0.0 にフォールバックします。
- ETL は各ステップを独立して例外処理しており、一部失敗でも残り処理は継続します。結果は ETLResult で集約されます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する executemany の空リストは一部バージョンで問題となるため、コード側で空チェックを行っています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — 環境変数読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析と ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダーと営業日判定
  - etl.py — ETL の公開インターフェース（ETLResult）
  - pipeline.py — ETL 実装（run_daily_etl 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログ（DDL・初期化ユーティリティ）
  - jquants_client.py — J-Quants API クライアント + 保存関数
  - news_collector.py — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / サマリー
- research/（上記と同階層に収まる）
- その他: strategy, execution, monitoring 等の名前空間は __all__ に含まれますが、ここに示したファイル群が主要実装です。

---

## テスト・デバッグのヒント

- OpenAI / ネットワーク呼び出しは unittest.mock.patch で _call_openai_api 等を差し替えることでテスト可能です（コード中で考慮済み）。
- .env の自動ロードを無効化して環境分離するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- DuckDB はインメモリ ":memory:" を使って単体テスト可能です（audit.init_audit_db などは ":memory:" を受け付けます）。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API 仕様や運用ルール（スケジューリング、監視、発注フロー等）は別途ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照してください。必要であれば README に追加したい具体的なサンプルや運用手順を教えてください。