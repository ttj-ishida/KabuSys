# KabuSys — 日本株データプラットフォーム & 自動売買基盤

KabuSys は日本株向けのデータ取得・品質管理・ファクター計算・ニュース NLP（LLM）によるセンチメント評価・マーケットレジーム判定・監査ログ・ETL パイプラインを含む、研究（Research）〜本番（Execution）までを想定したソフトウェアコンポーネント群です。本リポジトリは主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）と保存機能（DuckDB）
- RSS ニュース収集と LLM を用いたニュースセンチメント（銘柄別 ai_scores）
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマと初期化ユーティリティ（発注→約定のトレーサビリティ）
- J-Quants クライアント（レート制御・リトライ・トークンリフレッシュ）

目的は、ルックアヘッドバイアスを避けた安全なデータパイプラインと、LLM を活用した補助的な情報（ニュースセンチメント等）を組み合わせて戦略研究・自動売買の上流を支援することです。

---

## 主な機能一覧

- Data
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch/save 関数、トークン管理、レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）

- AI（LLM）
  - ニュースセンチメント（score_news: 銘柄ごとに -1.0〜1.0 を ai_scores に保存）
  - 市場レジーム判定（score_regime: ma200 とマクロセンチメントを合成して market_regime に保存）

- Research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - z-score 正規化ユーティリティ

- Audit / Execution
  - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
  - 監査用 DuckDB 初期化ユーティリティ（init_audit_db）

---

## 必要条件（Prerequisites）

- Python 3.10+
- DuckDB
- OpenAI Python SDK (openai)
- defusedxml（RSS パースの安全化）
- その他：標準ライブラリのネットワーク、json 等

代表的な Python パッケージ（例）:
- duckdb
- openai
- defusedxml

（プロジェクトに requirements.txt がない場合は上記を pip でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - setuptools が用意されているなら:
     ```
     pip install -e .
     ```
     （パッケージ化されていないケースは個別に）
   - 個別:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   プロジェクトルートに `.env` を置くと自動で読み込まれます（SRC/config.py により .env, .env.local をプロジェクトルートから読み込み）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必要な場合）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等）
   - OPENAI_API_KEY: OpenAI 呼び出しに必要（score_news, score_regime）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（例）

以下は主要 API のサンプル利用方法です。DuckDB はローカルファイルまたは ":memory:"。

- DuckDB 接続（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（J-Quants から株価/財務/カレンダーを取得して保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジーム判定（market_regime に書き込む）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って audit テーブルにアクセスできます
  ```

- RSS フィードを取得して raw_news に格納する（news_collector.fetch_rss を利用）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- LLM 呼び出し（score_news / score_regime）は OpenAI API キーが必要です。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 設計上、各処理は可能な限りルックアヘッドバイアスを避ける実装がされています（target_date を明示的に渡す等）。
- ETL / API 呼び出しはネットワーク/API エラーに対してリトライやフェイルセーフを備えていますが、ログを確認して問題を把握してください。

---

## 主要モジュール（抜粋）

- kabusys.config — 環境変数と .env 自動ロード / Settings
- kabusys.data
  - jquants_client.py — J-Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py — ETL パイプライン（run_daily_etl など）, ETLResult
  - quality.py — データ品質チェック
  - news_collector.py — RSS 収集（SSRF 対策 等）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py — 監査ログ DDL と初期化
  - stats.py — zscore_normalize 等
- kabusys.ai
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- kabusys.research
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — 前方リターン / IC / 統計

---

## ディレクトリ構成（要約）

（src レイアウトに基づく一部抜粋）

- src/
  - kabusys/
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
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - audit (utilities)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/ ... (その他)
    - monitoring/, execution/, strategy/ など（__all__ で公開されることを想定）

（開発時は src/ をパッケージルートとしてインストールしてください）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - config.py はプロジェクトルートを .git または pyproject.toml で探索します。プロジェクトルートが見つからない場合自動ロードをスキップします。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI の呼び出しエラー
  - OPENAI_API_KEY が未設定だと score_news / score_regime は ValueError を投げます。レート制限や 5xx は内部でリトライしますが、継続的な失敗時はログを確認してください。

- DuckDB への書き込みエラー
  - ETL はトランザクションを利用します。DB スキーマがない場合には事前にテーブルを作成するスクリプト（schema 初期化）が必要です（本 README では schema 初期化の具体的DDLは省略しています）。

---

## 参考 / 開発者向けメモ

- すべての「日付処理」はルックアヘッドバイアスを避けるため target_date を明示的に受け取る設計になっています。バックテストやバッチ実行では target_date を明示的に渡してください。
- News / LLM 部分は API レスポンスのフォーマットを厳密に期待しています（JSON モードで厳密な JSON を要求）。レスポンスのパース失敗は安全にフォールバックするよう実装されています。
- jquants_client は rate limiting（120 req/min）と 401 のトークン自動リフレッシュを実装しています。

---

もし README に追加したい具体的な情報（例えば、DB スキーマの DDL、運用スケジュールや systemd / cron のサンプル、CI/CD 設定、テストの実行方法など）があれば教えてください。必要に応じて README を拡張します。