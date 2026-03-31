# KabuSys

日本株向けの自動売買 / リサーチ / データ基盤ライブラリです。  
DuckDB を内部データベースとして利用し、J-Quants API／RSS／OpenAI（LLM）等と連携してデータ収集、品質チェック、ニュースセンチメント、マーケットレジーム判定、ETL、監査ログを提供します。

## 主な特徴
- データ ETL（株価、財務、マーケットカレンダー）の差分取得・保存（J-Quants 経由）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄別）スコアリング（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）モジュール
- 監査ログ（signal → order_request → executions）のスキーマ初期化／管理機能
- 環境変数／.env 自動読み込み（プロジェクトルートの .env/.env.local）

---

## 機能一覧（概要）
- kabusys.config
  - 環境変数読み込み、自動 .env ロード、設定プロパティ（J-Quants トークン、OpenAI 等）
- kabusys.data
  - jquants_client: J-Quants からのデータ取得／DuckDB 保存（差分・ページネーション・リトライ）
  - pipeline: 日次 ETL 実行（run_daily_etl）および個別 ETL ジョブ
  - news_collector: RSS 収集・前処理・保存ヘルパー
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロセンチメントを合成し market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提
- Python 3.10+（typing の一部表記に依存）
- DuckDB を使用（ローカルファイルベースまたはインメモリ）
- J-Quants API トークン、OpenAI API キー等の外部キー

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   最低限必要な外部パッケージ:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください:
   pip install -e . など）

4. 環境変数の設定
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須（少なくとも開発で使う主要項目）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI の API キー（score_news / regime_detector が必要）
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注等を実装する際に使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（モニタリング等で使用）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   任意/デフォルトあり:
   - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"
   - KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト "development"）
   - LOG_LEVEL: "DEBUG" / "INFO" / ...

   注: README に .env.example を参考に作成する旨の文言がコードにあります。プロジェクトに .env.example が含まれている場合はそれを参考にしてください。

---

## 使い方（主な例）

以下はいくつかの代表的な利用例です。Python スクリプトや REPL で実行できます。

基本的に DuckDB 接続を渡して関数を呼び出します。

- ETL（1日分のデータを取得して保存・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントの実行（OpenAI API キーが環境変数 OPENAI_API_KEY にあること）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

  score_news は API キーを引数（api_key="sk-..."）で渡すことも可能です。

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査用 DuckDB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルにアクセス可能
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- RSS 取得（news_collector の fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

注意点:
- OpenAI 呼び出し部は外部 API のため、API キー設定・レート・料金に注意してください。score_news / regime_detector は失敗フォールバックやリトライを組み込んでいますが、API 呼び出しの回数は管理してください。
- ETL / jquants_client は J-Quants のレート制限に従う実装（RateLimiter）です。実行頻度に注意してください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数管理・自動 .env ロード・settings
- ai/
  - __init__.py
  - news_nlp.py       — ニュースセンチメント（score_news）
  - regime_detector.py— 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
  - pipeline.py       — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py            — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理
  - quality.py        — データ品質チェック
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - stats.py          — Zスコア等の統計ユーティリティ
  - audit.py          — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## 実運用上の注意
- 環境変数や API キーは厳重に管理してください（特に J-Quants / OpenAI / Slack / kabu のキー）。
- 本ライブラリはバックテスト用のデータ取得や運用自動売買の一部を提供しますが、実際の発注ロジックやリスク管理はアプリケーション側で慎重に実装してください（取り消し・再送などの運用考慮）。
- DuckDB ファイルのバックアップや排他アクセス（複数プロセスからの同時書き込み）に注意してください。
- OpenAI のレスポンスや J-Quants の API 仕様変更に備え、エラーハンドリングや SDK バージョン依存に注意してください。

---

もし README に追加したい情報（例: 実際の .env.example、テスト/CI 手順、ライセンス情報、より詳しい API 使用例）があれば教えてください。README をそれに合わせて拡張します。