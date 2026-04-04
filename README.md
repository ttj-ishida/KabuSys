# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants・JPX・ニュース・LLM を組み合わせた
データ ETL、ニュース NLP、リサーチ、監査ログ、監視用設定などのユーティリティ群を提供します。

主な目的：
- J-Quants から市場データ（株価・財務・上場情報・カレンダー）を差分取得して DuckDB に保存
- RSS を収集してニュースを保存・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント分析と市場レジーム判定
- ファクター計算・特徴量探索（研究用）
- 発注・約定の監査ログスキーマ初期化ユーティリティ
- データ品質チェック

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - 必須環境変数未設定時は明示的エラーを発生
- データ ETL（kabusys.data.pipeline）
  - 株価（日次）、財務、マーケットカレンダーの差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括実行
- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しラッパー、リトライ・レート制限・トークン自動リフレッシュ
  - fetch / save 関数群（daily_quotes、financials、market_calendar、listed_info）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、記事正規化、SSRF 対策、記事ID 生成、raw_news 保存向けの前処理
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄別ニュースセンチメント計算（バッチ処理、JSON Mode 対応、リトライ）
  - score_news(conn, target_date, api_key=None)
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュース LLM 評価を組み合わせて日次で 'bull'/'neutral'/'bear' 判定
  - score_regime(conn, target_date, api_key=None)
- 研究モジュール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db
- 設定（kabusys.config）
  - 各種環境変数アクセスラッパー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
  - 自動 .env ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

---

## セットアップ手順（ローカル開発用）

1. Python と仮想環境
   - Python >= 3.10 を推奨
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（代表的な依存）
   - pip install duckdb openai defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   サンプル（.env.example）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション API（発注系を使う場合）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # LINE 通知（任意）
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. プロジェクトルートの作成（データ保存用）
   - デフォルトでは data/ 以下に DB 等を保存します。必要ならディレクトリを作成してください。
     - mkdir -p data

---

## 使い方（主要なユーティリティ例）

以下は Python スクリプトまたは REPL からの利用例です。各関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア生成（指定日）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る例）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます
  ```

- J-Quants クライアントの直接利用（データ取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

  quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,31))
  financials = fetch_financial_statements(date_from=date(2025,1,1), date_to=date(2026,3,31))
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点：
- OpenAI API を呼ぶ機能（score_news, score_regime 等）は OPENAI_API_KEY の設定が必須です（または関数に api_key 引数を与える）。
- J-Quants API を使う場合は JQUANTS_REFRESH_TOKEN が必須です。
- ETL や保存処理は DuckDB 側のスキーマが前提になっています。初回は適切なスキーマ初期化（プロジェクト固有のスクリプト）を行ってください。

---

## ディレクトリ構成

以下はコードベースの主要ファイル・モジュール構成（抜粋）です。実際は src/kabusys 以下に多数のモジュールがあります。

- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py                      # ニュース NLP（score_news）
      - regime_detector.py               # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - calendar_management.py           # 市場カレンダー管理
      - etl.py                           # ETL 公開インターフェース
      - pipeline.py                      # ETL パイプライン（run_daily_etl など）
      - stats.py                         # 統計ユーティリティ（zscore_normalize）
      - quality.py                       # データ品質チェック
      - audit.py                         # 監査ログスキーマ初期化
      - jquants_client.py                # J-Quants API クライアント（fetch/save）
      - news_collector.py                # RSS ニュース収集
    - research/
      - __init__.py
      - factor_research.py               # ファクター計算（momentum/value/volatility）
      - feature_exploration.py           # 将来リターン / IC / 統計サマリー
    - (他: execution, monitoring, strategy などのサブパッケージが想定される)

---

## 実運用上の注意 / ベストプラクティス

- 環境分離：
  - 設定で KABUSYS_ENV を使い分け（development / paper_trading / live）。
  - 本番（live）では十分なログ・監査・テストを行ってから稼働してください。
- セキュリティ：
  - .env に機密情報（API トークン）を含める場合はパーミッション管理を徹底すること。
  - news_collector は SSRF 対策やリダイレクト検査を実装していますが、社内ポリシーに合わせて更に制限することを検討してください。
- リトライとフェイルセーフ：
  - 外部 API 呼び出しはリトライやフォールバック（ゼロスコアなど）を行う設計になっていますが、
    API 制限や課金に注意して使ってください。
- Look-ahead bias：
  - 研究・スコア生成関数はルックアヘッドバイアス防止を念頭に実装されています（内部で date.today() を直接参照しない等）。
  - バックテストでは、データの取得タイミング（fetched_at）や ETL の実行タイミングを考慮してください。

---

必要に応じて、README に含めたい追加項目（例：インストール可能なパッケージリスト、具体的な DB スキーマ定義、運用 cron/ジョブのサンプル、CI 設定、単体テスト実行方法など）があれば教えてください。README をそれに合わせて拡張します。