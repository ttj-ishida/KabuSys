# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼リサーチ / 自動売買支援ライブラリです。  
J-Quants API による株価・財務・カレンダーの ETL、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## 概要

- データ取得（J-Quants） → DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント / 市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）および研究用ユーティリティ
- 監査ログ（signal → order_request → executions までのトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の重点は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時のフォールバック）」です。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存：daily_quotes, financial_statements, market_calendar, listed_info）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS 取得・前処理・記事ID生成・保存ロジック）
  - 品質チェック（missing_data、duplicates、spike、date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - トークンリトライ・JSON Mode を利用した LLM 呼び出し（エラーハンドリング付き）
- research/
  - factor 計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local を参照）
  - settings オブジェクト経由で設定値取得（例：settings.jquants_refresh_token）

---

## セットアップ手順

前提：
- Python 3.10 以上（typing の | 記法を使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存関係が必要

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要ライブラリ（例）:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabu API (kabuステーション) (必要なら)
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（アラート等）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パスなど（必要に応じて）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. （任意）DuckDB データベースを初期化
   - 監査用 DB 初期化（例）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下はライブラリの代表的な使い方サンプルです。各関数は詳細な docstring を持っています。

- 設定値参照:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- DuckDB 接続を作って日次 ETL を実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", num_written)
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存 DB に追記）:
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算（例: モメンタム）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN - 必須（J-Quants API 用リフレッシュトークン）
- OPENAI_API_KEY - OpenAI API 呼び出しに使用（news_nlp / regime_detector）
- KABU_API_PASSWORD - kabuステーション API 用パスワード（必要に応じて）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID - Slack 通知用
- DUCKDB_PATH - デフォルト: data/kabusys.duckdb
- SQLITE_PATH - デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT - 監視設定
- KABUSYS_ENV - development / paper_trading / live（デフォルト: development）
- LOG_LEVEL - DEBUG/INFO/WARNING/ERROR/CRITICAL

（設定は kabusys.config.settings 経由でアクセスできます）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - pipeline.py
  - jquants_client.py
  - etl.py (export)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, strategy/, execution/ など（パッケージ公開の __all__ に含まれる可能性あり）

（上記はリポジトリ内の主要モジュールを抜粋しています）

---

## 設計上の注意点 / 運用メモ

- ルックアヘッドバイアス回避のため、各モジュールは内部で date.today() を直接参照しない、または target_date を明示的に受け取る設計になっています。バックテストや再現性のある実行では target_date を明示して呼び出してください。
- J-Quants API 呼び出しはレート制限・リトライ・401 自動リフレッシュに対応していますが、取得トークン（JQUANTS_REFRESH_TOKEN）は必須です。
- OpenAI 呼び出しは JSON Mode（response_format）を使用します。レスポンスのバリデーション・リトライが含まれていますが、API の仕様変更により調整が必要になる場合があります。
- DuckDB の executemany は一部バージョンで空リストが許容されないため、空チェックが実装されています。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行われます。CI/テスト環境などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発 / 貢献

- コードはモジュール単位でユニットテストを追加してください（外部 API 呼び出しはモック化）。
- ドキュメント（docstring）を優先して保守してください。各関数に十分な説明とエッジケース（データ不足・エラー時の挙動）を記載しています。

---

必要であれば README に以下を追加できます：
- requirements.txt の具体的な推奨バージョン
- よくあるトラブルシューティング（J-Quants 認証エラー、OpenAI レスポンスエラー、DuckDB の権限問題等）
- 実運用のデプロイ手順（systemd サービス例、cron/airflow ジョブ例）

追加で書きたい内容があれば教えてください。