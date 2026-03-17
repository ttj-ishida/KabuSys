# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ取得（J-Quants）、ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログなど、アルゴリズム取引基盤に必要な主要機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から構成されています。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたスキーマ定義と永続化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理（営業日判定・翌営業日/前営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 各所に冪等性・リトライ・レート制御・セキュリティ対策（SSRF、XML 脆弱性、受信サイズ制限 等）

設計上、外部 API 呼び出しはレート制御とリトライ（指数バックオフ）、トークン自動リフレッシュを備え、DuckDB への保存は冪等（ON CONFLICT）を基本としています。

---

## 主な機能一覧

- data.jquants_client
  - 株価日足 / 財務データ / マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）、リトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（save_* 関数）
- data.schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 初期化 helper（init_schema, get_connection）
- data.pipeline
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル機能
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- data.news_collector
  - RSS フィードから記事収集・前処理・ID 生成（正規化 + SHA-256）
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - defusedxml による XML セキュリティ、受信サイズ上限、Gzip 解凍制御
  - DuckDB へ冪等保存（INSERT ... RETURNING を使用）
- data.calendar_management
  - 営業日判定、次/前営業日の取得、期間内営業日リスト取得
  - カレンダーの夜間差分更新ジョブ
- data.quality
  - 各種データ品質チェック（QualityIssue オブジェクトで結果を返す）
- data.audit
  - シグナル／発注／約定の監査スキーマと初期化ユーティリティ

---

## 動作要件（推奨）

- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等）

（プロジェクトに requirements.txt が無い場合は上記を pip インストールしてください）

例:
```bash
python -m pip install "duckdb" "defusedxml"
```

---

## 環境変数 / 設定

KabuSys は環境変数または `.env` / `.env.local` から設定を読み込みます（自動読み込み機能あり。無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

サンプル `.env`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

環境変数は `kabusys.config.settings` から参照できます。

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 環境を作成（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 必要パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```
   （必要に応じてその他ツールや SDK を追加）
4. `.env` を作成し、必須の環境変数を設定
5. DuckDB スキーマを初期化
   ```python
   >>> from kabusys.data.schema import init_schema
   >>> conn = init_schema("data/kabusys.duckdb")
   ```
   - 監査ログ（audit）テーブルを別 DB に初期化したい場合:
   ```python
   >>> from kabusys.data.audit import init_audit_db
   >>> audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（基本例）

以下は主要ユースケースの簡単なコード例です。

- DuckDB 初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL の実行（デフォルトは今日）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ETL を特定の日に対して実行
```python
from datetime import date
result = run_daily_etl(conn, target_date=date(2025, 1, 15))
```

- RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードのセット（抽出用）。None にすると紐付けをスキップ。
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- JPX カレンダー差分更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants から直接データを取得して保存
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 設定値の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成

サンプルの主要ファイル／ディレクトリ構成:
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      quality.py
      audit.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

各サブパッケージの役割:
- kabusys/config.py: 環境変数・設定の集中管理および .env 自動ロード機能
- kabusys/data: データ取得・ETL・スキーマ・品質チェック・監査ログなど
- kabusys/strategy: 戦略実装場所（雛形）
- kabusys/execution: 発注関連（ブローカ連携）実装場所（雛形）
- kabusys/monitoring: モニタリング／メトリクス関連（雛形）

---

## 設計上の注意点・補足

- 自動 .env ロード
  - プロジェクトルートは `.git` または `pyproject.toml` を探索して決定します。
  - 読み込み順: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API
  - レート制限（120 req/min）をモジュール内で守るように実装されています。
  - 401 受信時はリフレッシュトークンから ID トークンを再取得して 1 回だけリトライします。

- ニュース収集
  - RSS の XML パースには defusedxml を使用して XML 脆弱性を防ぎます。
  - 受信バイト数や gzip 展開後の上限を設けてメモリ DoS を防止しています。
  - URL 正規化によりトラッキングパラメータを除去し、SHA-256 の先頭 32 文字で記事 ID を生成します（冪等化）。

- DuckDB スキーマ
  - ON CONFLICT / DO UPDATE を用いて冪等保存を行う設計です。
  - audit モジュールは監査用スキーマを追加で初期化できます（UTC タイムゾーンを強制）。

---

## 開発・貢献

- コード品質や API 変更はドキュメント（DataPlatform.md 等）に準拠してください（リポジトリにあるドキュメントに従う）。
- 自動化されたテストがある場合はそれに従ってください。ユニットテストでは外部通信をモックすることを推奨します（特にネットワーク・ファイル・DB）。

---

必要に応じて README に追記（インストール手順、CI、使用例の拡張、スクリーンショット、ライセンス情報など）できます。追加したい項目があれば教えてください。