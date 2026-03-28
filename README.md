# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュース収集・NLP（OpenAI 連携）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダートレース）などを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス回避（日時の自動参照を避け、target_date を明示的に渡す）
- DuckDB を中心とするローカルデータストア
- J-Quants API / OpenAI / RSS 等の外部依存は明示的に扱う（リトライ・レートリミット等の考慮あり）
- 冪等性（ON CONFLICT / UUID 等）とフェイルセーフを重視

---

## 機能一覧

- data
  - ETL パイプライン（prices, financials, market calendar）の差分取得・保存（J-Quants）
  - J-Quants API クライアント（リトライ・レートリミット・トークン自動リフレッシュ）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF/サイズ制限/トラッキング除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai
  - ニュース NLP（gpt-4o-mini を利用した銘柄別センチメント、JSON Mode 対応、バッチ処理・リトライ）
  - 市場レジーム判定（ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントを重み付け合成）
- research
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- config
  - 環境変数の読み込み (.env/.env.local 自動読み込み、無効化フラグあり) と Settings API

---

## 必要条件（推奨）

- Python 3.10+（typing の一部に新しい型構文を使用）
- pip
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

requirements.txt は本リポジトリに含まれていない想定のため、以下のようにインストールしてください:

例:
pip install duckdb openai defusedxml

（プロジェクトによっては追加のパッケージが必要になる可能性があります）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - ルートに pyproject.toml/.git があれば、config の自動 .env ロードが有効になります

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` に設定できます（自動読み込みの優先度: OS 環境 > .env.local > .env）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD     : kabu ステーション API 用パスワード（必要時）
     - KABU_API_BASE_URL     : kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知がある場合
     - DUCKDB_PATH           : デフォルトデータベースパス（data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG/INFO/...（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env 読み込みを無効化

   - 自動ロードを無効にしたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。

5. DB ディレクトリ作成（必要なら）
   - デフォルトの DUCKDB_PATH の親ディレクトリを作成しておくと安全です（例: mkdir -p data）

---

## 使い方（代表的な例）

以下は Python から直接呼び出す簡単な例です。各サンプルでは duckdb パッケージを用いた接続を使用します。

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得と品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（AI による銘柄別センチメント）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written scores: {written}")
  ```

- 市場レジーム判定を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_kabusys.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- マーケットカレンダーの夜間更新ジョブ（単体）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved calendar records: {saved}")
  ```

注意点
- OpenAI 呼び出しには API コストとレート制限があります。API キーは安全に管理してください。
- ETL/AI 呼び出しは外部 API に依存するため、ネットワーク・API キーの設定が正しいことを確認してください。
- 関数は設計上ルックアヘッドバイアスを避けるため target_date を明示的に受け取ります。内部で現在時刻に依存する処理は最小化されています。

---

## .env パースと自動読み込み挙動

- config モジュールはリポジトリルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。
- 読み込み優先度:
  - OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト等で利用）。
- .env のパースは典型的な KEY=VAL 形式をサポートし、export プレフィックス・クォート・インラインコメントなどに対応しています。

---

## 主要モジュールの API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.env, settings.duckdb_path などのプロパティを提供

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult クラス（結果の要約）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token()

- kabusys.data.news_collector
  - fetch_rss(url, source) など（RSS の取得と前処理）

- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date, spike_threshold)
  - 各チェック関数（check_missing_data, check_spike, ...）

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(path)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats 経由）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py (ETL 前面 API)
  - pipeline.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (パブリック ETL インターフェース再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research modules: calc_* / feature exploration etc.

ファイルごとの責務は各モジュールのドキュメント文字列（docstring）に記載されています。

---

## 運用上の注意

- 本システムは実運用での発注機能を含む想定があります。実際に発注する前に paper_trading 環境で十分にテストしてください（KABUSYS_ENV を paper_trading に設定）。
- OpenAI / J-Quants／証券会社 API のキーは環境変数で管理し、ログやソース管理に残さないでください。
- ETL 実行や AI スコアリングは外部 API 呼び出しのため、適切なエラーハンドリング・再実行・監視が必要です。
- DuckDB ファイルのバックアップや整理（パージ方針）を運用ポリシーとして定めてください。

---

## 参考・テスト操作

- 自動 .env 読み込みを無効にして単体テストを実行する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しのモック
  - テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch して外部呼び出しを差し替えられる設計です。

---

この README はコードベースの主要機能と使い始めの手順をまとめたものです。詳細な実装や追加ユーティリティは各モジュールの docstring を参照してください。必要であれば、セットアップの例や運用手順書（cron / GitHub Actions での ETL 定期実行例 など）も追記できます。