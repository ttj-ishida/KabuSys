# KabuSys

日本株自動売買システム（ライブラリ）

このリポジトリは日本株向けのデータ取得・ETL・品質チェック・監査ログ基盤を提供するライブラリ群です。J-Quants / kabuステーション 等の外部サービスと連携し、DuckDB にデータを蓄積して戦略層／実行層へデータを供給します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主に実現します。

- J-Quants API からの市場データ（株価日足、財務情報、JPX カレンダー）取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）
- セキュリティ・堅牢性配慮（API レート制御、リトライ、SSRF 対策、XML パース安全化、メモリ上限）

設計上の特徴：
- idempotent（冪等）な保存処理（DuckDB 側で ON CONFLICT を利用）
- J-Quants API のレート制限（120 req/min）と再試行・トークン自動リフレッシュ対応
- ニュース収集での SSRF / Gzip-bomb / XML-bomb 対策
- ETL は個別ステップごとにエラーハンドリングし、運用時のロバスト性を重視

---

## 主な機能一覧

- データ取得
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（jquants_client）
- 保存（DuckDB）
  - save_daily_quotes, save_financial_statements, save_market_calendar（冪等）
- ニュース収集
  - RSS フィード取得、テキスト前処理、raw_news 保存、銘柄抽出・紐付け
- ETL
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（差分更新・バックフィル・品質チェック）
- 品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- スキーマ初期化
  - init_schema（全テーブル・インデックス作成）
- 監査ログ（Audit）
  - init_audit_schema, init_audit_db（監査用テーブル群の初期化）

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈に `X | Y` を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発パッケージや追加依存があれば別途インストールしてください
```

---

## 環境変数（設定項目）

このパッケージは環境変数（またはプロジェクトルートの `.env`, `.env.local`）を読み込みます。自動読み込みはデフォルトで有効です。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

主な環境変数（必須マークは必須）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack（通知等に使用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (省略時: data/kabusys.duckdb)
  - SQLITE_PATH (省略時: data/monitoring.db)
- システム
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

簡易の `.env.example`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の読み込み仕様のポイント:
- プロジェクトルートは `pyproject.toml` または `.git` を基準に自動検出
- 優先順位: OS 環境 > .env.local > .env
- export プレフィックスやクォート、コメントなどの一般的な .env 書式に対応

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成して必要な値を設定するか、
   - 環境変数（export）で設定してください。

3. DuckDB スキーマの初期化
   - Python REPL か簡単なスクリプトで初期化できます:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   conn.close()
   ```
   - 監査ログ用 DB を別ファイルで分離する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   audit_conn.close()
   ```

4. （任意）初回 ETL 実行
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # デフォルトで今日の処理を行う
   print(result.to_dict())
   conn.close()
   ```

---

## 使い方（主な API / コマンド例）

以下は主要な利用例です。プロダクション運用ではこれらをジョブ（cron / Airflow / prefect 等）で定期実行します。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # ETLResult を返す
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コードの集合（抽出に使用）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants のアクセストークン取得（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
```

- 品質チェック単独実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 運用上の注意・設計メモ

- API レート制御: jquants_client は固定間隔スロットリング（120 req/min）を実装しています。大量の同時呼び出しに注意してください。
- リトライ: ネットワークエラーや 429/408/5xx はリトライ（指数バックオフ）します。401 はトークン自動リフレッシュを試みます。
- 冪等性: DB への保存は可能な限り ON CONFLICT を利用して重複を回避します（ETL の再実行が安全）。
- ニュース収集: URL 正規化・トラッキングパラメータ除去 → SHA-256 ハッシュの先頭32文字を記事IDとして冪等化します。SSRF や XML 攻撃、Gzip-bomb 等に対処しています。
- カレンダー: market_calendar が未取得のときは土日ベースのフォールバックを使用します。DB にある値を優先します。
- 監査ログ: 監査テーブルは UTC タイムゾーンに固定し、削除しない前提で構築されています。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの構成（src 配下）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ pipeline.py
   │  ├─ schema.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

主要モジュールの役割:
- config.py: 環境変数の読み込みと Settings クラス
- data/schema.py: DuckDB スキーマ定義・初期化
- data/jquants_client.py: J-Quants API クライアント（取得・保存）
- data/news_collector.py: RSS ニュース収集と保存・銘柄紐付け
- data/pipeline.py: ETL パイプライン（差分更新・品質チェック）
- data/calendar_management.py: マーケットカレンダー管理（営業日判定等）
- data/audit.py: 監査ログテーブルの初期化
- data/quality.py: データ品質チェック

---

## 開発 / テスト上のヒント

- 自動 .env 読み込みを無効にする:
  - テストで環境を明示的に制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- in-memory DB を使ったテスト:
  - DuckDB のパスに `":memory:"` を渡すとインメモリ DB を使用できます（init_schema(":memory:")）。
- モックと差し替え:
  - news_collector の HTTP 呼び出しは内部で `_urlopen` を使用しているため、テスト時はこの関数をモックして差し替え可能です。
- ログレベル:
  - 環境変数 `LOG_LEVEL` でライブラリのログレベルを制御できます（DEBUG/INFO/...）。

---

## ライセンス / コントリビューション

（本リポジトリのライセンス・コントリビューション規約をここに記載してください）

---

何か README の追記や、具体的な実行スクリプト（CLI）や unit test のテンプレートを追加したい場合は教えてください。必要に応じてサンプルの運用スクリプトや CI ワークフロー例も作成できます。