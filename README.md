# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants API からマーケットデータや財務情報を取得して DuckDB に保存し、ETL・品質チェック・ニュース収集・マーケットカレンダー管理・監査ログなどを提供します。

## 概要
KabuSys は以下を目的とした内部ライブラリ／ツール群です。

- J-Quants API からの株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得
- DuckDB ベースのデータスキーマ定義と初期化
- 日次 ETL（差分更新 + バックフィル）とデータ品質チェック
- RSS を用いたニュース収集と記事 ↔ 銘柄紐付け
- マーケットカレンダーの夜間バッチ更新と営業日判定ユーティリティ
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ
- （将来的に）戦略・実行・監視モジュールへの拡張ポイント

設計上の注意点：
- J-Quants API のレート制限（120 req/min）を厳守する仕組みあり
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
- データ保存は冪等（ON CONFLICT を使用）で再実行に強い
- ニュース収集では SSRF や XML Bomb、大きすぎるレスポンス等への対策を実装

---

## 主な機能一覧
- data.jquants_client
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - rate limiter、リトライ、id_token 自動リフレッシュ
  - DuckDB へ保存する save_* 関数（冪等）
- data.schema
  - DuckDB 用スキーマ定義と init_schema()
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェック
  - 差分取得、バックフィル対応
- data.news_collector
  - RSS 取得・前処理・記事保存（save_raw_news）・銘柄抽出と紐付け
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 安全処理
- data.calendar_management
  - 営業日判定、next/prev_trading_day、期間内営業日取得、calendar_update_job
- data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化ユーティリティ
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue レポーティング

---

## セットアップ手順（開発者向け / クイックスタート）

前提
- Python 3.10 以上推奨（Union 型の `X | Y` 構文を使用）
- DuckDB を利用（duckdb パッケージ）
- defusedxml（RSS パースの安全化）

1. リポジトリをクローンして作業環境を作る（任意）
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存ライブラリをインストール
   （requirements.txt がプロジェクトにある場合はそれを使ってください。なければ最低限以下をインストール）
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings）が未設定だと例外を投げます。主な変数:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID: Slack 通知チャンネル（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=./data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリ自動作成
   conn.close()
   ```

5. 監査用 DB 初期化（任意）
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（代表的な操作例）

- 日次 ETL を実行する（ETL の自動トークン利用）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ETL の個別ジョブ（価格のみ）:
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- RSS からニュース収集して保存する:
  ```python
  import duckdb
  from kabusys.data import news_collector as nc

  conn = duckdb.connect("data/kabusys.duckdb")
  articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = nc.save_raw_news(conn, articles)
  print("new articles:", new_ids)
  ```

- カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- J-Quants ID トークン取得（直接呼ぶ場合）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

---

## 環境変数（Settings）一覧と説明
（必須のものは明示）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルの保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

環境変数はプロジェクトルートの `.env` / `.env.local` から自動読込されます（OS 環境変数が優先）。自動ロードは _find_project_root() で .git または pyproject.toml を検出した場合にのみ行われます。

---

## ディレクトリ構成（主要ファイル）
プロジェクトのソースは `src/kabusys` 以下に配置されています。主要ファイルと簡単な説明:

- src/kabusys/__init__.py
  - パッケージのバージョンと公開モジュール一覧

- src/kabusys/config.py
  - 環境変数のロード・Settings クラス（必須変数の取得、環境判定、ログレベル等）

- src/kabusys/data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py : RSS 収集、前処理、DuckDB への保存、銘柄抽出
  - schema.py : DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py : ETL（差分更新、run_daily_etl 等）
  - calendar_management.py : カレンダー更新・営業日判定ユーティリティ
  - audit.py : 監査ログスキーマと初期化ユーティリティ
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）

- src/kabusys/strategy/ (空の __init__.py — 戦略ロジックの拡張ポイント)
- src/kabusys/execution/ (空の __init__.py — 発注実行ロジックの拡張ポイント)
- src/kabusys/monitoring/ (空の __init__.py — 監視/メトリクスの拡張ポイント)

---

## 開発上の注意点 / 実運用での留意点
- J-Quants API のレート制限やリトライポリシーは実装済みですが、運用環境では API 仕様変更や制限に注意してください。
- DuckDB のファイルパス（単一のファイルへ同時接続が発生する場合）やバックアップ戦略を検討してください。
- ニュース収集では信頼できる RSS ソースのみ登録し、外部アクセス時のネットワークポリシー（プロキシ／防火壁）に注意してください。
- 監査ログは削除しない前提です。ストレージ容量や保管ポリシーを設計してください。
- KABUSYS_ENV に応じた挙動（paper_trading / live）をアプリ側で実装することを想定しています。

---

## 追加情報 / 貢献
- 既存のモジュール（strategy、execution、monitoring）は拡張ポイントです。戦略や注文実行、監視用機能を追加していってください。
- テストを書く際は、config の自動 .env ロードを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと便利です。

不明点や README の補足が必要であれば、どの点を詳しくしたいか教えてください。