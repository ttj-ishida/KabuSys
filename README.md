# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量分析・自動売買に必要な基盤処理を集約したライブラリです。主な責務は以下の通りです。

- J-Quants API を用いた株価・財務・マーケットカレンダー等の差分取得・保存（DuckDB）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・前処理・OpenAI による銘柄別 NLP スコアリング
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントを組合せ）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレースを保持する DuckDB スキーマ）
- 実行時設定は環境変数 / .env ファイルで管理（自動読み込み機能あり）

設計上の重要点：
- ルックアヘッドバイアス回避（target_date を明示、内部で date.today() を参照しない箇所が多い）
- 冪等性（DuckDB への保存は ON CONFLICT を利用）
- フェイルセーフ：API 失敗時に処理継続する設計（致命的なケースは明示的に報告）

---

## 機能一覧

- 環境設定管理（kabusys.config.settings）
  - JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY / KABU_API_PASSWORD などを取得
  - 自動でプロジェクトルートの .env / .env.local をロード（無効化可）
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar など
  - save_* 関数で DuckDB へ冪等保存
- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult に結果・品質問題・エラー情報を格納
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合を検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取り込み、URL 正規化、SSRF 対策、raw_news への保存準備
- ニュースNLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア算出（ai_scores へ保存）
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 0.7）とマクロニュースセンチメント（重み 0.3）を合成し market_regime に保存
- 研究用（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic など
  - zscore_normalize（kabusys.data.stats）でクロスセクション標準化
- 監査ログスキーマ初期化（kabusys.data.audit）
  - init_audit_schema / init_audit_db により監査用 DuckDB を初期化

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に union 型などを使用）
- インターネット接続（J-Quants / OpenAI）
- DuckDB（Python パッケージ duckdb）をインストール

1. リポジトリをチェックアウト / クローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （ない場合は最低限: pip install duckdb openai defusedxml）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` および任意で `.env.local` を置くと自動読み込みされます。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_station_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   注意:
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - settings で必須変数が要求される場合、未設定だと ValueError が出ます。

5. 初期 DB（監査ログ）を作成（任意）
   - Python から:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な例）

以下はライブラリを利用する際の簡単なコード例です。実運用ではログ設定や例外処理等を適切に追加してください。

- DuckDB 接続を作る（パスは settings.duckdb_path を利用可能）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY を使用）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（専用ファイルを作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  momentum = calc_momentum(conn, date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

注意点:
- OpenAI 呼び出しはネットワーク/レート制限の影響を受けます。API キーは OPENAI_API_KEY を設定してください。
- J-Quants はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）から id_token を取得します。settings.jquants_refresh_token を設定してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視系 SQLite パス（data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

settings オブジェクト（kabusys.config.settings）から上記をプロパティとして取得できます。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py                     — 環境変数／.env 管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py           — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント + DuckDB 保存
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETL の公開ラッパ
  - stats.py                     — zscore_normalize 等
  - quality.py                   — データ品質チェック
  - news_collector.py            — RSS 取得・前処理
  - calendar_management.py       — 市場カレンダー管理 / 営業日ロジック
  - audit.py                     — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py           — モメンタム・バリュー・ボラティリティ計算
  - feature_exploration.py       — forward returns / IC / summary
- ai/、data/、research/ の各モジュールはそれぞれの責務に沿って設計されています。

---

## 開発者向けメモ

- .env パーサはシェル風の書式（export PREFIX=val, クォート、コメント）に対応しています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- OpenAI 呼び出し部分はモック可能（ユニットテスト用に _call_openai_api をパッチ）です。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、モジュール内では空チェックを行っています。
- J-Quants クライアントはレートリミット（120 req/min）とリトライ・トークン自動リフレッシュに対応しています。

---

## ライセンス / 貢献

（このテンプレートでは明示していません。実際のプロジェクトに合わせて LICENSE ファイルを追加してください。）

---

何か追加したいセクション（例：詳しい API リファレンス、データベーススキーマ、運用手順、CI/CD 設定）や、README の翻訳・整形（英語版の併記等）があれば教えてください。