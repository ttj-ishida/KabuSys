# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータレイヤに使い、J‑Quants や RSS / OpenAI（LLM）を組み合わせて以下を実現します：

- データ ETL（株価・財務・マーケットカレンダー）の差分取得と保存（J-Quants）
- ニュース収集・前処理・銘柄紐付け（RSS）
- ニュースセンチメント（LLM）による銘柄別スコアリング
- マクロニュース + ETF MA200 による市場レジーム判定（LLM）
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（信号 → 発注 → 約定）のスキーマ初期化ユーティリティ

バッチ処理と研究用途の双方で利用できる設計になっています。Look-ahead バイアス回避や API リトライ／レート管理、冪等性（ON CONFLICT）等に注意して実装されています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存）
  - ニュース収集（RSS 正規化・SSRF 対策・前処理）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - 品質チェック（missing / spike / duplicates / date_consistency）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 一般統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを LLM で銘柄別にスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research
  - calc_momentum / calc_volatility / calc_value（ファクター算出）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析支援）
- config
  - Settings クラスによる環境変数管理（.env 自動ロード, 必須値チェック）

---

## セットアップ手順

前提
- Python 3.9+ を想定（プロジェクトの pyproject.toml を参照してください）
- DuckDB, OpenAI SDK, defusedxml などが必要

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。
   - 例（最低限の依存）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発中はローカルeditableインストール:
     ```
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を作成してください（.env.example を参考に）。
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順に優先されます。
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で便利）。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J‑Quants リフレッシュトークン（必須）
     - SLACK_BOT_TOKEN : Slack 通知に使うトークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
     - KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime を実行する際に必要）
   - 任意 / デフォルト
     - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 で自動 .env ロードを無効化
     - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH : data/monitoring.db（デフォルト）
     - KABU_API_BASE_URL : kabuAPI の base URL（デフォルト http://localhost:18080/kabusapi）

---

## 使い方（簡単な例）

以下は Python スクリプト/REPL での利用例です。

- 設定値の取得
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- DuckDB 接続の作成と日次 ETL 実行
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))  # path は settings.duckdb_path を使うのが便利
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメント・スコアリング
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数、または api_key 引数で与えられます
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} symbols")
  ```

- 市場レジーム判定
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（独立 DB にする場合）
  ```py
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って監査テーブルにアクセス可能
  ```

- ニュース RSS を取得（単体）
  ```py
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注意点
- OpenAI 呼び出しは課金対象です。開発・テスト時はモック（unittest.mock.patch）して _call_openai_api を差し替えてください。score_news と regime_detector は内部で同名のラッパーを持ち、テスト用に patch 可能です。
- ETL は外部 API（J-Quants）を呼びます。テストでは get_id_token 等をモックすることを推奨します。
- DuckDB への多数レコード挿入時は executemany によるチャンク処理が行われています。空の params で executemany を呼ばないよう注意しています。

---

## ディレクトリ構成（主要ファイル）

リポジトリの重要な部分のみ抜粋しています（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                         -- 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py                     -- ニュースセンチメント（score_news）
      - regime_detector.py              -- 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py               -- J-Quants API クライアント + 保存
      - pipeline.py                     -- ETL (run_daily_etl, run_prices_etl...)
      - etl.py                          -- ETLResult の再エクスポート
      - news_collector.py               -- RSS 収集・前処理
      - calendar_management.py          -- マーケットカレンダー管理
      - quality.py                      -- データ品質チェック
      - stats.py                        -- zscore_normalize など
      - audit.py                        -- 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py              -- calc_momentum / calc_value / calc_volatility
      - feature_exploration.py          -- calc_forward_returns / calc_ic / factor_summary / rank
    - ai、data、research 内にさらにユーティリティやモジュールが存在します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime 実行時に必要)
- KABU_API_PASSWORD (kabu API 用)
- KABU_API_BASE_URL (オプション, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると自動 .env ロードを無効化)

settings（kabusys.config.Settings）から安全に取得できます。必須変数が未設定だと ValueError を投げます。

---

## テスト・開発時のヒント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を検出）から行います。テストでロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI や J-Quants の呼び出しは外部依存がありテストに向かないため、内部の _call_openai_api や jquants_client._request / get_id_token などを unittest.mock で差し替えてください。
- news_collector はネットワーク通信や XML パースを行うため、fetch_rss や _urlopen をモックしてテストできます。
- DuckDB はインメモリ（":memory:"）での初期化が可能（init_audit_db 等）なのでテスト用 DB を簡単に用意できます。

---

以上が README の概要です。必要であれば、具体的な .env.example のテンプレートや、CI 用のテストコマンド、さらに詳細な API 使用例（関数別の引数説明や戻り値のスキーマ）を追加して作成します。どの情報をより詳しく出力しますか？