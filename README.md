# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
このパッケージはデータ ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアント等を提供し、アルゴリズム取引システムの基盤を構成します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるライブラリ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- RSS によるニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_score）およびマクロセンチメントと価格指標を合成した市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および研究ユーティリティ（将来リターン、IC、統計サマリ）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）
- DuckDB を中心としたデータ保存・クエリ処理

設計思想として「ルックアヘッドバイアスを避ける」「冪等性」「外部 API に対する堅牢なリトライ/レート制御」「最小依存（標準ライブラリ中心）」を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / トークン自動更新 / レート制御）
  - pipeline: 日次 ETL（prices / financials / calendar）および ETLResult
  - news_collector: RSS 収集、前処理、raw_news への保存（SSRF 防御・サイズ制限等）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ（signal_events, order_requests, executions）と初期化
  - stats: z-score 正規化など共通統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント計算および ai_scores への書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロ記事の LLM センチメントを合成した市場レジーム判定
- research
  - factor_research: calc_momentum / calc_volatility / calc_value（各種定量ファクター）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（研究用統計・評価）
- config
  - 環境変数読み込み（.env / .env.local 自動ロード）と settings オブジェクト（必須変数チェック）

---

## セットアップ手順

注意: コードは Python 3.10 以降（match 型や | 型ヒントを含むため）を想定しています。

1. リポジトリをクローンする
   - 通常の手順で取得してください。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/Mac)
   - .\.venv\Scripts\activate    (Windows PowerShell)

3. 必要パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください。）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabuステーション等の API パスワード（必要な場合）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知を使う場合）
     - SLACK_CHANNEL_ID      : Slack チャネル ID
   - 任意・デフォルト付き:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) デフォルト: INFO
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db
     - OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）の場合必要

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DB 初期化（監査ログ等）
   - 監査ログ専用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下は主要なユースケースの利用例です。実行前に settings（環境変数）が正しく設定されていることを確認してください。

- 日次 ETL を実行（データ取得・保存・品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_scores への書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数または api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- AI 系処理（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。API 呼び出しはリトライを行いますが、レート制限や料金に注意してください。
- 実運用で発注や kabu API を使う場合は、KABUSYS_ENV を適切に設定（paper_trading / live）し、十分なテストを行ってください。

---

## 主要モジュール / ディレクトリ構成

概要的なツリー（主要ファイルのみ）:

- src/kabusys/
  - __init__.py            -- パッケージ定義、バージョン
  - config.py              -- 環境変数／設定読み込み（settings）
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュースを LLM でスコア化して ai_scores に保存
    - regime_detector.py   -- MA とマクロセンチメントを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得/保存/認証/リトライ）
    - pipeline.py          -- ETL パイプライン（run_daily_etl など）
    - etl.py               -- ETLResult 再エクスポート
    - news_collector.py    -- RSS 収集と前処理（SSRF防御等）
    - calendar_management.py -- 市場カレンダー管理・営業日判定
    - quality.py           -- データ品質チェック
    - stats.py             -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py             -- 監査ログスキーマの初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py   -- モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py -- 将来リターン・IC・統計サマリ等
  - research/*              -- 研究用ユーティリティ群（rank, factor_summary, etc.）

各ファイル内には詳細な docstring と設計方針、フェイルセーフ動作（例: API 失敗時のフォールバック）が記載されています。まずは data.pipeline.run_daily_etl と ai.news_nlp.score_news を組み合わせるワークフローから始めるとよいでしょう。

---

## 注意事項 / 運用上のヒント

- Look-ahead バイアスを避ける設計が随所に入っています。例えば target_date 未満のデータのみ参照する等、バックテスト用の取り扱いに注意してください。
- DuckDB の executemany はバージョン差で挙動が異なる箇所があります（コード内で対応済み）。DuckDB バージョン管理に注意してください。
- OpenAI API 呼び出しはコストとレート制限に注意してください（モデルは gpt-4o-mini を指定している箇所あり）。
- 自動で .env をロードしますが、CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して明示的に環境を制御できます。
- 実際に発注する機能はこのコードベースの別モジュール（execution 等）で実装する想定です。実運用前に paper_trading 環境で十分に検証してください。

---

必要であれば、README にサンプル .env.example、requirements.txt（推奨パッケージ一覧）、または具体的な ETL / バックテストのワークフロー例（cron / Airflow など）を追記できます。どの情報を優先的に追加しますか？