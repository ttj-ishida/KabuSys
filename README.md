# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、DuckDB スキーマ、品質チェック、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムに必要なデータ基盤とユーティリティをまとめた Python パッケージです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーの差分取得（レート制限・自動再試行・トークンリフレッシュ対応）
- RSS フィードからのニュース収集と DuckDB への冪等保存（SSRF 防御、サイズ制限、トラッキングパラメータ除去）
- DuckDB スキーマ定義および初期化（Raw / Processed / Feature / Execution / Audit レイヤ）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティを確保）

設計上、冪等性・再現性・セキュリティ（SSRF / XML脆弱性対策）に配慮しています。

---

## 主な機能一覧

- data/jquants_client.py
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定）、指数バックオフによるリトライ、401 発生時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- data/news_collector.py
  - RSS フィード取得 → 前処理 → raw_news へ冪等保存（INSERT ... RETURNING）
  - URL 正規化（utm* 等除去）＋SHA-256 ベースの記事 ID 生成
  - SSRF 対策（スキーム検証、リダイレクト先検査、プライベートアドレス拒否）
  - レスポンスサイズ上限、gzip 解凍後の検査、defusedxml による XML 攻撃防御

- data/schema.py / data/audit.py
  - DuckDB のテーブル群（Raw / Processed / Feature / Execution / Audit）を定義・初期化
  - 監査ログ用テーブル（signal_events, order_requests, executions 等）とインデックスを提供

- data/pipeline.py
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル（デフォルト 3 日）、カレンダー先読み（デフォルト 90 日）
  - ETL 結果を ETLResult として返却

- data/quality.py
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す

- calendar_management.py
  - 営業日判定、前後営業日取得、期間内営業日列挙、夜間カレンダー更新ジョブ

---

## 必要な環境 / 依存関係

主な Python パッケージ（最小限）:

- Python 3.10+
- duckdb
- defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（実運用では HTTP クライアントや Slack 連携等の依存を追加することがあります）

---

## 環境変数（主なもの）

KabuSys は .env ファイル（プロジェクトルートに置く）または環境変数から設定を読み込みます。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

必須（Settings クラスで _require になっているもの）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu API のパスワード
- SLACK_BOT_TOKEN : Slack Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意（デフォルト値あり）:

- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env のフォーマットは一般的な KEY=VALUE 形式に対応し、export プレフィックスやクォートも扱います。

---

## セットアップ手順（ローカルでの基本）

1. リポジトリをクローンし、仮想環境を作る

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

2. .env を作成（ルートに置く）

参考: 必須トークン等を設定

```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
# 任意: DUCKDB_PATH=data/kabusys.duckdb
```

3. DuckDB スキーマ初期化

Python REPL またはスクリプトで:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ用に別 DB を用いる場合:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

(init_schema は親ディレクトリがなければ自動作成します)

---

## 使い方（主な API と例）

- J-Quants トークン取得 / データ取得（モジュールは自動的にトークンキャッシュ・リフレッシュを扱います）

```python
from kabusys.data import jquants_client as jq
# id_token を明示的に取得（通常は settings.jquants_refresh_token を使用）
id_token = jq.get_id_token()
# 日足取得（範囲指定可）
from datetime import date
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- ETL 実行（1日分のフルワークフロー、品質チェック込み）

```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集（既存の DuckDB 接続に保存）

```python
from kabusys.data import news_collector, schema
conn = schema.init_schema("data/kabusys.duckdb")

# デフォルトソースを使って収集
res = news_collector.run_news_collection(conn)
print(res)  # {source_name: 新規保存件数}

# known_codes を渡して銘柄抽出と紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例
res = news_collector.run_news_collection(conn, known_codes=known_codes)
```

- カレンダー更新ジョブ（夜間バッチ想定）

```python
from kabusys.data import calendar_management, schema
conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- 監査用スキーマ初期化（監査ログのみ別 DB で運用する場合）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 設計上の注意点 / 動作ルール

- J-Quants API
  - レート制限は 120 req/min に固定（モジュール内で待機）
  - リトライ: 408, 429, 5xx に対して最大 3 回（指数バックオフ）。429 の場合は Retry-After を優先
  - 401 を受け取った場合、リフレッシュを試みて 1 回リトライ
  - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias を追跡可能に

- News Collector
  - URL 正規化→ID（SHA-256 の先頭32文字）で冪等性
  - defusedxml による XML パース（XML Bomb 対策）
  - リダイレクト先も検査してプライベートアドレスなどへのアクセスを防止
  - レスポンスサイズ上限（デフォルト 10MB）。gzip 解凍後もチェック

- ETL
  - 差分更新を行い、DB 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）
  - backfill_days（デフォルト 3）により最終取得日の数日前から再取得して API の後出し修正を吸収
  - 品質チェックは Fail-Fast にはせず、問題を収集して呼び出し側が判断できるようにする

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py              # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py    # J-Quants API クライアント（取得・保存）
      - news_collector.py    # RSS ニュース収集・保存
      - schema.py            # DuckDB スキーマ定義・初期化
      - pipeline.py          # ETL パイプライン
      - calendar_management.py
      - audit.py             # 監査ログスキーマ
      - quality.py           # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 開発 / テストについて

- 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 単体テスト用に id_token 注入や HTTP のモックが可能な設計（_urlopen 等を差し替えられる）になっています。

---

## 参考 / FAQ

- Q: DuckDB の初期化は必須ですか？
  - A: ETL やデータ保存・品質チェックを行う際は schema.init_schema() によるテーブル初期化を推奨します。既存 DB へ接続する場合は schema.get_connection() を使って接続してください。

- Q: J-Quants のトークンはどのように扱われますか？
  - A: 設定（JQUANTS_REFRESH_TOKEN）を使って get_id_token により id_token を取得し、モジュールレベルでキャッシュします。401 時は自動でリフレッシュを試みます。

---

必要であれば、README に含めるサンプル .env.example、追加の CLI 実行例、運用フロー（夜間 ETL ・監視アラートの設定）なども追記します。どの部分を詳しく記載しましょうか？