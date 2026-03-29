# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
J-Quants / OpenAI / kabuステーション 等と連携して、データの ETL、ニュース NLP、ファクター計算、監査ログの管理、マーケットカレンダー管理などを提供します。

## 主な特徴
- ETL パイプライン（市場カレンダー / 日足価格 / 財務データ）の差分取得と保存（J-Quants API）
- ニュース収集（RSS）と LLM による銘柄センチメント（ai_scores）生成（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量探索（IC, forward returns 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化・管理（DuckDB）
- J-Quants API クライアント（レート制御・自動トークンリフレッシュ・リトライ実装）
- セキュアな RSS 取得（SSRF 対策、サイズ制限、XML パーサの安全化）

---

## 機能一覧（モジュール別概要）
- kabusys.config
  - .env / 環境変数の自動読み込み（.git や pyproject.toml を基準にプロジェクトルートを探索）
  - settings オブジェクト経由で設定値を参照（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（利用箇所）など）
- kabusys.data
  - jquants_client: J-Quants API 取得/保存関数、rate-limiter、id_token 管理
  - pipeline: run_daily_etl 等の ETL パイプライン、ETLResult
  - news_collector: RSS から raw_news 取得（SSRF・サイズ制限・トラッキング除去）
  - calendar_management: market_calendar 管理、営業日判定ユーティリティ
  - quality: データ品質チェック（missing / spike / duplicates / date_consistency）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ用テーブル初期化（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 指定ウィンドウの記事を統合して銘柄ごとのセンチメントを生成し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュース（LLM）を使って market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（prices_daily, raw_financials を参照）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件
- Python >= 3.10
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセスが必要）
  - J-Quants API へのアクセス（JQ トークン）
  - OpenAI API キー（ニュース NLP / レジーム判定で使用）

パッケージのインストール例:
```bash
python -m pip install duckdb openai defusedxml
# またはプロジェクトが pip パッケージ化されていれば
# pip install -e .
```

---

## 環境変数 / .env
プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` と `.env.local` を自動で読み込みます（OS 環境変数優先、.env.local は上書き）。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数で上書き可能）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネルID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます（テスト等で利用）

例 `.env`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（手順例）
1. Python と依存パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # requirements.txt がない場合:
   python -m pip install duckdb openai defusedxml
   ```

2. プロジェクトルートに `.env` を作成（上のサンプルを参照）
   - 開発時に `.env.local` を使ってローカル設定を上書きできます。

3. DuckDB ファイル用ディレクトリを用意（DUCKDB_PATH の親ディレクトリ）
   ```bash
   mkdir -p data
   ```

4. （任意）監査用 DB を初期化
   - Python REPL / スクリプトで:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # 返り値は初期化済みの duckdb 接続
     ```

---

## 使い方（主要な API 例）
以下は代表的なユースケースのコード例です。各関数は duckdb.DuckDBPyConnection を受け取ります。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー、価格、財務、品質チェック含む）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（指定日ウィンドウの記事を集約して ai_scores を書き込む）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を明示するか、環境変数 OPENAI_API_KEY を設定
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込んだ銘柄数: {n}")
  ```

- 市場レジーム判定（1321 MA200乖離 + マクロニュース）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- ファクター計算（モメンタム等）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

- 監査ログスキーマの初期化（既存接続に追加する場合）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- RSS 取得（news_collector のユーティリティ）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

---

## 注意点 / 実装上の設計方針（重要）
- ルックアヘッドバイアス防止:
  - AI スコア生成・レジーム判定・ETL などは内部で date.today()/datetime.today() を直接参照しないように設計されています。必ず target_date を明示して呼び出すか、モジュールの `target_date` を使ってください。
- .env 読み込み:
  - 自動読み込みはプロジェクトルート探索に依存します。テストから読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し:
  - API リトライ、レート制御、JSON モードなどを考慮した実装になっています。APIキーは引数で注入可能（テスト容易性のため）。
- J-Quants クライアント:
  - レート制御（120 req/min）、トークン自動リフレッシュ、リトライ（指数バックオフ）を実装しています。
- セキュリティ:
  - RSS 収集は SSRF 対策（リダイレクト時の検査、プライベート IP 判定）、XML パーサに defusedxml を使用、受信サイズ制限あり。

---

## ディレクトリ構成（簡易）
（ソースが `src/kabusys` 配下にある想定）

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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (その他: strategy/, execution/, monitoring/ が将来のモジュール候補として存在)

各ファイルは README の該当セクションで説明した責務を持ちます（ETL・NLP・研究・データ品質・監査ログ等）。

---

## トラブルシュート / よくある質問
- .env が読み込まれない
  - プロジェクトルートに `.git` または `pyproject.toml` があるか確認してください。自動読み込みを無効にしている場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。
- OpenAI / J-Quants API 呼び出しでエラーが出る
  - API キー/トークンが正しく設定されているか、ネットワークからアクセスできるか、レート制限に引っかかっていないかを確認してください。J-Quants はレート制限（120 req/min）を守る設計です。
- DuckDB にテーブルがない
  - 初回は ETL を実行する前にスキーマ作成処理が必要です（別スクリプトや migrations を用意している場合はそちらを利用）。監査用は `init_audit_schema` / `init_audit_db` を使用してください。

---

README に書かれている使い方は主要な API の呼び方と設計方針を簡潔にまとめたものです。具体的な運用スクリプト（定期バッチやワーカー、発注ロジックなど）はこのライブラリを組み合わせて実装してください。必要であれば、利用シナリオ別の具体的なサンプルや運用手順（systemd/cron/コンテナ化など）を追加で作成します。必要な場合は教えてください。