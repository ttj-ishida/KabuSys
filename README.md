KabuSys — 日本株自動売買プラットフォーム
=================================

本プロジェクトは日本株のデータパイプライン・リサーチ・AI 判定・監査・ETL を含む自動売買・研究基盤の一部実装です。  
（提示されたコードベースの抜粋に基づく README です）

概要
----
KabuSys は以下を目的としたモジュール群です。

- J‑Quants API を用いた株価 / 財務 / カレンダーの差分取得と DuckDB への冪等保存（ETL）
- ニュース収集（RSS）と LLM を用いたニュースセンチメント評価（銘柄別）
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアの合成）
- 研究用途のファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量探索
- データ品質チェック、マーケットカレンダー管理
- 発注→約定までを辿れる監査ログ用スキーマ（DuckDB）

主要機能一覧
-------------
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート基準、無効化フラグあり）
  - 必須環境変数のラッピング（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* など）
  - KABUSYS_ENV, LOG_LEVEL の検証

- データ ETL（kabusys.data.pipeline / etl / jquants_client）
  - J‑Quants API から日足・財務・カレンダーを差分取得（ページネーション対応）
  - レートリミット遵守、リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得（SSRF／リダイレクト検査、gzip 実装、トラッキングパラメータ除去）
  - 記事 ID の一意化（URL 正規化 → SHA256 ハッシュ先頭）

- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を利用した銘柄別センチメントスコア生成（JSON mode）
  - バッチ処理・チャンク化・リトライ・レスポンスバリデーション
  - ai_scores テーブルへの安全な差し替え保存

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアを合成して daily レジーム判定
  - LLM 呼び出し失敗時にはフェイルセーフ（macro_sentiment=0.0）

- 研究用モジュール（kabusys.research）
  - ファクター計算: momentum, value, volatility
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合等の検出（QualityIssue を返す）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_db による DuckDB 初期化（UTC タイムゾーン固定）

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上（タイプ注釈の | 演算子を利用）
   - ネットワークアクセス（J‑Quants / RSS / OpenAI など）
   - 推奨: 仮想環境を使用

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従う）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 .env（必要なキー、最低限のサンプル）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - OPENAI_API_KEY=sk-...
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   注意: Settings クラスは以下の値を検証します。
   - KABUSYS_ENV: "development" / "paper_trading" / "live"
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

5. データベース初期化（監査スキーマ）
   - Python REPL で:
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)
   - または既存の DuckDB 接続へ init_audit_schema(conn) を呼ぶ

基本的な使い方（コード例）
-------------------------

- DuckDB 接続を開く（モジュールは duckdb を使用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（run_daily_etl）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントをスコアリング（AI を使用）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {n_written} ai_scores")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- ニュース RSS を取得（保存ロジックはプロジェクトの raw_news テーブルへ実装する必要あり）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

- 研究モジュール例（ファクター計算）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  # momentum は dict のリスト（date, code, mom_1m, mom_3m, ...）

運用上の注意
-------------
- LLM（OpenAI）呼び出しを行う機能は api_key を必要とします。関数は api_key 引数または環境変数 OPENAI_API_KEY を参照します。
- AI モジュールはレスポンス不備や API エラー時にフェイルセーフなデフォルト（0.0）を採る設計になっていますが、API 利用料やレイテンシには注意してください。
- jquants_client は 120 req/min のレート制御を内蔵しています。別途並列化する場合は注意してください。
- DuckDB の executemany に空のリストを渡すと問題になるバージョンがあるため、実装側で空チェックを行っています。

ディレクトリ構成（主要ファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（銘柄別スコア）
  - regime_detector.py      — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py       — J‑Quants API クライアント & DuckDB 保存
  - pipeline.py             — ETL パイプライン / run_daily_etl 等
  - etl.py                  — ETL の公開インターフェース（ETLResult）
  - news_collector.py       — RSS ニュース収集
  - quality.py              — 品質チェック
  - calendar_management.py  — マーケットカレンダー管理
  - stats.py                — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py      — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py  — 将来リターン/IC/統計サマリー/ランク

（補足）
- 一部参照されるモジュールやテーブル（raw_news, raw_prices, ai_scores, market_calendar 等）はデータベーススキーマ側で事前に作成されている前提です。ETL / audit 初期化ユーティリティを利用してテーブルを整備してください。
- README は提示されたコード抜粋に基づいて作成しています。追加のユーティリティや CLI を含む場合はプロジェクトのトップレベルドキュメント（pyproject.toml / setup.cfg / scripts）に従ってください。

ライセンス / 貢献
-----------------
（コードベースにライセンス表記がないためここでは明記していません。実運用・公開前にライセンス・セキュリティ要件を確認してください。）

問い合わせ
----------
仕様の補完や具体的な使い方（DB スキーマ、ETL の Cron 設定、運用手順など）を希望される場合は、目的（バックテスト用？本番運用？）と利用環境を教えてください。それに応じて README の追記やサンプルスクリプトを作成します。