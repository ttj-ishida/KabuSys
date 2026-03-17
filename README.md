# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL・品質チェック・ニュース収集・監査ログなど、トレーディング基盤の基礎機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの市場データ（株価・財務・市場カレンダー）取得
- DuckDB を使ったデータレイク（スキーマ・初期化・接続管理）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- レート制限・リトライ・トークン自動リフレッシュ等の堅牢な実装

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）を遵守する仕組みあり
- リトライ（指数バックオフ）、401 に対する自動トークン更新
- データ保存は冪等性（ON CONFLICT）を重視
- ニュース収集での SSRF / XML 攻撃対策や受信サイズ制限

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから idToken を取得）
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）
- data.schema
  - DuckDB スキーマの定義と初期化（init_schema, get_connection）
- data.pipeline
  - 日次 ETL をまとめて実行（run_daily_etl）
  - 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分取得・バックフィル・品質チェック統合
- data.news_collector
  - RSS フィード取得（fetch_rss）
  - raw_news への保存と銘柄紐付け（save_raw_news, save_news_symbols, run_news_collection）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、受信サイズ制限
- data.quality
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks による総合実行
- data.audit
  - シグナル / 発注要求 / 約定の監査ログ用スキーマ（init_audit_schema, init_audit_db）
- 環境設定管理（config）
  - .env 自動ロード（プロジェクトルート検出）と Settings オブジェクト

---

## 要件（主要依存）

- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリ: urllib, logging, datetime, pathlib 等）

インストールはプロジェクトの packaging に依存しますが、開発環境では pip を使って依存を入れてください。例:

```bash
pip install duckdb defusedxml
```

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

3. 必須環境変数（少なくとも以下を設定してください）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション用パスワード（実行モジュールで利用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - 省略可: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行モード（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   例 `.env`（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema.init_schema を実行してファイルを作成・初期化します。

例:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログを追加したい場合
from kabusys.data import audit
audit.init_audit_schema(conn)
```

---

## 使い方（例）

以下はライブラリの典型的な使い方例です。

- J-Quants の id_token を取得（必要なら直接呼び出し可能）:

```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使う
```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェックを順に実行）:

```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みが前提
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行（既存の DuckDB 接続を渡す）:

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources を省略するとデフォルトの Yahoo Finance の RSS を使う
out = news_collector.run_news_collection(conn, known_codes={"7203","6758","9984"})
print(out)  # {source_name: 新規保存件数, ...}
```

- スキーマの初期化（最初に一度だけ）:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログを別DBで分けたい場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- ETL の差分取得は DB 上の最終取得日を参照して自動で date_from を決定します。初回は 2017-01-01 から取得します。
- run_daily_etl はエラーを個別に捕捉して可能な範囲で処理を継続します。戻り値の ETLResult でエラー / 品質異常を確認してください。

---

## 環境設定の自動読み込み挙動

- config.py により、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テストなどで自動ロードを止めたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル風の export KEY=VAL やクォートを考慮した実装になっています。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境設定 / Settings
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集 / 保持 / 銘柄抽出
    - pipeline.py            -- ETL パイプライン（差分・品質チェック）
    - schema.py              -- DuckDB スキーマ定義・初期化
    - audit.py               -- 監査ログ（signal/order/execution）用スキーマ
    - quality.py             -- 品質チェック
  - strategy/
    - __init__.py            -- 戦略関連（拡張ポイント）
  - execution/
    - __init__.py            -- 発注/約定処理（拡張ポイント）
  - monitoring/
    - __init__.py            -- モニタリング関連（拡張ポイント）

（上記は配布パッケージの典型的な構造です。プロジェクトルートには .env.example 等のドキュメントがある想定です）

---

## 設計上の注意・挙動

- API レート制御: jquants_client 内で固定間隔スロットリングを実施（120 req/min 相当）。
- リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回のリトライ。
- 401 ハンドリング: id_token の自動リフレッシュを行い1回リトライ。
- データ保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識。
- ニュース収集はトラッキングパラメータ除去・URL 正規化・SSRF/サイズ対策済み。
- 品質チェックは Fail-Fast ではなく全件検査を行い、呼び出し元が判断する設計。

---

## 開発・テスト時のヒント

- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部環境への依存を切ると安定しやすいです。
- jquants_client のネットワーク呼び出しはテストでモックしやすいように設計されています（例: _urlopen / _get_cached_token のモック）。
- news_collector.fetch_rss では _urlopen を差し替えて HTTP 層を制御できます。

---

必要であれば、README にサンプル .env.example、CLI コマンド例（cron / Airflow 用）、あるいは戦略・実行層の利用例を追記します。どの追加情報が欲しいか教えてください。