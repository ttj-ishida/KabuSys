# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、ファクター計算、監査ログ／発注トレース機能などを提供します。

主な想定用途
- 日次バッチでの市場データ ETL（価格・財務・マーケットカレンダー）
- ニュースの収集と LLM を用いた銘柄センチメント算出
- 市場レジーム判定（ETF とマクロニュースの合成）
- 研究（ファクター計算、将来リターン、IC 検証）
- 発注監査ログ用の監査 DB 初期化／運用支援

---

## 機能一覧

- data
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レートリミット・保存）
  - ETL パイプライン（prices / financials / calendar の差分取得、品質チェック）
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF 対策、URL 正規化、重複防止）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル定義と初期化）
  - 統計ユーティリティ（Zスコア正規化）
- ai
  - news_nlp: OpenAI（gpt-4o-mini）で銘柄単位のニュースセンチメントを算出して ai_scores テーブルへ書き込み
  - regime_detector: ETF (1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を算出
- research
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー）

設計上のポイント
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を不適切に参照しない設計
- DuckDB を主なローカルデータストアとして使用（冪等性を意識した保存）
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスを厳密にバリデート
- ネットワーク/API エラーに対してリトライやフェイルセーフ処理を多用

---

## 必要環境 / 依存

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの配布パッケージに requirements.txt / pyproject があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／取得して仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   例:
   ```bash
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # またはパッケージが pyproject/requirements を提供していれば:
   # pip install -e .
   # pip install -r requirements.txt
   ```

3. 環境変数 / .env を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可）。
   - 最低限必要なキー（例）
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # kabuステーション API（必要場面のみ）
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # OpenAI（news_nlp / regime_detector 用）
     OPENAI_API_KEY=sk-...

     # Slack（通知等）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXX

     # データベースパス（任意）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行環境
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - 必須変数が不足していると Settings プロパティが ValueError を投げます。

4. DuckDB ファイルのディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から呼び出す代表的な API の例です。

- ETL（1日分の日次ETL を実行）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（ai_scores へ書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（market_regime へ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（order/audit テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査ログに書き込みなどを行う
  ```

- RSS フィード取得（news_collector.fetch_rss の利用例）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点
- OpenAI 呼び出しは API の利用料金が発生します。API キー・利用制限に注意してください。
- J-Quants API は認証トークンを必要とし、レートリミット（120 req/min）を守る実装になっています。
- ETL／API 呼び出しはネットワークエラーや API エラーに対してリトライ等の設計がされていますが、ログを監視して問題を検出してください。

---

## .env 自動読み込みに関して

- パッケージ起動時にプロジェクトルート（__file__ の親階層で .git または pyproject.toml が見つかる場所）を探索し、`.env` → `.env.local` の順で自動的に読み込みます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## 主要モジュールと API（抜粋）

- kabusys.config.Settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password / kabu_api_base_url
  - settings.slack_bot_token / slack_channel_id
  - settings.duckdb_path / sqlite_path
  - settings.env / settings.log_level / settings.is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, save_daily_quotes
  - fetch_financial_statements, save_financial_statements
  - fetch_market_calendar, save_market_calendar
  - fetch_listed_info

- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)

---

## ディレクトリ構成（抜粋）

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
    - (その他 ETL / helper モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他の研究用モジュール）

上記はソース全体の主要ファイルのみ抜粋しています。各モジュールは DuckDB を前提に SQL と Python を組み合わせて実装されています。

---

## 運用上の注意 / トラブルシューティング

- DuckDB ファイルのパス（settings.duckdb_path）は共有／バックアップ戦略を検討してください。監査 DB は削除しない前提です。
- API キーやトークンが不足すると、Settings のプロパティ取得時に ValueError が発生します。ログで原因を確認してください。
- OpenAI のレスポンスは厳密に JSON を期待していますが、万が一パースに失敗してもフェイルセーフとしてスコアを 0.0 にして処理継続する設計です（news_nlp/regime_detector）。
- J-Quants の 401 は自動リフレッシュを試みますが、リフレッシュに失敗した場合は例外になります。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境読み込みを制御し、OpenAI 呼び出し部分は unittest.mock で差し替えてください（各モジュールに差し替えを前提とした実装あり）。

---

もし README に追加したい「インストール済みパッケージの exact list」「実運用例（systemd / cron の設定例）」「スキーマ定義（テーブル列の完全一覧）」などが必要であれば、必要な情報を教えてください。