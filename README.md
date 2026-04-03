# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、ファクター研究、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は、日本株の定量分析・自動売買基盤を構成するためのモジュール群です。主要機能は以下のとおりです。

- J-Quants API を用いた株価・財務・上場銘柄・市場カレンダーの差分取得と DuckDB への保存（ETL）
- RSS からのニュース収集と前処理、記事と銘柄の紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- ETF（1321）の MA とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロード機能あり）

パッケージは `src/kabusys` 以下に実装されています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / ページネーション / リトライ / レート制御）
  - pipeline: ETL パイプライン（run_daily_etl など）
  - news_collector: RSS 取得と前処理（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（複数のチェックをまとめて実行）
  - audit: 監査ログスキーマの作成・初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM を組み合わせた市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提: Python 3.10 以上を推奨（typing で `X | Y` を使用）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なパッケージ（主なもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt、または pip install -e .）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、`kabusys.config` が自動で読み込みます（ルートは .git または pyproject.toml を基準に検出）。
   - 自動ロードを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（利用する場合）
   - OPENAI_API_KEY: OpenAI を使う場合は設定（score_news / score_regime 呼び出し時に引数で渡すことも可能）
   - そのほか任意:
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等（defaults あり）

6. データディレクトリ作成
   - デフォルトでは data/ に duckdb 等を保存します。必要に応じて作成:
     - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト上での利用例です。

- 基本設定読み込み
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで参照できます。
  - .env.example を用意して `.env` を作成してください（プロジェクトに合わせて値を設定）。

- DuckDB 接続と日次 ETL 実行
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュースセンチメントのスコアリング（ai.news_nlp）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    n = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
    print(f"scored {n} codes")

  - api_key を None にすると環境変数 OPENAI_API_KEY を利用します。

- 市場レジーム判定（ai.regime_detector）
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- ファクター計算（research）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    volatility = calc_volatility(conn, target_date=date(2026,3,20))
    value = calc_value(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # init_audit_schema は内部で実行されます

- ニュース RSS 取得（ニュースコレクタ）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    # 取得した記事を raw_news に保存する処理はアプリ側で実装してください

注意点:
- OpenAI 呼び出しはリトライ・フォールバック機構がありますが、APIキーの設定や料金に注意してください。
- ETL / AI 呼び出しは、バックテスト等でルックアヘッドバイアスが起きないよう設計されています（関数は target_date 引数を明示的に受け取ります）。

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）。
- KABU_API_PASSWORD: kabuステーション API のパスワード（利用する場合）。
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するには 1 を設定

設定は kabusys.config.Settings を通して参照できます。`.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。

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
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit (schema utilities inside audit.py)
  - (その他モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージ宣言のみの想定)
- strategy/ (戦略層は別途実装想定)
- execution/ (注文実行・ブローカー連携は別途実装想定)

補足:
- データベーススキーマ定義やテーブル作成は各モジュール（例: audit.init_audit_schema）で行います。
- jquants_client は API 呼び出し・保存機能を提供しますが、実際のテーブル作成スクリプトは別実装を想定しています（プロジェクト内の schema 初期化ユーティリティを参照してください）。

---

## 開発・拡張メモ

- DuckDB を用いて高速な列指向クエリを実行します。ETL/分析処理は基本的に SQL + 最小限の Python ロジックで実装されています。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）で厳密な JSON を期待する設計ですが、実際に余分な前後テキストが混入する場合のフェイルセーフが組み込まれています。
- J-Quants クライアントはレート制御・認証トークン自動リフレッシュ・リトライを備えています。
- ニュース収集は SSRF 対策（リダイレクト検査・プライベートホスト拒否）や最大受信サイズ制限、トラッキングパラメータ除去などを実装しています。

---

もし README に追加したいサンプルスクリプト（例: ETL cron スクリプト、データベース初期化スクリプト、CI / テスト手順等）があれば、その用途に合わせて追記用のテンプレートを作成します。必要な内容を教えてください。