# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
J-Quants や kabuステーション、RSS ニュースなど外部ソースからデータを取得し、DuckDB に格納して ETL、品質チェック、監査ログ、カレンダー管理、ニュース収集などを行うためのモジュール群を提供します。

主な対象用途
- 株価・財務・市場カレンダーの自動取得と差分更新（J-Quants）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いた三層（Raw / Processed / Feature）データ管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定トレース）スキーマ
- 発注実行・戦略・監視モジュールの基盤（strategy, execution, monitoring パッケージ）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須設定の取得とバリデーション（settings オブジェクト）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期）、JPX カレンダーをページネーション対応で取得
  - レートリミット制御（120 req/min）、再試行（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応）、XML セキュリティ対策（defusedxml）
  - URL 正規化・トラッキング除去、記事ID = SHA-256 のハッシュ
  - SSRF 対策（スキーム検証 / プライベートIPブロック / リダイレクト検査）
  - DuckDB へのバルク挿入（INSERT ... RETURNING）と銘柄抽出・紐付け
- データスキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化ユーティリティ
  - インデックス作成、初期化関数 `init_schema` / `get_connection`
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日の判定、バックフィル）
  - 日次 ETL エントリ `run_daily_etl`（カレンダー→株価→財務→品質チェック）
  - 個別 ETL ジョブ（prices, financials, calendar）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後の営業日取得 / 期間内営業日取得
  - 夜間バッチ更新 job（calendar_update_job）
- 品質チェック（kabusys.data.quality）
  - 欠損データ / スパイク（前日比閾値） / 重複 / 日付不整合の検出
  - `QualityIssue` を返却し、重大度に応じて呼び出し側で対応
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル、索引、UTC タイムゾーン設定
  - 発注の冪等性とトレーサビリティを担保

（strategy, execution, monitoring パッケージは本コードベースではエントリポイントのみ用意されています）

---

## 必要条件

- Python 3.10 以上（型アノテーションの `|` 演算子や forward-ref の使用のため）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

推奨: 仮想環境（venv / pyenv / poetry 等）を使用してください。

---

## インストール

例: pip を使う場合

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. 開発インストール（プロジェクトがパッケージ化されていれば）
   - pip install -e .

※ プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

---

## 環境変数（.env）

以下の環境変数が利用されます（README は主要項目のみ記載）。必須項目は Settings クラス内で _require によって要求されます。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` を設定すると .env 自動ロードを無効化

自動ロードの挙動:
- パッケージ起点（このファイルの親階層）からプロジェクトルートを .git または pyproject.toml で検出し、
  OS 環境変数 > .env.local > .env の順で読み込みます。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（初回）

1. 必要パッケージをインストール（上記参照）。
2. 環境変数を設定（.env を作成）。
3. DuckDB スキーマ初期化の実行例:

Python スクリプト例:
```python
from kabusys.data import schema

# ファイルパスに DB を作成（親ディレクトリは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログテーブルを同じ DB に追加する場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
conn.close()
```

メモ:
- テスト用途でインメモリ DB を使う場合は `db_path=":memory:"` を指定できます。
- audit 用に専用 DB を作る場合は `init_audit_db()` を使えます。

---

## 使い方（主要 API と簡単な例）

- 設定にアクセスする:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

- 日次 ETL を実行する:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブを実行する:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に保持している銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
conn.close()
```

- 単独で RSS フィードを取得する（例外は呼び出し元で処理）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

- カレンダー更新ジョブ:
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
conn.close()
```

- 品質チェックを個別実行:
```python
from kabusys.data.schema import init_schema
from kabusys.data.quality import run_all_checks

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
conn.close()
```

注意点:
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークンリフレッシュを行いますが、長時間のループで大量リクエストする場合はアプリ側でも配慮してください。
- news_collector は defusedxml, SSRF 検査、レスポンスサイズ制限等を実装しており、安全性を考慮しています。

---

## ディレクトリ構成

以下は主要ファイルの一覧（src 配下）です:

- src/kabusys/
  - __init__.py
  - config.py                     - 環境設定と自動 .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得・保存）
    - news_collector.py            - RSS 収集・保存・銘柄抽出
    - schema.py                    - DuckDB スキーマ定義 & 初期化
    - pipeline.py                  - 日次 ETL パイプライン
    - calendar_management.py       - JPX カレンダー管理 / バッチ更新
    - audit.py                     - 監査ログスキーマ（シグナル・発注・約定）
    - quality.py                   - データ品質チェック
  - strategy/
    - __init__.py                  - 戦略関連パッケージプレースホルダ
  - execution/
    - __init__.py                  - 発注実行関連プレースホルダ
  - monitoring/
    - __init__.py                  - 監視関連プレースホルダ

（その他、プロジェクトルートに pyproject.toml / .git / .env などが想定されます）

---

## 設計上の重要な注意点

- レート制御とリトライ:
  - J-Quants クライアントは 120 req/min の制限を守る設計です。大量取得時は注意してください。
- 冪等性:
  - DB への保存は可能な限り ON CONFLICT 句を用いて冪等にしています（raw テーブル等）。
- 時刻管理:
  - 監査ログや fetched_at は UTC 基準を想定しています（audit.init_audit_schema は TimeZone を UTC に設定）。
- セキュリティ:
  - RSS の XML は defusedxml でパースし、SSRF 対策・受信サイズ制限を実装しています。
- テスト:
  - id_token の注入や conn に対する in-memory DB（":memory:"）利用でユニットテストが容易になる設計です。
- エラー処理:
  - ETL は各ステップで独立して例外を捕捉し、可能な限り他ステップを継続します。結果は ETLResult に集約されます。

---

## 開発・貢献

- バグ修正や機能追加は Pull Request を送ってください。プロジェクトルートに CI / フォーマットやテスト方針を追加すると良いです。

---

以上がこのコードベース（KabuSys）の README です。  
使い始めに不明点があれば、どの機能の利用方法を詳しく知りたいか教えてください。