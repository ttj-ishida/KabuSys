# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（データ取得・保存・品質チェック）、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などの機能を備えています。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータパイプライン／リサーチ／運用支援ライブラリ群です。主な目的は以下：

- J-Quants API を用いた市場データ（株価、財務、上場情報、マーケットカレンダー）の差分取得と DuckDB への冪等保存
- ニュースの収集と LLM による銘柄ごとのセンチメント評価
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- ファクター計算（モメンタム・バリュー・ボラティリティなど）と研究ツール
- データ品質チェック（欠損／スパイク／重複／日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- RSS ニュース取得（SSRF 対策・トラッキングパラメータ除去等の前処理）

設計上の注力点は「ルックアヘッドバイアス防止」「冪等性」「堅牢な API リトライとレート制御」「DB 操作の一貫性」です。

---

## 機能一覧

- data/etl
  - run_daily_etl: 日次 ETL（カレンダー、株価、財務、品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL
  - jquants_client: J-Quants API 呼び出し・保存ロジック（レート制限・リトライ・トークンリフレッシュ対応）
  - news_collector: RSS フィード収集（SSRF 対策、XML 安全処理、前処理）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）

- ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）で銘柄別センチメント化し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存

- research
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター算出）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（研究用ユーティリティ）

- config
  - 環境変数読み込み (.env/.env.local の自動ロード、無効化オプション有り) と settings オブジェクト

---

## セットアップ手順

以下は最小限のセットアップ手順の例です。プロジェクト配布形態によって調整してください。

1. Python 環境の準備
   - 推奨: Python 3.9+（コードは型注釈を利用しています）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際の要件はプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成するか、OS 環境変数で設定します。
   - 必須（コード内で `_require` により必須になっているもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知に利用する Bot トークン
     - SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID
   - その他よく使う設定:
     - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用。関数呼び出しでも上書き可能）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト向け）

   - 例 .env（参考）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化（監査用の例）
   - 監査ログ用 DuckDB の初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 他スキーマの初期化は用途に応じて実装済みのスキーマ初期化処理を使ってください（プロジェクト内に schema 初期化関数がある場合はそちらを参照）。

---

## 使い方（簡易例）

以下は主要機能の呼び出し例です。実際はログ設定や例外処理を適宜追加してください。

- 日次 ETL 実行（J-Quants からデータ取得して DuckDB に保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア算出（LLM を使って ai_scores に書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で与えれば環境変数に依らず上書き可能
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- RSS フィードの取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

- 監査 DB の初期化（order/audit 用）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

---

## 設計上の注意点 / 運用上の留意事項

- ルックアヘッドバイアス対策:
  - 多くの関数は date.today() を内部で参照せず、呼び出し側が target_date を明示することを想定しています。バックテストでは必ず過去の date を指定してください。
- 環境変数の自動ロード:
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml）を探し .env / .env.local を自動読み込みします。テスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 冪等性:
  - J-Quants データ保存関数（save_*）は ON CONFLICT DO UPDATE により冪等化されています。
  - ETL の差分取得は最終取得日を基に行います（バックフィル日数を設定可能）。
- API 呼び出し:
  - J-Quants クライアントは固定間隔の RateLimiter とリトライロジックを備えています。OpenAI 呼び出し部分もリトライ・フォールバックを実装していますが、API 利用上限とコストに注意してください。
- ニュース取得:
  - RSS 取得時に SSRF 防御、gzip/サイズ上限、XML 脆弱性対策（defusedxml）を行っています。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なファイル群（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - etl.py (公開インターフェース)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記に加え、strategy / execution / monitoring 等のパッケージを公開するための __all__ がパッケージルートに用意されています。実装・詳細はコードを参照してください。）

---

## 開発・テスト

- 自動ロードされる .env を使用するため、ローカル開発時は .env.example を参考に .env を準備してください（.env.example はプロジェクトに含めるのが一般的です）。
- 外部 API を必要とする機能（J-Quants / OpenAI / RSS）については、単体テストではモック（unittest.mock）を使って依存を置き換えてください。コード内にもテスト用に差し替え可能な内部関数（例: _call_openai_api、_urlopen 等）が用意されています。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env 自動読み込みを無効化できます（テストで環境をコントロールしたい場合に有用）。

---

## ライセンス / 貢献

- この README はコードベースの概要と利用方法を示すためのもので、実運用前に必ずセキュリティ/テスト/監査を行ってください。
- 貢献や問題報告はリポジトリの issue / pull request にて受け付けてください。

---

ご希望があれば、README に以下を追加します：
- requirements.txt / pyproject.toml に合わせた具体的なインストール手順
- 各テーブル定義（DDL）の要約
- 実行ワークフロー（Cron / Airflow などでの日次 ETL 実行例）
- Slack 通知・エラーハンドリングのサンプル

どれを追加しますか？