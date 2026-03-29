# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集、AI を使ったニュースセンチメント、ファクター計算、監査ログなど、アルゴリズム取引システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を持つモジュール群で構成されています。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（取得・保存・品質チェック）
- RSS を用いたニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄ごと）および市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- マーケットカレンダー管理／営業日判定
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 簡易的な設定管理（.env の自動読み込み、環境変数経由の設定）

設計上の重要点：
- ルックアヘッドバイアス回避（関数内で datetime.today()/date.today() を盲目的に使わない等）
- DuckDB を中心に SQL + Python で効率的に処理
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える
- 冪等性を重視（DB への保存は ON CONFLICT などで重複を吸収）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save の一連）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（fetch_rss, 前処理、保存ロジック）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとの ai_score を生成して ai_scores に書き込む）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースを合成して regime を判定）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）

---

## 必要条件（例）

- Python 3.10+
- duckdb
- openai
- defusedxml

実際の利用では openai SDK のバージョンやその他依存をプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. ソースをチェックアウト／配置

2. 仮想環境を作成して有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   代表的な依存例：

   ```bash
   pip install duckdb openai defusedxml
   ```

   パッケージ化されている場合：

   ```bash
   pip install -e .
   ```

4. 環境変数を準備する

   プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（CWD に依存せず package 内からプロジェクトルートを探索します）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（主なもの）:

   - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しに使う場合（ai モジュールで参照）
   - その他:
     - KABUSYS_ENV: development | paper_trading | live（省略時 `development`）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: デフォルトは `data/kabusys.duckdb`
     - SQLITE_PATH: デフォルトは `data/monitoring.db`

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   KABUSYS_ENV=development
   ```

---

## 使い方（クイックスタート）

以下は主要機能の簡単な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- 監査ログ DB を初期化する

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- 日次 ETL を実行する

  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に保存する

  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジームを判定して market_regime に保存する

  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- J-Quants の ID トークンを取得（内部で環境変数の refresh token を参照）

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()
  print(token)
  ```

- RSS を取得（ニュース収集の単体テストなど）

  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- AI 関連（score_news / score_regime）は OpenAI API キーが必要です。引数で api_key を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL 系は J-Quants のトークンが必要になります（JQUANTS_REFRESH_TOKEN 環境変数）。

---

## 設定（環境変数の仕様）

- 自動 .env 読み込み
  - パッケージ初期化時に `.env` と `.env.local` をプロジェクトルートから自動読み込みします（OS 環境変数を優先）。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 主な設定キー（settings 経由でアクセス可）
  - settings.jquants_refresh_token <- JQUANTS_REFRESH_TOKEN（必須）
  - settings.kabu_api_password <- KABU_API_PASSWORD（必須）
  - settings.kabu_api_base_url <- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - settings.slack_bot_token <- SLACK_BOT_TOKEN（必須）
  - settings.slack_channel_id <- SLACK_CHANNEL_ID（必須）
  - settings.duckdb_path <- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - settings.sqlite_path <- SQLITE_PATH（デフォルト: data/monitoring.db）
  - settings.env <- KABUSYS_ENV（development / paper_trading / live）
  - settings.log_level <- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## ディレクトリ構成

主要ファイル / モジュールの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py            # 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py        # ニュースセンチメント（score_news）
    - regime_detector.py # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  # J-Quants API クライアント（fetch/save 等）
    - pipeline.py        # ETL パイプライン（run_daily_etl など）
    - news_collector.py  # RSS ニュース収集
    - calendar_management.py # マーケットカレンダー管理 / 営業日ロジック
    - quality.py         # データ品質チェック
    - stats.py           # 統計ユーティリティ（zscore_normalize）
    - etl.py             # ETLResult エクスポート
    - audit.py           # 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py # calc_forward_returns, calc_ic, factor_summary, rank

（上記はリポジトリ内の主要なモジュールを抜粋したものです）

---

## 運用上の注意

- OpenAI / J-Quants などの外部 API キーは厳重に管理してください。`.env` ファイルはバージョン管理に含めないでください。
- DuckDB ファイルや監査 DB のバックアップ、アクセス権限管理を検討してください。
- `KABUSYS_ENV` を `live` にした場合は発注や本番用処理が有効になる想定です。paper_trading / development と明確に切り替えて運用してください。
- ETL・API 呼び出しにはレート制限・リトライが実装されていますが、負荷や料金に注意してスケジューリングしてください。

---

## 貢献・拡張

- 新しいデータソースの追加（jquants_client に類似の保存インターフェースを実装）
- 取引実行部分（execution）や監視（monitoring）モジュールの拡張
- AI プロンプト改善やモデルの差し替え（news_nlp / regime_detector）

---

もし README に追加したい具体的なコマンドやサンプル（例：systemd タイマー、Airflow DAG、CI 設定など）があれば教えてください。必要に応じてサンプル .env.example や運用手順も作成します。