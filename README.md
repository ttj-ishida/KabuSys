# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログなど、取引アルゴリズム開発と運用に必要な主要機能を含みます。

---

## 概要

KabuSys は以下の機能を組み合わせて日本株の自動売買パイプラインを構築するためのモジュール群です。

- J-Quants API を利用した株価・財務・カレンダーの差分 ETL（DuckDB への保存・品質チェック）
- RSS ベースのニュース収集（SSRF / サイズ制限等の安全対策付き）
- OpenAI を用いたニュースセンチメント（銘柄別）およびマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム／ボラティリティ／バリュー等）とリサーチユーティリティ（IC や統計サマリ）
- 監査（audit）テーブル群の初期化・管理（シグナル→発注→約定のトレーサビリティ）
- 環境変数・設定管理（.env 自動読み込み）

設計方針として、ルックアヘッドバイアスの回避、冪等性、フェイルセーフ（API 失敗時の継続）、DuckDB を中心とした SQL 主導の処理を重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、ページネーション、保存関数）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・正規化・raw_news への保存ロジック）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI に問い合わせ、ai_scores へ書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュース LLM の混合で市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - .env 自動読み込み（プロジェクトルート検知）と Settings クラス（必須環境変数チェック）
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の | 型注釈を利用）
- 必須 Python パッケージ（代表）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそちらを参照してください。最低限上記パッケージは必要です。）

---

## セットアップ手順

1. リポジトリをクローン（例）:

   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成・有効化:

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール（例）:

   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください:
   pip install -r requirements.txt

4. 環境変数の準備

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると、kabusys.config が自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例 `.env`（必須項目は用途に応じて設定）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   - 必須（利用機能に応じて）:
     - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack通知を使う場合
     - OPENAI_API_KEY: ai.score_news / regime_detector の呼び出しに必要
     - KABU_API_PASSWORD / KABU_API_BASE_URL: kabuステーション API を利用する場合

5. データベース・ディレクトリの準備

   デフォルトでは DUCKDB ファイルは `data/kabusys.duckdb`、監視用 SQLite は `data/monitoring.db` を参照します。`.env` で上書き可。必要に応じてディレクトリを作成してください。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトからの利用例です。

- DuckDB 接続を作り ETL を実行する:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）を実行:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")

- 市場レジームスコアを計算して保存:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 研究用ファクター計算:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])

- 監査 DB 初期化（監査テーブルを作成）:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査ログ書き込み/参照が可能

注意点:
- LLM 呼び出しには OPENAI_API_KEY が必要です。api_key を関数引数で明示的に渡すことも可能です。
- 全てのモジュールはルックアヘッドバイアスを避ける設計（target_date を明示して処理）です。バックテスト等で date を固定して使ってください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須：ETL で J-Quants を使う場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文処理を行う場合）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知設定
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（sqlite）パス（data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化します（テスト用）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py (パッケージ定義・バージョン)
- config.py (環境変数管理 .env 自動読み込み、Settings)
- ai/
  - __init__.py
  - news_nlp.py (ニュースセンチメントの取得・ai_scores 書き込み)
  - regime_detector.py (ETF MA とマクロ LLM を合成した市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント、保存関数)
  - pipeline.py (ETL パイプライン / run_daily_etl)
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py (RSS 取得・正規化・SSRF 対策)
  - calendar_management.py (市場カレンダー管理、営業日判定)
  - quality.py (データ品質チェック)
  - stats.py (zscore_normalize 等の統計ユーティリティ)
  - audit.py (監査ログスキーマ初期化)
- research/
  - __init__.py
  - factor_research.py (モメンタム/バリュー/ボラティリティ)
  - feature_exploration.py (forward returns / IC / summary)

その他: パッケージ外にドキュメントや CI 設定があればリポジトリルートに配置します。

---

## テスト・開発時のヒント

- モジュール内部の外部 API 呼び出し（OpenAI や HTTP）には注入ポイントや内部ラッパーがあり、unittest.mock で差し替え可能（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- .env の自動読み込みはプロジェクトルートの検出に基づき行われます。テストで影響を避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany は空パラメータリストを受け付けない箇所があるため、モジュール内でも空チェックを行っています。テスト時も注意してください。

---

## 補足

- 本 README はコードベースの公開 API と設計ノートに基づき作成しています。実運用では接続先 URL、API トークンの管理、監査・ログの運用・バックテスト用データ分離等を慎重に設計してください。
- ライセンスや実装上の責任範囲はリポジトリのルートにある LICENSE や CONTRIBUTING を参照してください（存在する場合）。

---

ご要望があれば、README に含めるサンプル .env.example や requirements.txt の候補、よく使う CLI スクリプト例（ETL を cron/Cloud Scheduler で実行する方法等）も作成します。どの形式（短いサンプル / 詳細手順）が良いか教えてください。