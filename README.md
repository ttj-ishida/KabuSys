# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
Data (ETL)、Research（ファクター計算・特徴量探索）、AI（ニュースセンチメント / 市場レジーム判定）、および監査/発注トレースのユーティリティを提供します。

主な用途の例：
- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と銘柄別 AI センチメント付与
- 日次の market_regime / ai_scores の算出
- 研究用のファクター計算、IC・前方リターン算出
- 注文監査用の DuckDB スキーマ初期化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを検出して読み込み）
  - 必須環境変数取得ヘルパー（missing -> ValueError）
- Data（kabusys.data）
  - J-Quants API クライアント（取得・保存・ページング・リトライ・レート制限）
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策、XML 安全パース）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（監査テーブル・インデックス、init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（Zスコア正規化）
- AI（kabusys.ai）
  - ニュースセンチメントの LLM スコアリング（score_news）
  - 市場レジーム判定（score_regime）: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成
  - LLM 呼び出しは OpenAI API（gpt-4o-mini 想定）を使用。API キーは引数 or 環境変数で注入可能（テスト容易性に配慮）
- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

---

## 必要条件（依存例）

（プロジェクトに含まれるコードから想定される主なパッケージ）
- Python 3.10+
- duckdb
- openai
- defusedxml

例（requirements.txt の一部）:
- duckdb
- openai
- defusedxml

実際のバージョンはプロジェクトのパッケージ管理設定に合わせてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作る
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   - もし setup.py / pyproject.toml がある場合:
     ```
     pip install -e .
     ```
   - 最小:
     ```
     pip install duckdb openai defusedxml
     ```

3. 環境変数設定
   - プロジェクトルートに `.env` を作成して次を設定（例）
     ```
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動で .env/.env.local を読み込む仕組みが有効（無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）

4. DuckDB データベースの準備
   - デフォルトパスは `data/kabusys.duckdb`（settings.duckdb_path）
   - 監査ログ専用 DB を初期化する例（Python REPL / スクリプト）:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存接続に監査スキーマを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（主要な例）

- 設定取得（環境変数）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- DuckDB に接続して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(__import__('kabusys').__file__))  # 実運用では settings.duckdb_path を使う
  # 例: conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメント付与（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # API キーは環境変数 OPENAI_API_KEY か、引数 api_key で渡す
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター呼び出し例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

- ニュース収集（RSS）を取得する単体ユーティリティ
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  ```

注意:
- AI系関数は OpenAI API を呼ぶため料金・利用規約に注意してください。
- API 呼び出しには retry/backoff の処理が組み込まれています。テストでは API 呼び出し箇所をモックする設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 for AI機能) — OpenAI API キー（score_news / score_regime 等）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（使用箇所がある場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb) — メイン DuckDB ファイルパス
- SQLITE_PATH (任意, デフォルト: data/monitoring.db) — 監視用途の SQLite パス
- KABUSYS_ENV (任意, デフォルト: development) — 有効値: development / paper_trading / live
- LOG_LEVEL (任意, デフォルト: INFO) — 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化（テスト用）

---

## ディレクトリ構成（ハイレベル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定ロード（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント / 保存関数
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS ニュース収集・前処理
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック
  - stats.py — 汎用統計（zscore_normalize）
  - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等
  - feature_exploration.py — 将来リターン・IC・統計サマリー

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス対策
  - 日付/ウィンドウ計算は内部で datetime.today() を参照しない（target_date を明示的に渡す設計）
  - prices_daily などのクエリは target_date 未満 / 排他条件を徹底
- 冪等性
  - ETL 保存関数は ON CONFLICT DO UPDATE などで冪等に実行可能
  - 監査ログは order_request_id を冪等キーとして設計
- フェイルセーフ
  - AI API の失敗時はスコアを 0.0 にフォールバックするなど合成の安全性を確保
  - ETL の各ステップは独立してエラーハンドリングを行い、部分失敗しても他処理は継続
- テスト容易性
  - OpenAI 呼び出し部分は内部関数をモックしやすく設計（ユニットテストで差し替え可能）
  - 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能

---

## 追加のヒント

- ローカルで ETL を回すときは DUCKDB_PATH を適切に設定しておくとデータ管理が容易です。
- AI 呼び出しはコストが発生するので開発・テスト時はモックを推奨します。
- jquants_client は API レート・401 リフレッシュ等を扱います。大規模実行ではレート制御に注意してください。

---

ご要望があれば以下を追記・展開します：
- インストール用の pyproject.toml / requirements.txt のテンプレート
- よく使う CLI スクリプト例（ETL バッチ、ニュース収集、レジーム判定の cron 例）
- 各テーブルのスキーマ詳細とサンプルクエリ
- 開発・デバッグのチェックリスト（ログ設定、テスト用モック方法）