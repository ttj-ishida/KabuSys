# KabuSys

日本株向けの自動売買／データプラットフォームのライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と NLP（OpenAI を利用したセンチメント評価）、ファクター計算・研究ユーティリティ、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主要な設計方針：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を無作為に使わない）
- DuckDB を中心にローカルにデータを保存・参照
- OpenAI（gpt-4o-mini）を利用した JSON Mode での堅牢なレスポンス処理
- 冪等性（ON CONFLICT / idempotent 保存）と堅牢なリトライ／フォールバック処理

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得する ETL パイプライン（kabusys.data.pipeline）
  - 差分判定・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク（前日比）や日付不整合の検出（kabusys.data.quality）
- マーケットカレンダー管理
  - JPX カレンダーの取得／営業日判定／次営業日の取得など（kabusys.data.calendar_management）
- ニュース収集
  - RSS フィードの取得、URL 正規化、SSRF 回避、raw_news への冪等挿入（kabusys.data.news_collector）
- NLP / AI
  - 銘柄ごとのニュースセンチメントスコア生成（kabusys.ai.news_nlp::score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）（kabusys.ai.regime_detector::score_regime）
- 研究（Research）
  - ファクター計算（Momentum / Value / Volatility 等）、将来リターン、IC（情報係数）計算、Z-score 正規化（kabusys.research）
- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティ用テーブル DDL と初期化ユーティリティ（kabusys.data.audit）
- J-Quants クライアント
  - レート制限・認証（refresh token）・ページネーション対応の API 呼び出しと DuckDB への保存ヘルパ（kabusys.data.jquants_client）

---

## 要件（推奨）

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
（パッケージ名やバージョンはプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . または pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` と `.env.local` を置くと自動で読み込まれます（読み込み優先: OS env > .env.local > .env）。
   - 自動 .env ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for ETL）
   - OPENAI_API_KEY: OpenAI API キー（必須 for news_nlp / regime_detector）
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文実装がある場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使う場合
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/...

   .env の例（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（コード例）

以下は代表的な操作のサンプルです。実行前に必要な環境変数を設定してください。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores）を生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> 環境変数 OPENAI_API_KEY を使用
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームスコア算出
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants から全上場情報を取得（ユーティリティ）
  ```python
  from kabusys.data.jquants_client import fetch_listed_info
  info = fetch_listed_info(date_=date(2026,3,20))
  print(len(info))
  ```

テスト時の便利なポイント:
- OpenAI への実際の HTTP 呼び出しは、モジュール内の _call_openai_api を unittest.mock.patch で差し替えてモックできます（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）。

---

## 主要 API（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(text)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=[...])
  - calc_ic, factor_summary, rank
  - zscore_normalize (kabusys.data.stats)

---

## ディレクトリ構成（抜粋）

（提供されたコードベースに基づく主要ファイル）

- src/
  - kabusys/
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
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (ETLResult export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - (その他の名前空間: strategy, execution, monitoring は __all__ に記載あり。実装はプロジェクト全体を参照してください)

---

## 運用上の注意

- OpenAI（gpt-4o-mini）を使用する箇所は API 呼び出しの失敗や JSON パースの安全対策が実装されていますが、API キーや利用上限には注意してください。
- J-Quants API はレート制限があります（実装では 120 req/min を想定した RateLimiter を使用）。
- DuckDB への executemany に空リストを渡すと失敗するバージョン（古い DuckDB 0.10 等）があるため、コード内で空チェックが行われています。DuckDB バージョン互換性に注意してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 貢献 / 問い合わせ

バグ報告や改善提案はプルリクエスト / Issue でお願いします。テストやモック（OpenAI / ネットワーク部分の差し替え）を用意するとレビューがスムーズです。

---

この README はコードベースの主要機能をまとめたものです。より詳しい仕様（データスキーマ・ETL フロー・運用手順）はプロジェクト内のドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。