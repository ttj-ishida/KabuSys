# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に格納する ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）を提供します。

---

## 主な目的・概要

- J-Quants API から日次の株価（OHLCV）、財務諸表（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアント実装。
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化。
- 差分取得（バックフィル対応）／保存（冪等性を保つ INSERT ... ON CONFLICT DO UPDATE）を行う ETL パイプライン。
- データ品質チェック（欠損、スパイク、重複、日付不整合）モジュール。
- 監査ログ（signal → order_request → execution のチェーン）を管理する監査テーブル群。
- レート制限・リトライ・トークン自動リフレッシュ等を組み込んだ J-Quants クライアント。

設計上のポイント：
- レート制限（デフォルト 120 req/min）を固定間隔スロットリングで遵守。
- 401 時にリフレッシュトークンから id_token を自動取得して再試行。
- すべてのタイムスタンプは UTC（fetched_at 等）。
- ETL と品質チェックはエラーを拾って継続する（Fail-Fast ではない）。

---

## 機能一覧

- data/jquants_client.py
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar （ページネーション対応）
  - get_id_token（リフレッシュトークンからの id_token 発行）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レートリミッタ、リトライ、401 時の自動リフレッシュ
- data/schema.py
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution）と init_schema / get_connection
- data/pipeline.py
  - 差分更新・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）と個別の ETL ジョブ
- data/quality.py
  - 欠損、スパイク、重複、日付不整合の検出。QualityIssue 型で結果を返す。
- data/audit.py
  - signal_events / order_requests / executions など監査用テーブルの初期化とユーティリティ
- config.py
  - .env（および .env.local / OS 環境変数）から設定を読み込む Settings（自動ロード機能あり）
  - 自動ロード優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- strategy/, execution/, monitoring/ パッケージの骨組み（拡張ポイント）

---

## 前提要件

- Python 3.10+
  - （コード中で型注釈に `X | Y` や `frozenset[str]` などを使用しているため）
- 依存パッケージ（最小）
  - duckdb

インストール例（仮にパッケージ化されている場合）:
```
pip install duckdb
pip install -e .
```
（プロジェクトに requirements.txt があればそれを使ってください）

---

## 環境変数（必須 / 推奨）

以下は config.Settings から参照される主な環境変数名です。`.env` または `.env.local`、もしくは OS 環境変数に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等に使う sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

ヒント:
- `.env.local` は `.env` を上書きする（OS の環境変数は上書き不可）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時に便利）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. Python (>=3.10) を用意し、仮想環境を作る:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存インストール:
   ```
   pip install duckdb
   # もしパッケージ配布があれば:
   pip install -e .
   ```

3. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに設置）。上の例を参照。

4. DuckDB スキーマ初期化:
   - Python REPL やスクリプトで以下を実行します。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```
   - 監査ログ用テーブルを追加する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

---

## 使い方（コード例）

- J-Quants id_token の取得:
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って POST で取得
```

- 日次 ETL の実行（簡単な例）:
```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別ジョブ（株価のみ）:
```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- 品質チェックの実行:
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

設計上、ETL 関数には id_token を注入できるため、テスト時に固定トークンを渡せます。
例:
```python
pipeline.run_daily_etl(conn, target_date=date.today(), id_token="dummy-token")
```

---

## 注意点 / 実装上の挙動

- J-Quants クライアント:
  - レート制限 120 req/min を守るために最小間隔でスロットリングを行います。
  - リトライは最大 3 回（408/429/5xx やネットワークエラーに対して）。429 の場合は Retry-After ヘッダを優先。
  - 401 が返った場合は一度だけトークンをリフレッシュして再試行します（無限再帰防止済み）。
  - 取得時に fetched_at を UTC ISO8601（例: 2023-01-01T00:00:00Z）で記録します。
- DuckDB 保存:
  - save_* 関数は ON CONFLICT DO UPDATE を使い冪等に保存します。
- ETL の差分取得:
  - 最終取得日を見て差分取得し、デフォルトで backfill_days（デフォルト 3）分さかのぼって再取得します（API の後出し修正対策）。
- 時刻関連:
  - 監査ログ（audit）・fetched_at 等の TIMESTAMP は UTC 前提です。init_audit_schema は接続で TimeZone='UTC' を設定します。
- 品質チェック:
  - 各チェックは QualityIssue オブジェクト列を返します。重大度（severity）が "error" のものは呼び出し元で扱いを決定してください。

---

## ディレクトリ構成

以下はソースツリーの主要ファイル一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存）
    - schema.py              — DuckDB スキーマ / 初期化
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ / 発注 → 約定 トレーサビリティ
    - pipeline.py
  - strategy/
    - __init__.py            — 戦略用パッケージ（拡張ポイント）
  - execution/
    - __init__.py            — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視・メトリクス（拡張ポイント）

（上記はプロジェクト内の主要モジュールに対応）

---

## 開発・拡張ポイント

- strategy/ にアルゴリズムを実装し、signal_events / order_requests を生成するフローを作る。
- execution/ にブローカー接続（kabu ステーション等）を実装して order_requests を実際の発注に繋げる。
- monitoring/ で監視（Prometheus / Slack 通知）や稼働ダッシュボードを実装する。
- DuckDB のスキーマやインデックスは設計文書（DataSchema.md）に基づいているため、変更時は互換性に注意する。
- テストのために KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動的な .env ロードを無効化できます。

---

## ライセンス / 責任

本 README はコードベースの説明を行うものです。実運用での使用前に API 利用規約、金融規制、実運用時のリスク管理（資金管理・発注回数制限等）を必ず確認してください。

---

もし README に追記してほしいサンプルスクリプト、CI の設定例、より詳細な .env.example を作成する必要があれば教えてください。