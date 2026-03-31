# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ・発注トラッキング、マーケットカレンダー管理など、取引システムを構成する主要コンポーネント群を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分 ETL（DuckDB 保存、冪等）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / 市場レジーム判定
- 研究向けのファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）の DuckDB スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- カレンダー管理（JPX カレンダーの夜間更新、営業日判定）

設計方針として、ルックアヘッドバイアス対策、堅牢な API リトライ、冪等性、外部依存の最小化（研究モジュールは pandas 等に依存しない）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークンリフレッシュ・レートリミット）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・正規化・raw_news 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュース（LLM）を組み合わせて market_regime に判定結果を書き込み
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: 環境変数・設定読み込み（.env 自動ロード、必須チェック）

---

## 前提条件

- Python 3.10+（型ヒントで Union 表記や型演算を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI）

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境を作成・アクティベート（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   例（最低限）:
   ```
   pip install duckdb openai defusedxml
   # もしパッケージ化されていれば:
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（または各関数呼び出しで api_key を指定）
   - オプション・パス関連:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG / INFO / ...）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=~/data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化（監査ログなど）例:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings

   conn = init_audit_db(str(settings.duckdb_path))
   # または既存接続へ init_audit_schema(conn)
   ```

---

## 使い方（主要な呼び出し例）

以下は代表的なユースケースとコード例です。実行は各自の環境変数（API キー等）を正しく設定した上で行ってください。

- DuckDB 接続の作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定することでルックアヘッドバイアスを避ける
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を用いて ai_scores に書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すことも可能。None の場合は環境変数 OPENAI_API_KEY を参照
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 市場レジーム判定（MA200 とマクロニュースから label を market_regime に保存）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（別ファイルで監査用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- カレンダー操作（営業日判定など）
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  is_open = is_trading_day(conn, date(2026, 3, 20))
  next_day = next_trading_day(conn, date(2026, 3, 20))
  ```

- RSS 取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意:
- OpenAI 呼び出しは課金対象であり、API キーと利用量の管理に注意してください。
- J-Quants との通信はレート制限・認証が必要です。JQUANTS_REFRESH_TOKEN を設定してください。
- DuckDB の executemany で空リストを渡すことが制約となる箇所があるため、関数は内部で空チェックをしています。

---

## 環境変数と自動ロード挙動

- config.Settings を通じて環境変数を参照します。必須値が未設定の場合は ValueError が発生します。
- 自動ロード:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を特定し、プロジェクトルートの `.env` と `.env.local` を順に読み込みます。
  - 読み込み順（優先度）: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```
- 変数検証:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL"。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        # ニュースセンチメント計算と ai_scores 書き込み
    - regime_detector.py # 市場レジーム判定（MA200 + LLM）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - news_collector.py     # RSS 収集・前処理
    - quality.py            # データ品質チェック
    - calendar_management.py# マーケットカレンダー管理
    - audit.py              # 監査ログスキーマ（init_audit_schema / init_audit_db）
    - stats.py              # zscore_normalize 等
    - etl.py                # ETLResult 再エクスポートインターフェース
  - research/
    - __init__.py
    - factor_research.py    # calc_momentum, calc_volatility, calc_value
    - feature_exploration.py# calc_forward_returns, calc_ic, factor_summary, rank
  - ai, research, data の各モジュールは主に duckdb 接続を受け取る設計で、外部の発注 API 等には依存しません。

---

## テスト・開発メモ

- 設定読み込みを無効にしたいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI / J-Quants 呼び出しは外部依存のためユニットテストではモック（unittest.mock.patch 等）を使用して置き換えることを想定しています。実装中にも各モジュールに差し替えやすい内部ラッパー関数を用意しています（例: _call_openai_api のモック差替え）。
- DuckDB による SQL は互換性を意識して書かれていますが、バージョン差異には注意してください（executemany の空リストなど）。

---

## ライセンス・貢献

（プロジェクトに合わせてライセンス／貢献ガイドラインを追記してください）

---

この README はコードベースの主要な API と設定の使い方を概説しています。詳しい API 引数・返り値や内部実装の仕様は各モジュールの docstring を参照してください。質問や補足があればお知らせください。