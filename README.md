# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、品質チェック、ETL、特徴量計算、ニュース NLP（OpenAI を利用したセンチメント）、市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）など、戦略開発〜運用に必要な機能群を備えます。

---

## 主な機能（概要）

- ETL パイプライン（J-Quants API からの差分取得・保存・品質チェック）
  - 日次 ETL の実装（prices / financials / calendar）
  - 差分取得・バックフィル対応・品質チェック結果の集約（ETLResult）
- J-Quants API クライアント
  - 株価日足、財務データ、上場銘柄情報、JPX マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ニュース収集（RSS）とニュース前処理
  - URL 正規化・SSRF 対策・サイズ上限・gzip 対応などの安全対策
- ニュース NLP（OpenAI を利用したセンチメント）
  - 銘柄ごとのニュース集約 → LLM によるセンチメントスコア化（ai_scores へ保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + LLM マクロセンチメント）
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- データ品質チェック
  - 欠損、重複、未来日付、スパイク検出など
- 監査ログ（audit）
  - signal_events / order_requests / executions 等テーブルを備え、UUID による完全なトレーサビリティ
  - 初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 必要条件

- Python 3.10+
  - 型注釈に `X | None` や `from __future__ import annotations` を利用しているため 3.10 以上を想定しています。
- 主な Python 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布時に requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主要）

kabusys は .env / .env.local（プロジェクトルート）および環境変数から設定を読み込みます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主に必要な変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' / 'paper_trading' / 'live')（省略時 development）
- LOG_LEVEL — ログレベル ('DEBUG','INFO',...)（省略時 INFO）

.env ファイルの読み込みルール:
- OS 環境変数が優先される
- .env.local が .env を上書き（.env.local の方が優先）
- 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索して判定）から行われる

---

## セットアップ手順（例）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際のパッケージ一覧はプロジェクトの requirements.txt / pyproject.toml を参照してください。

3. ソースをインストールまたは PYTHONPATH を設定
   - プロジェクトルートで: pip install -e .
   - もしくは開発中は src を PYTHONPATH に含める

4. .env を作成
   - プロジェクトルートに .env を作成し、必要な環境変数を設定します。
   - 例:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB ファイルの初期化（監査ログなどを作る場合）
   - Python REPL またはスクリプトで:
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings
     conn = init_audit_db(settings.duckdb_path)
     # もしくは既存接続に対して init_audit_schema(conn)

6. （任意）OpenAI キーを設定して NLP 機能を利用

---

## 主要な使い方（例）

以下は Python から主要機能を呼ぶ簡単な例です。

- ETL（日次パイプライン）を実行する
  - 目的: J-Quants から差分でデータを取得し、品質チェックまで実行
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP による銘柄スコアを算出（score_news）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026, 3, 20))
    print("scored:", count)

  - note: OPENAI_API_KEY が必要。引数で api_key を渡すことも可能。

- 市場レジーム判定（score_regime）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

  - 内部で ETF 1321 の MA200 と OpenAI によるマクロセンチメントを合成して regime テーブルへ保存します。

- 監査ログ（audit）スキーマの初期化
  - 例:
    from kabusys.data.audit import init_audit_db
    from kabusys.config import settings

    conn = init_audit_db(settings.duckdb_path)  # transactional=True を渡すことも可能

- 監査専用 DB を別ファイルに作る場合:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

- RSS フィードの取得（ニュース収集の一部）
  - 例:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意:
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続はファイルパス文字列で duckdb.connect(...) により作成できます。
- OpenAI を呼び出す機能は API 呼び出しに失敗した場合にフォールバックやスキップする設計の箇所が多くあります（フェイルセーフ）。

---

## 自動ロードされる設定ファイル挙動

- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。
- 読み込み順:
  - OS 環境変数（最優先）
  - .env.local（存在すれば上書き）
  - .env（読み込み）
- 自動読み込みを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル風の `export KEY=val` やクォート、インラインコメントに対応しています。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

リポジトリの主要なツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py (パッケージ定義・公開モジュール)
  - config.py
    - 環境変数・設定管理（Settings オブジェクト）
    - 自動 .env ロード機能
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI でスコア化、ai_scores への書き込み
    - regime_detector.py
      - ETF 1321 MA200 乖離 + マクロニュース LLM を合成して market_regime 判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 & DuckDB への保存）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - news_collector.py
      - RSS 収集・前処理・記事ID生成（SSRF 対策等）
    - calendar_management.py
      - market_calendar 操作、営業日判定、calendar_update_job
    - audit.py
      - 監査ログ DDL / スキーマ初期化 / init_audit_db
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - etl.py
      - pipeline.ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー・ランク関数
  - ai/, data/, research/ はそれぞれの責務別のモジュール群です。

---

## 開発上の注意点 / 設計上のポイント

- Look-ahead bias の防止:
  - 多くのモジュールは内部で date.today() を直接参照しない設計（外部から target_date を渡す）。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT / DO UPDATE を利用して冪等に保存。
  - ニュースの ID は URL 正規化 + SHA-256 で決め、重複挿入を防止。
- フェイルセーフ設計:
  - LLM/API 失敗時はゼロやスキップして処理継続する箇所が多い（例: macro_sentiment=0.0）。
- セキュリティ:
  - RSS の取得時に SSRF 対策、gzip サイズチェック、defusedxml を使用。

---

もし README に追記したいサンプルスクリプト、CI 手順、あるいは .env.example のテンプレートが必要であれば、用途（開発／本番／テスト）に応じた雛形を作成します。必要であれば教えてください。