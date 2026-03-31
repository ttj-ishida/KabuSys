# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP、LLM を使った市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマの初期化などを提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 必要な環境変数（設定）
- 使い方（主要 API の例）
- ディレクトリ構成（主要ファイルの説明）
- 開発 / テストに関するメモ

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データ基盤構築を支援する Python モジュール群です。  
主に次を目的としています:

- J-Quants API からの市場データ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたローカルデータベース保存（冪等保存）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集・前処理・LLM による銘柄別センチメント算出
- マーケットレジーム判定（ETF の MA と LLM センチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマの初期化

設計上の特徴として、Look-ahead バイアス防止、冪等性、エラー耐性（リトライ／フォールバック）を重視しています。

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants との呼び出し、取得データの DuckDB への保存関数
  - pipeline: 日次 ETL（run_daily_etl）および個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 取得・前処理・raw_news への保存補助
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査ログテーブルの DDL／初期化ヘルパー
  - stats: z-score 正規化ユーティリティ
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントを LLM（gpt-4o-mini）で算出して ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime を算出
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: 将来リターン、IC 計算、統計サマリー、ランク変換など
- config:
  - Settings クラスによる環境変数ベースの設定管理（.env 自動読み込み機構付き）

---

## セットアップ手順

推奨 Python バージョン: 3.10 以上（Union 型記法や型ヒントのため）

1. リポジトリをクローン（あるいはプロジェクトルートに移動）
2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - 必須ライブラリ（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - ソースを編集して開発する場合:
     ```
     pip install -e .
     ```
     （プロジェクトに pyproject.toml / setup.cfg があることを想定しています）

4. 環境変数を設定
   - 下記「必要な環境変数」を参照して .env を作成するか、OS 環境変数に設定してください。
   - パッケージはプロジェクトルートの .env / .env.local を自動で読み込みます（無効化可）。

---

## 必要な環境変数（設定）

kabusys.config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live （デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

.env 自動ロード:
- モジュール import 時にプロジェクトルート（.git または pyproject.toml を基準）から .env, .env.local を自動読み込みします。
- 無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: Settings の一部プロパティは設定が必須で、未設定の場合 ValueError を投げます（重要な外部 API キー等）。

---

## 使い方（主要 API の例）

以下は主要なユースケースの簡単なコード例です。

- DuckDB 接続を作り日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を計算して ai_scores に書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
  print(f"wrote {n_written} scores")
  ```

- 市場レジーム判定を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
  ```

- 監査ログ用の DuckDB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- RSS を取得する（news_collector の低レベル関数）:
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注: OpenAI を使う関数は api_key 引数を受け取るので、環境変数を直接使いたくない場合は明示的に渡せます。

---

## ディレクトリ構成（主なファイルと役割）

（ソースルート: src/kabusys 以下）

- __init__.py
  - パッケージエクスポート: data, strategy, execution, monitoring（strategy 等は別モジュールで追加想定）
- config.py
  - Settings: 環境変数取得、.env 自動読み込みロジック
- ai/
  - __init__.py: score_news を公開
  - news_nlp.py: ニュースを銘柄ごとに集約して LLM に送り ai_scores に保存
  - regime_detector.py: ETF(1321) の MA200 乖離と LLM マクロセンチメントを合成して market_regime に保存
- data/
  - __init__.py
  - jquants_client.py: J-Quants API との通信、取得・保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl, ...）、ETLResult データクラス
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector.py: RSS 収集・前処理・保存補助（SSRF 対策・トラッキング除去等）
  - calendar_management.py: 市場カレンダー管理／営業日判定
  - audit.py: 監査ログテーブル DDL と初期化ヘルパー
  - stats.py: z-score 正規化など汎用統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

（strategy, execution, monitoring モジュールはパッケージ __all__ に含めていますが、このスナップショットでは省略されている場合があります）

---

## 開発 / テストに関するメモ

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し等は外部 API に依存するため、ユニットテストでは該当関数（内部の _call_openai_api など）をモックしてテストする設計になっています。
- DuckDB の executemany に空リストを渡すとエラーになる（特に 0.10 系）ため、コード中では空チェックを行っています。
- news_collector は SSRF 対策や Content-Length / サイズ制限、defusedxml を用いた安全な XML パースを実装しています。外部 RSS の取得はネットワークエラー等が起きる前提で例外処理されます。

---

何か特定の使い方（例: ETL の cron 設定、kabuステーションとの注文フロー実装、戦略テンプレート）について README を拡張したい場合は、用途に応じて追加サンプルや設定例を作成します。どの部分を詳しく知りたいですか？