# KabuSys

日本株向け自動売買 / データパイプライン / 研究ライブラリのモノリポジトリ。  
DuckDB をデータレイクに、J-Quants / RSS / OpenAI を用いてデータ収集・品質チェック・NLP スコアリング・市場レジーム判定・ファクター計算・監査ログを提供します。

---

## プロジェクト概要

KabuSys は以下の目的をもつコンポーネント群を含みます。

- データ収集（J-Quants API）と ETL（prices / financials / market calendar）
- ニュース収集（RSS）と NLP（OpenAI）による銘柄別センチメントスコア化
- 市場レジーム判定（ETF MA + マクロニュース）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 実行環境設定のための環境変数管理

設計上の特徴：
- DuckDB を中心とした SQL ベースの処理（外部依存を最小化）
- Look-ahead バイアス防止のため日時取得や DB クエリに配慮
- API 呼び出しは冪等・リトライ・レート制御を実装
- OpenAI とのやりとりは JSON Mode 等を利用して厳密なパースを想定

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）
  - settings オブジェクトによる設定取得（トークン・パス・環境等）
- kabusys.data
  - jquants_client: J-Quants API の取得・保存機能（差分取得、ページネーション、保存の冪等性）
  - pipeline / etl: 日次 ETL 実行（run_daily_etl 等）
  - news_collector: RSS 取得と raw_news への保存（SSRF 対策、URL 正規化）
  - calendar_management: 市場カレンダーおよび営業日判定ユーティリティ
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査ログテーブル定義・初期化、監査DB初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321)の MA とマクロニュースを組合せて市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提:
- Python 3.9+（typing の記法に合わせて適宜）
- Git でプロジェクトルートが存在（.env 自動ロード機能はプロジェクトルートを探索します）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール（最低限）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （必要に応じて他の依存を追加）
   - プロジェクトに pyproject.toml や setup があれば: pip install -e .
4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（主要）:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注等）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - 任意:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
   - 簡易 .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
5. DB ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単なコード例）

以下は Python REPL やスクリプトからの利用例です。

- DuckDB 接続を作って ETL を実行（デイリーパイプライン）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリングを実行（OpenAI API キーは環境変数か引数で指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20))
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 環境変数自動ロードをテストで無効化する
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## よく使う API（概要）

- ETL / data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl

- データ品質 / data.quality
  - run_all_checks(conn, target_date=None, ...)

- ニュース収集 / data.news_collector
  - fetch_rss(url, source) など（RSS 取得ユーティリティ）

- AI / kabusys.ai
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)

- 監査ログ / data.audit
  - init_audit_db(path) / init_audit_schema(conn)

- J-Quants クライアント / data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token(refresh_token=None)

---

## ディレクトリ構成（主なファイル）

（パッケージは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / .env 自動読み込み / settings
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLP（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント・保存処理
    - pipeline.py                   - ETL 実行ロジック（run_daily_etl 等）
    - etl.py                        - ETLResult の公開
    - news_collector.py             - RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py        - マーケットカレンダー管理・営業日判定
    - quality.py                    - データ品質チェック
    - stats.py                      - 統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（momentum/value/volatility）
    - feature_exploration.py        - 将来リターン / IC / ランク / summary
  - research and other modules...
- pyproject.toml or setup.py (存在すればビルド/インストール情報)

各モジュールは docstring と詳細な設計方針を含み、ユニットテストおよび本番運用を意識した実装スタイルになっています。

---

## 運用上の注意

- OpenAI や J-Quants の API キーは漏洩しないよう適切に管理してください。
- ETL 実行中はネットワーク・API レート制限に注意（jquants_client は内部でレート制御を行います）。
- 本リポジトリ内の関数は Look-ahead バイアス防止に配慮していますが、バックテスト環境で使用する場合はデータ投入タイミングに注意してください（fetch 時刻情報等）。
- DuckDB の executemany に空リストを与えるとエラーとなるバージョン差異があるため、関連処理では空チェックが実装されています。

---

必要であれば、README に以下を追加できます：
- CI / テスト実行方法（pytest など）
- 具体的な .env.example ファイル
- デプロイ / 運用スケジュール例（cron / Airflow / GitHub Actions）
- スキーマ定義（DDL の抜粋）や SQL サンプル

どの内容を追加したいか教えてください。