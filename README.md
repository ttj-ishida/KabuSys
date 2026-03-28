# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータパイプライン、ニュース NLP、リサーチ（ファクター計算）、監査ログ、及び戦略評価に必要なユーティリティ群を備えたライブラリです。本リポジトリは主に以下を目的とします：

- J-Quants API からのデータ取得（価格・財務・カレンダー）
- DuckDB を使ったデータ保存と ETL パイプライン
- RSS ニュース収集と LLM を用いたニュースセンチメント評価
- 市場レジーム判定（MA + マクロニュースの合成）
- ファクター計算・特徴量探索・統計ユーティリティ
- 発注・約定に関する監査ログスキーマの初期化

以下はこのコードベースの概要、セットアップ、使い方、ディレクトリ構成です。

---

## 主な機能（抜粋）

- Data（kabusys.data）
  - J-Quants クライアント（fetch / save / id_token 管理）
  - ETL パイプライン（日次 ETL：価格・財務・カレンダー）
  - マーケットカレンダー管理（営業日判定、next/prev）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS、安全なフェッチと前処理）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ

- AI（kabusys.ai）
  - news_nlp.score_news: ニュース記事を LLM（gpt-4o-mini）で銘柄ごとにセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321)の200日MA乖離とマクロニュースセンチメントを合成して market_regime を作成

- Research（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
  - 統計ユーティリティ: zscore_normalize（kabusys.data.stats から）

- 設定管理（kabusys.config）
  - 環境変数の読み込み（.env / .env.local 自動ロード、オーバーライドルール）
  - settings オブジェクトで各種設定・パス・トークンを参照可能

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 本リポジトリでは主に以下パッケージが利用されます：
     - duckdb
     - openai（OpenAI Python SDK）
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

4. ローカルパッケージとしてインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと、自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
   - 優先順位: OS 環境変数 > .env.local > .env

   必要となる主要環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用、関数引数でも可）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（使用箇所に依存）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL（DEBUG, INFO, ...）

   例 .env テンプレート（プロジェクトルートに配置）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=Cxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（よく使う API 例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- 共通: 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（LLM を使う）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を指定しなければ環境変数 OPENAI_API_KEY を参照します
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("scored:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用 API（ファクター計算等）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect(str(settings.duckdb_path))
  m = calc_momentum(conn, target_date=date(2026,3,20))
  v = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS フェッチ（ニュース収集の低レベル API）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意点：
- score_news / score_regime は OpenAI API を呼び出します。API キーは関数引数として渡すか環境変数 OPENAI_API_KEY を設定してください。
- jquants_client は J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を settings から参照します。
- DuckDB へ書き込む一部の関数はトランザクションで冪等性を保つ実装になっていますが、実行時の DB バックアップ等は運用側で管理してください。

---

## 設定（settings）で参照できる主な値

- jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
- kabu_api_password (KABU_API_PASSWORD)
- kabu_api_base_url (KABU_API_BASE_URL; デフォルト http://localhost:18080/kabusapi)
- slack_bot_token (SLACK_BOT_TOKEN)
- slack_channel_id (SLACK_CHANNEL_ID)
- duckdb_path (DUCKDB_PATH; Path)
- sqlite_path (SQLITE_PATH; Path)
- env (KABUSYS_ENV: development/paper_trading/live)
- log_level (LOG_LEVEL)
- is_live / is_paper / is_dev ブール系プロパティ

環境変数の自動読み込み挙動：
- プロジェクトルート（.git か pyproject.toml が存在するディレクトリ）を探索して `.env` と `.env.local` を自動ロードします。
- 読み込み順: OS 環境変数 > .env.local（上書き） > .env（既存の OS 環境変数は保護）
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを行いません。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py   — RSS ニュース収集
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns / IC / summaries

---

## 開発・テスト時の注意

- LLM / 外部 API 呼び出しはテスト中にモックすることを推奨します。コード中にテスト用に差し替え可能な内部ラッパー関数（例: _call_openai_api）があります。
- DuckDB を使うため、ローカルの .duckdb ファイルの取り扱いには注意してください。テストでは ":memory:" を使うことができます。
- J-Quants API のレート制限（120 req/min）を守るため、jquants_client にレートリミッタが組み込まれています。運用時は id_token の管理・エラー処理に注意してください。

---

## 最後に

この README はコードベースに含まれるモジュールの主要機能と基本的な使い方をまとめたものです。各モジュールに詳細な docstring が記述されていますので、個別の関数や処理フローについてはソース内のドキュメントを参照してください。必要であれば README にサンプルワークフロー（ETL スケジュール例や戦略評価の流れ）を追加できますので、その場合は用途（運用 / 開発 / バックテスト）を教えてください。