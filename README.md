# KabuSys

KabuSys は日本株向けの自動売買基盤（データ取得・ETL・品質チェック・監査ログ等）を想定した Python ライブラリです。J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に永続化してパイプライン処理・品質チェック・監査ログを行うための基盤機能を提供します。

Version: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価日足 (OHLCV)、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応の固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution の多層スキーマ
  - 各種制約（CHECK/PRIMARY KEY/FOREIGN KEY）とインデックスを定義
  - 冪等なテーブル作成（CREATE IF NOT EXISTS）とインデックス作成

- ETL パイプライン
  - 差分更新（最終取得日ベース）、backfill による後出し修正吸収
  - 市場カレンダー先読み（lookahead）
  - データ保存は ON CONFLICT DO UPDATE による冪等性
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- データ品質チェックモジュール
  - 欠損（OHLC 欄）、主キー重複、スパイク（前日比閾値）、将来日付 / 非営業日の検出
  - QualityIssue オブジェクトによる詳細レポート（severity: error/warning）

- 監査ログ（audit）
  - シグナル → 発注要求 → 約定のトレーサビリティテーブル群
  - 冪等キー（order_request_id / broker_execution_id）設計
  - すべての TIMESTAMP は UTC 保存

- 設定管理
  - .env / .env.local / OS 環境変数から設定値を自動読み込み（プロジェクトルート検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

---

## 必要要件

- Python 3.9+（コードは型注釈で 3.10 の Union | を使っていますが、3.9 でも typing 互換対応があれば動作します。確実には 3.10+ を推奨）
- duckdb
- （実運用）ネットワークアクセス（J-Quants API）

必要なパッケージはプロジェクトに requirements ファイルがあればそちらを使用してください。最低限は:

```
pip install duckdb
```

（本 README は最小限の依存しか示していません。実運用では urllib 等以外にログ・Slack 連携など追加ライブラリが必要になる可能性があります。）

---

## 環境変数（主なもの）

以下はコードで参照される主要な環境変数と既定値（記載があるもの）です。.env/.env.local をプロジェクトルートに置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV : 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込みを無効化
- KABUSYS_API_BASE_URL (not in code) :  -- （注意: kabu_api_base_url の env 名は KABU_API_BASE_URL）
- KABU_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH : DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH : 監視用 SQLite 等のパス。デフォルト "data/monitoring.db"

例: .env の最小テンプレート
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

.env のパーサは `export KEY=val`、シングル/ダブルクォート、コメント行等に対応します。

---

## セットアップ手順（ローカルでの開始例）

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 必要パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb
   # プロジェクトがパッケージ化されている場合:
   # pip install -e .
   ```
4. プロジェクトルートに .env を作成（上のテンプレート参照）
5. DuckDB スキーマ初期化（次節を参照）

---

## データベース初期化

DuckDB スキーマを作成して接続を得るには `kabusys.data.schema.init_schema` を使用します。

Python REPL / スクリプト例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

監査ログテーブルを既存接続へ追加する場合:
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で得た接続
init_audit_schema(conn)
```

監査専用 DB を作る場合:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## ETL 実行方法（例）

日次 ETL のエントリポイント: `kabusys.data.pipeline.run_daily_etl`

簡単な実行例:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# 初回: スキーマ作成
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

引数例:
- target_date: ETL の対象日（date オブジェクト）
- id_token: J-Quants の ID トークンを直接注入可能（省略時は内部キャッシュ/自動取得）
- run_quality_checks: 品質チェックを実行するか（デフォルト True）
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）
- calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

個別 ETL（株価 / 財務 / カレンダー）も `run_prices_etl`, `run_financials_etl`, `run_calendar_etl` として提供されています。

---

## J-Quants クライアントの使い方（簡易）

認証 ID トークン取得:
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を利用
```

日足取得:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
```

取得結果の保存（DuckDB）:
```python
from kabusys.data.jquants_client import save_daily_quotes
saved_count = save_daily_quotes(conn, records)
```

注意: HTTP リトライやレートリミット、401 のトークン自動リフレッシュはクライアント内部で処理されます。

---

## 品質チェック（quality モジュール）

`kabusys.data.quality.run_all_checks(conn, target_date, reference_date, spike_threshold)` は各種チェックを実行し、品質問題のリスト（QualityIssue オブジェクト）を返します。ETL の一部として既定で実行されますが、個別に呼び出すこともできます。

QualityIssue には:
- check_name, table, severity ("error" / "warning"), detail, rows（サンプル）

ETL 実行結果 (`ETLResult`) に品質問題とエラーが集約されます。

---

## 自動 .env 読み込みの動作

- プロジェクトルートの特定: このパッケージは `__file__` を基に親ディレクトリに `.git` または `pyproject.toml` がある場所をプロジェクトルートと見なします。
- 読み込み優先順位: OS 環境 > .env.local (> .env)
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みをスキップします（テスト等で利用）。

---

## 注意事項 / 実運用メモ

- J-Quants の API レート制限（120 req/min）を厳守していますが、外部の処理と合わせて呼び出し頻度に注意してください。
- DuckDB のファイルパスの親ディレクトリがない場合、init 関数が自動で作成します。
- すべての TIMESTAMP は UTC を前提としています（監査ログでは SET TimeZone='UTC' を実行）。
- KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかでなければなりません。

---

## 主要ディレクトリ構成（src 配下）

- src/
  - kabusys/
    - __init__.py
    - config.py               -- 環境変数・設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - jquants_client.py     -- J-Quants API クライアント（取得・保存関数）
      - schema.py             -- DuckDB スキーマ定義・初期化
      - pipeline.py           -- ETL パイプライン（差分更新・品質チェック）
      - audit.py              -- 監査ログ（signal/order/execution）テーブル初期化
      - quality.py            -- データ品質チェック（欠損・重複・スパイク・日付不整合）
    - strategy/
      - __init__.py           -- 戦略関連モジュール（骨組み）
    - execution/
      - __init__.py           -- 発注実行関連（骨組み）
    - monitoring/
      - __init__.py           -- 監視用モジュール（骨組み）

---

## 開発・拡張のヒント

- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、環境変数をテスト側で明示的に設定すると良いです。
- `jquants_client._RateLimiter` は固定間隔スロットリング実装のため、後でトークンバケット等に切り替えることも可能です。
- DuckDB スキーマは DDL がモジュール内に定義されているため、新しいテーブルを追加する場合は schema.py の DDL リストとインデックス配列に追記してください。
- Audit テーブルは削除前提では設計されていないため（ON DELETE RESTRICT）、運用時は注意してください。

---

ご不明点や README に追加したい具体的な使用例（CLI スクリプト、cron / Airflow 連携例、Slack 通知の実装例など）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追加で用意します。