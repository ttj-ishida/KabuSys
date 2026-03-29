# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュースの収集・NLP スコアリング、LLM を使った市場レジーム判定、研究用ファクター・特徴量解析、監査ログ（監査テーブル）等のユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資・自動売買基盤を構築するための内部ライブラリ群です。主に以下の領域をカバーします。

- データ取得（J-Quants API）・ETL（差分取得、冪等保存、品質チェック）
- ニュース収集（RSS）・NLP によるセンチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（シグナル → 発注 → 約定 をトレースするテーブル群）
- 汎用ユーティリティ（統計、カレンダー管理、品質チェックなど）

設計方針として、バックテストでのルックアヘッドバイアスを避ける実装（明示的な target_date に基づく処理）や、外部 API 呼び出しの堅牢性（リトライ、レートリミット、フォールバック）を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants からの株価・財務・カレンダー取得（ページネーション・リトライ・トークン自動更新対応）
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
- data/pipeline
  - 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - ETLResult による実行結果集約
- data/quality
  - 欠損、重複、スパイク、日付不整合（未来日/非営業日）などの品質チェック
- data/calendar_management
  - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days 等
- data/news_collector
  - RSS フィード取得、前処理、記事ID生成/正規化（SSRF・XML 漏洩対策あり）
- ai/news_nlp
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア生成（ai_scores へ書込）
- ai/regime_detector
  - ETF（1321）200日 MA 乖離とマクロニュース LLM スコアを合成し日次市場レジーム判定（market_regime へ書込）
- research
  - calc_momentum / calc_volatility / calc_value 等のファクター計算、forward returns、IC、統計サマリー
- data/audit
  - signal_events / order_requests / executions など監査用テーブル定義と初期化ユーティリティ

---

## セットアップ手順

前提: Python 3.10 以上を推奨（コード中に型ヒントの `X | None` 等を使用）

1. リポジトリをチェックアウト、仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
   - 開発用 / packaging に応じて pyproject.toml / requirements.txt を利用してください。例:
   ```
   pip install duckdb openai defusedxml
   pip install -e .   # パッケージとしてインストールする場合
   ```

3. 環境変数 (.env) の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu API のパスワード（発注等を行う場合）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知を使う場合）
     - SLACK_CHANNEL_ID      : Slack 通知送信先チャンネル ID
     - OPENAI_API_KEY        : OpenAI API キー（AI スコアリングを実行する場合）
   - 任意/デフォルト:
     - KABUSYS_ENV （development | paper_trading | live） デフォルト: development
     - LOG_LEVEL （DEBUG|INFO|WARNING|ERROR|CRITICAL） デフォルト: INFO
     - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（コード例）

以下は簡単な操作例です。実際の運用ではエラーハンドリングやログ設定を行ってください。

- DuckDB 接続の用意
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 監査 DB を初期化（別ファイルに監査用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL を実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # ETL 実行（target_date を指定しない場合は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを作成（OpenAI API キーは env もしくは引数）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジームを判定（regime_detector）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- J-Quants API を直接使ってデータ取得（テストやデバッグ用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を利用して取得
  rows = fetch_daily_quotes(id_token=id_token, date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
  ```

- ニュース RSS の取得（news_collector.fetch_rss を単体で呼ぶ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意: 上記の多くの操作は OpenAI キーや J-Quants トークン、DuckDB スキーマ（テーブル作成）が前提です。データ保存用のスキーマが存在しない場合は、対象テーブルを作成する初期化処理を用意してください（本リポジトリ内に schema 初期化用のユーティリティが存在する想定です）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリングを行う場合）
- KABU_API_PASSWORD: kabu API のパスワード（発注機能使用時）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知を行う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
- KABUSYS_ENV: 環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動的な .env 読み込みを無効化します。

config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を自動的に読み込みます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの LLM スコアリングと ai_scores 書込
    - regime_detector.py     # 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch / save）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETL 結果再エクスポート（ETLResult）
    - quality.py             # データ品質チェック
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - news_collector.py      # RSS 取得 / 前処理 / セキュリティ対策
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     # momentum / value / volatility 等
    - feature_exploration.py # forward returns / IC / rank / summary
  - ai/                      # （上記）
  - research/                # （上記）
- pyproject.toml (想定)
- .git/ (想定)

（実際のリポジトリには追加のユーティリティ・テスト等が含まれる可能性があります）

---

## 注意事項 / 運用上の留意点

- Look-ahead バイアス対策: 多くの関数は内部で datetime.today() を参照せず、明示的な target_date に基づいて処理します。バックテストや過去の再現性を考慮した設計です。
- LLM/外部 API の失敗時フォールバック: OpenAI/J-Quants 呼び出しでエラーやパース失敗があっても、モジュールはフェイルセーフ（スコアを 0 にフォールバック、または該当処理をスキップ）を行う箇所が多くあります。ただし、致命的なケースは上位に例外を上げます。
- DuckDB スキーマ: ETL や保存処理は既存のスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, 等）を前提としています。初期スキーマの作成は別途スクリプト／マイグレーションが必要です。
- セキュリティ: news_collector では SSRF、XML Bomb、レスポンスサイズ上限などの対策を実装していますが、実運用ではネットワークレベルの制限や監査を行ってください。
- レート制限: J-Quants は 120 req/min を想定し RateLimiter を使用しています。大量取得・並列呼び出しの際は注意してください。

---

必要であれば README に以下を追加可能です:
- テーブル DDL / 初期スキーマ作成手順
- CI / テスト実行方法
- 実運用向けのデプロイ手順（systemd / cron / Airflow 等）
- 詳細な .env.example ファイル

希望があれば追記します。