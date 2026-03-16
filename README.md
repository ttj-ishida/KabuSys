# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）

このリポジトリは日本株の自動売買システム向けに設計された内部ライブラリ群です。データ取得（J-Quants）、DuckDB ベースのスキーマ定義・初期化、ETL パイプライン、監査ログ、データ品質チェック等を提供します。戦略層・発注層・監視層のための基盤コンポーネント群が含まれます。

バージョン: 0.1.0

---

## 概要

主な目的は以下のとおりです。

- J-Quants API から株価（日足・OHLCV）、財務データ、JPX マーケットカレンダーを取得するクライアントを提供する。
- DuckDB に対するスキーマ定義（Raw / Processed / Feature / Execution / Audit）を提供し、冪等に初期化できる。
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）を実行する。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用のテーブル定義・初期化を提供する。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実施する。

設計上のポイント:

- API レート制限（J-Quants: 120 req/min）を固定間隔スロットリングで遵守。
- リトライ（指数バックオフ）と 401 自動トークンリフレッシュ対応。
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等性を担保。
- すべてのタイムスタンプは UTC を基本に扱う設計（監査ログでは明示的に UTC を設定）。

---

## 機能一覧

- 環境変数管理（.env 自動ロード / プロジェクトルート判定）
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン取得（get_id_token）
  - レートリミット・リトライ・自動リフレッシュ
- DuckDB 用スキーマ定義と初期化（data.schema）
  - raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions 等
- ETL パイプライン（data.pipeline）
  - 差分取得（最終取得日ベース）＋バックフィル
  - 市場カレンダーの先読み
  - 品質チェック実行（quality モジュール）
  - 実行結果を ETLResult として返却
- 監査ログ（data.audit）
  - signal_events, order_requests, executions の DDL と初期化
  - UUID ベースのトレーサビリティを想定
- データ品質チェック（data.quality）
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック

戦略（strategy/）、発注（execution/）、監視（monitoring/）用のパッケージは骨組みを提供（実装は各自拡張）。

---

## セットアップ手順

前提
- Python 3.9+（typing の Union | などを使用）
- ネットワーク接続（J-Quants API へアクセスする場合）
- DuckDB を使用（ローカルファイルまたは :memory:）

推奨手順（ローカル開発）

1. リポジトリをクローンし、仮想環境を作成する:

   ```
   git clone <this-repo>
   cd <this-repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールする（最低限は duckdb）:

   ```
   pip install duckdb
   ```

   プロジェクトに pyproject.toml / requirements.txt があればそれを用いてインストールしてください:
   ```
   pip install -r requirements.txt
   # または開発時にパッケージとして使いたい場合
   pip install -e .
   ```

3. 環境変数を設定する（.env ファイルを作成するのが推奨）:

   プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` として次の変数を設定してください（例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   # 任意: KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   自動ロードについて:
   - デフォルトでプロジェクトルートの `.env`（続いて `.env.local`）を自動的に読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は典型的な初期化と日次 ETL の実行例です。

1. DuckDB スキーマの初期化

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
   ```

2. 監査ログテーブルの初期化（必要な場合）

   ```python
   from kabusys.data.audit import init_audit_schema
   # conn は init_schema の戻り値（既存接続）を再利用できます
   init_audit_schema(conn)
   ```

3. 日次 ETL の実行

   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   run_daily_etl は次を順に行います:
   - market_calendar の先読み取得（デフォルト 90 日先まで）
   - 株価（raw_prices）の差分取得（最終取得日からのバックフィル；デフォルト 3 日）
   - 財務データ（raw_financials）の差分取得（同上）
   - 品質チェック（デフォルトで有効）

4. J-Quants API クライアントを直接使う（必要に応じて）

   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を使って自動で取得
   records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
   saved = save_daily_quotes(conn, records)
   ```

注意点:
- jquants_client 内部でレートリミッタとリトライが働きます（120 req/min、最大 3 回リトライ、401 → 自動リフレッシュ）。
- save_* 関数は ON CONFLICT DO UPDATE を使用し冪等にデータを保存します。

---

## 環境変数一覧（主なもの）

必須 (Settings.require でチェックされるもの)
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意、値は 1）

.env 自動ロード挙動:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` を読み込み、 `.env.local` を上書き読み込みします。
- OS 環境変数は保護され、明示的な上書きはされません（`.env.local` は上書きフラグあり）。

---

## 主要モジュール説明

- kabusys.config
  - プロジェクトルート検出、.env パーサ、Settings クラス（環境変数の取得と検証）
- kabusys.data.jquants_client
  - J-Quants API へ安全にアクセスするクライアント（レート制御、リトライ、トークン管理、データ取得・保存）
- kabusys.data.schema
  - DuckDB の DDL（Raw / Processed / Feature / Execution）と init_schema / get_connection
- kabusys.data.pipeline
  - ETL の差分取得ロジック（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェック連携
- kabusys.data.audit
  - 監査ログ用 DDL と初期化（signal_events, order_requests, executions）
- kabusys.data.quality
  - データ品質チェックの実装（欠損 / スパイク / 重複 / 日付不整合）
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 戦略・発注・監視レイヤーのためのパッケージ（拡張用）

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                # 発注関連パッケージ（拡張用）
      - __init__.py
    - strategy/                 # 戦略実装用（拡張用）
      - __init__.py
    - monitoring/               # 監視用（拡張用）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得/保存/認証）
      - schema.py               # DuckDB スキーマ定義と初期化
      - pipeline.py             # ETL パイプライン（差分更新・品質チェック）
      - audit.py                # 監査ログ（トレーサビリティ）定義・初期化
      - quality.py              # データ品質チェック

実行に使用する DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます（`DUCKDB_PATH` で変更可能）。

---

## 運用上の注意 / 補足

- トークン管理: J-Quants の id_token は自動的に refresh_token から取得・キャッシュされ、401 発生時は一度だけ再取得してリトライします。
- レート制御: J-Quants API の制限（120 req/min）を守るため、固定間隔のスロットリングを行います。大量取得をするとレート制限により遅延します。
- ETL の差分取得は安全性を重視し、バックフィル（日数は設定可能）によって API の後出し修正を吸収します。
- DuckDB の ON CONFLICT を利用しているため、一般的な再実行は安全ですが、スキーマ変更や手動でのデータ改変がある場合は注意してください。
- 監査ログは削除しない前提の設計です（ON DELETE RESTRICT 等）。監査データは原則保存し続けてください。

---

## 貢献 / 拡張

- strategy、execution、monitoring パッケージは拡張用に空のパッケージとして用意されています。各自の戦略やブローカー接続、監視ジョブを実装してください。
- 品質チェックはクエリベースで実装されており、新たなチェックを追加する場合は `kabusys.data.quality` に関数を追加し `run_all_checks` に組み込んでください。
- 将来的に他のデータソース（ニュース・代替データ）を追加する場合は raw 層と save_* 関数を追加することを推奨します。

---

何か追加の情報やサンプル（例えば CI 用のワークフロー、具体的な戦略テンプレート、ローカルでのモック API 起動方法など）が必要であれば教えてください。README に追記して整備します。