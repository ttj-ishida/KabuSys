# KabuSys

日本株向けのデータパイプライン・リサーチ・自動売買基盤用ライブラリ (KabuSys)

このリポジトリは、日本株のデータ取得（J-Quants）、データ品質チェック、ETL、ニュース収集・NLP、リサーチ（ファクター計算・特徴量解析）、および売買監査ログ（トレーサビリティ）や市場レジーム判定・AIスコアリングなどの機能を提供します。DuckDB を分析用DBとして使い、OpenAI（gpt-4o-mini）をニュースのセンチメント解析に利用する設計です。

## 主な特徴
- J-Quants API を用いた差分ETL（株価日足、財務、カレンダー等）
- DuckDB に対する冪等保存（ON CONFLICT / UPDATE）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策、URL正規化、サイズ制限）
- ニュースの LLM ベースセンチメント解析（バッチ、JSON-mode、リトライ）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの融合）
- 研究用モジュール：モメンタム/ボラティリティ/バリュー等のファクター計算、将来リターン、IC 計算、Z-score 正規化
- 監査ログ（signal_events / order_requests / executions）テーブル定義と初期化ユーティリティ
- 環境変数・設定管理（.env 自動ロード機構あり）

---

## 機能一覧（モジュール別）
- kabusys.config
  - 環境変数の自動読み込み（プロジェクトルートにある `.env` / `.env.local`）。必須設定取得ユーティリティ。
- kabusys.data
  - jquants_client: J-Quants API 取得、保存ロジック（rate limit、リトライ、トークンリフレッシュ）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 取得・前処理・記事ID生成・SSRF対策
  - calendar_management: 市場カレンダー取得／営業日判定／next/prev_trading_day 等
  - audit: 監査ログスキーマ作成 & DB 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを計算して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースで市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10+ 推奨（typing 機能を利用）
- DuckDB（Python パッケージ）を利用
- OpenAI Python SDK（LLM 呼び出し）
- defusedxml（RSS パースのセキュリティ）

1. リポジトリをクローンし、仮想環境を作成
   - Unix/macOS:
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     git clone <repo-url>
     cd <repo>
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. パッケージインストール
   - 簡易に必要パッケージをインストールする例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用に editable install:
     ```
     pip install -e .
     ```
     （setup.py / pyproject.toml がある場合に利用）

3. 環境変数設定
   - プロジェクトルートに `.env` を作成することで自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI 呼び出し用（news_nlp / regime_detector）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）

   - `.env` の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_pw
     SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
     SLACK_CHANNEL_ID=C0123456789
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（主要ユースケース）

以下は Python スクリプト／REPL からの利用例です。

- DuckDB 接続を作成して日次 ETL を実行（run_daily_etl）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # 今日の ETL（内部で営業日に調整されます）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- OpenAI を使ったニューススコアリング（銘柄別ニュース解析）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム算出:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions テーブルが作成されます
  ```

- RSS 取得（ニュースコレクタの単体利用）:
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- AI モジュールは OpenAI の API キー（OPENAI_API_KEY）を必要とします。
- J-Quants 呼び出しは API レート制限を守り、トークンの自動リフレッシュ機能を備えています。J-Quants のリフレッシュトークンを `JQUANTS_REFRESH_TOKEN` に設定してください。
- データ取得 / 保存系は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar 等）を前提とします。初期スキーマは ETL 実行時または別途スキーマ初期化スクリプトで作成してください。

---

## 環境変数（重要なキー）
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (AI スコアリングに必須)
- KABU_API_PASSWORD (kabuステーション API パスワード)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- KABUSYS_ENV (development | paper_trading | live) — 動作モード判定
- LOG_LEVEL (ログレベル)
- DUCKDB_PATH (DuckDB ファイルパス)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑制します（テスト時に有用）。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内部の主要なファイル構成（src/kabusys 以下）です。実際のツリーはリポジトリを参照してください。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各ファイルの役割は上の「機能一覧」を参照してください。

---

## 開発・テスト
- テストフレームワークは特に指定していませんが、ユニットテストを書く際は OpenAI / ネットワーク呼び出しや外部APIをモックすることを推奨します（モジュール内の _call_openai_api や _urlopen 等を patch 可能）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト実行時に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用上の注意
- J-Quants・OpenAI など外部 API 呼び出しはコスト・レート制限があるためバッチ設計・リトライ・バックオフが組み込まれています。運用時は API 利用量・課金に注意してください。
- DuckDB の executemany はバージョン差異に注意（空リストを渡せない制約等）。pipeline モジュールはそれらを考慮した実装になっています。
- LLM 出力に依存する箇所はパースに失敗した場合にフォールバック（0.0）する等の安全策が入っていますが、プロダクションでの自動売買に組み込む際は追加のガバナンスを必ず実装してください。

---

この README はコードベースの現状（モジュール実装）を基に作成しています。より詳細な設計資料（DataPlatform.md, StrategyModel.md 等）や運用手順が別途ある場合はそちらも併用してください。必要であれば README に含めるサンプルや運用手順をさらに追加します。