# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）、J-Quants クライアント等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を主な目的とした Python ライブラリです。

- J-Quants API を用いたマーケットデータ（株価・財務・カレンダー）の差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理、記事と銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 × マクロセンチメントの合成）
- 研究用ファクター・統計ユーティリティ（モメンタム、バリュー、ボラティリティ、IC、Z-score 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注フローの監査ログスキーマ（signal → order_request → execution のトレース可能化）

設計上の特徴：
- ルックアヘッドバイアスを避ける実装（明示的な target_date 指定、現在日時の暗黙参照回避）
- DuckDB を利用したローカルデータレイク設計
- API 呼び出しはリトライ・バックオフ・レートリミット制御を備える
- 冪等性を重視した DB 書き込み（ON CONFLICT / DELETE→INSERT の置換戦略等）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 各種）
  - market_calendar 管理（営業日判定, next/prev/get_trading_days）
  - news_collector（RSS 取得・前処理・保存）
  - quality（データ品質チェック）
  - audit（監査ログスキーマ初期化・監査 DB ユーティリティ）
  - stats（Zスコア正規化等）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄別ニュースセンチメントを ai_scores へ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定（bull/neutral/bear）を market_regime へ書き込み
- research/
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - 環境変数の自動読み込み（.env / .env.local）と Settings API（settings.*）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `|` を使用）
- DuckDB、openai 等のライブラリを利用

1. リポジトリをクローンし、パッケージをインストール（開発インストール推奨）:

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"   # setup.cfg/pyproject に extras を定義している場合
   ```

   （プロジェクトに requirements ファイルがある場合はそれに従ってください。主な依存例: duckdb, openai, defusedxml）

2. 環境変数 / .env を用意

   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を配置すると自動読み込みされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要なら）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出しで渡すか環境変数に設定）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   デフォルト DB パス:
   - DuckDB: data/kabusys.duckdb（settings.duckdb_path）
   - 監視用 SQLite: data/monitoring.db（settings.sqlite_path）

3. データディレクトリの作成（必要に応じて）:

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python インタラクティブやスクリプトからの呼び出し例です。すべて DuckDB 接続を渡して操作します。

- DuckDB 接続を作成して日次 ETL を実行する:

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # ETL を今日実行（target_date を指定しても良い）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} ai_scores")
  ```

- 市場レジーム判定を実行:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化（監査専用 DuckDB を作る）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duckdb.db")
  # conn は初期化済みの DuckDB 接続
  ```

- market_calendar 周りのユーティリティ例:

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- score_news / score_regime は OpenAI API を呼びます。API 呼び出しは失敗時にフェイルセーフ（スコア 0 等）で継続する設計ですが、API キーが未設定だと ValueError を投げます。
- ETL / J-Quants クライアントは rate limit / token refresh / retry を内部で処理します。

---

## 環境変数の自動ロード挙動

- 自動ロード対象ファイル: プロジェクトルートの `.env` と `.env.local`
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
- .env のパースはシェル風の export/コメント/クォート等に対応しています

---

## ディレクトリ構成（主要ファイル）

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
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 ETL・client 補助モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

上記は本リポジトリに含まれる主要モジュールです。各モジュールは DuckDB 接続を受け取り、純粋に SQL / 計算処理を実行する設計になっています。

---

## 開発・テスト時のヒント

- テスト時に環境変数の自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分（_call_openai_api 等）はモックしやすい設計になっており、ユニットテストでは patch で置き換えることが想定されています。
- DuckDB の executemany は空リストを受け付けないバージョン制約に配慮した実装箇所があります（パラメータが空かをチェックしてから呼び出す等）。

---

もし README に追加したいサンプルスクリプト（ETL スケジューラ設定、監査クエリ例、.env.example のテンプレート等）があれば、内容を教えてください。README をその形式に合わせて追記します。