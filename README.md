# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ（KabuSys）。  
ETL・データ品質チェック・ニュース収集・AIによるニュースセンチメント解析・市場レジーム判定・監査ログ（トレーサビリティ）など、量的運用・研究・実行層で必要となるユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部向けライブラリです。

- J-Quants API からの株価・財務・カレンダーデータ取得と DuckDB への差分ETL
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ベースのニュース収集と前処理（SSRF対策・トラッキング除去）
- OpenAI を使ったニュースセンチメント（銘柄別）および市場レジーム判定
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- 研究用ファクター計算・前方リターン計算・IC 計測などのユーティリティ

設計方針としては、Look-ahead バイアス回避、冪等性（ETL保存時 ON CONFLICT）、外部呼出しのリトライ/バックオフ、テスト可能性（API呼び出し差し替えポイント）を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - ニュース収集（RSS fetch, preprocessing, 保存ロジック）
  - 監査（init_audit_schema / init_audit_db）
  - 統計ユーティル（zscore_normalize）
- ai
  - score_news: ニュース（raw_news/news_symbols）から銘柄別センチメントを生成して ai_scores に保存
  - score_regime: ETF（1321）の MA200 乖離とニュースマクロセンチメントを合成して market_regime に保存
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）

---

## 要件

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準モジュール: urllib, json, datetime など

（実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt することを推奨します）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime を使う場合）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視DB等（data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他監視関連

   .env の自動読み込み順序: OS 環境変数 > .env.local (> .env)。プロジェクトルートは .git か pyproject.toml を基準に探索します。

4. DuckDB ファイルや出力ディレクトリの作成
   - デフォルトでは data/ 以下に DB や PID ファイルを作成します。必要なディレクトリを作成しておくと良いです。

---

## 使い方（簡単なコード例）

以下はライブラリの主要な使い方例です。実行前に環境変数を設定してください。

- ETL（日次パイプライン実行）
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース（銘柄別）センチメント評価（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"ai_scores に書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査DBの初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests 等を記録できます
  ```

- カレンダー問い合わせ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- AI を呼ぶ箇所（score_news / score_regime）は OpenAI API キーが必要です。api_key 引数から直接渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API は rate limit（120 req/min）や認証のリフレッシュに対応しています。JQUANTS_REFRESH_TOKEN を設定してください。

---

## 設定 (.env) の例

以下は最低限の例（実際の値に置き換えてください）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env ファイルは .env と .env.local の二段階で読み込まれます。OS 環境変数を優先します。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 管理（自動 .env ロード機能、必須変数チェック）
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news → ai_scores に銘柄別センチメントを書き込む。OpenAI (gpt-4o-mini) を JSON mode で利用。
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に記録。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API との通信（fetch/save）、認証、レートリミッタ、ページネーション、DuckDB への保存処理を提供。
    - pipeline.py
      - run_daily_etl 等の ETL パイプライン、ETLResult クラス。
    - calendar_management.py
      - 市場カレンダーの管理、営業日判定、calendar_update_job。
    - news_collector.py
      - RSS 取得・前処理・SSRF 対策・記事ID正規化（SHA-256）等。
    - quality.py
      - データ品質チェック群（欠損、重複、スパイク、日付不整合）。
    - stats.py
      - zscore_normalize などの統計ユーティリティ。
    - audit.py
      - 監査ログスキーマのDDL・初期化（signal_events / order_requests / executions）。
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility 計算
    - feature_exploration.py
      - forward returns / IC / factor_summary / rank

---

## 運用メモ / 注意事項

- Look-ahead バイアス防止:
  - 各種関数は date.today() を直接参照しない（呼び出し側が target_date を指定する設計）。
  - ETL・AI のスコアは明示的な target_date を使うことを推奨します。
- 冪等性:
  - save_* 関数は ON CONFLICT / INSERT … DO UPDATE により冪等に動作します。
  - ニュース記事は正規化 URL の SHA-256 で ID を生成し冪等保存。
- リトライ・フェイルセーフ:
  - 外部API呼び出し（J-Quants / OpenAI）は共通的なリトライ・バックオフを実装しています。
  - AI の失敗時はスコアを 0 にフォールバックする設計の箇所があります（フェイルセーフ）。
- テスト:
  - OpenAI 呼び出し点は内部でラップしてあり、ユニットテスト時にモック差し替えしやすく設計されています。

---

## 貢献 / 拡張案

- 追加のニュースソースを DEFAULT_RSS_SOURCES に登録して収集対象を拡張できます。
- モデル設定（使用モデル、温度、バッチサイズ）を config から外だしして運用中に調整できるようにすると便利です。
- ETL のスケジューリング（cron / Airflow / GitHub Actions）や監視（LINE 通知等）を組み合わせて運用する想定です。

---

もし README にサンプルの .env.example、requirements.txt、または実行用スクリプト（cli）を追加したい場合は、既定の内容を元にテンプレートを作成します。必要であれば教えてください。