# KabuSys

日本株自動売買プラットフォーム用の基盤ライブラリ（プロトタイプ）です。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ、監査ログ、データ品質チェック等の共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムの共通基盤コンポーネント群です。主に以下を提供します。

- J-Quants API からの市場データ取得（OHLCV、財務データ、マーケットカレンダー）
- DuckDB を利用した永続化スキーマ（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント:
- API レート制御・リトライ・トークン自動リフレッシュ
- DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- 品質チェックは全件収集し、呼び出し元で重大度に応じて対処可能

---

## 機能一覧

- config: 環境変数の読み込み・設定管理（.env 自動ロード機能含む）
- data.jquants_client: J-Quants からのデータ取得／保存（fetch_* / save_*）
- data.schema: DuckDB のスキーマ定義・初期化（init_schema, get_connection）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl 等）
- data.quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- data.audit: 監査ログ（signal_events, order_requests, executions）の初期化と管理
- execution / strategy / monitoring: 将来の実装ポイント（パッケージのエントリあり）

---

## 前提・依存

- Python 3.10 以上（型注釈に | を使用）
- duckdb（DuckDB Python バインディング）

必要に応じてプロジェクトに追加する依存:
- （将来的に）Slack SDK や kabu API クライアントなど

例: duckdb のインストール
```
pip install duckdb
```

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを取得

2. 仮想環境を作成（推奨）
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール
```
pip install duckdb
# 他に必要なパッケージがあれば追加
```

4. 環境変数の準備
- プロジェクトルートに `.env`（およびローカル上書き用の `.env.local`）を置くと自動で読み込まれます。
- 自動ロードを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

推奨する最低限の .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
# KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO           # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

- 必須の環境変数は Settings クラスで `_require` によってチェックされます（未設定時は ValueError）。

---

## 使い方（簡単な例）

以下は ETL の初期化と日次実行の例です。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2. 監査ログスキーマの追加（任意）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3. 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日が対象
print(result.to_dict())
# ETLResult によって取得数・保存数・品質チェック結果・エラー情報が得られます
```

4. 個別ジョブの実行（例: 株価差分ETL）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())
```

5. データ品質チェックを単独で実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6. トークンを明示して J-Quants API を直接叩く（テスト等）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

---

## 設定（Settings / 環境変数）

主な環境変数（Settings クラスを参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

注意:
- .env および .env.local はプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みされます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化

---

## ディレクトリ構成

主要ファイルと概要:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（自動 .env ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch_* / save_*）
    - schema.py              — DuckDB スキーマ定義と初期化（init_schema）
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - audit.py               — 監査ログ（signal_events / order_requests / executions）
    - quality.py             — データ品質チェック（各チェック関数と run_all_checks）
    - pipeline.py            — ETL 実行ロジック（差分、バックフィル、品質チェック統合）
  - execution/                — 発注・約定処理用パッケージ（未実装のエントリ）
  - strategy/                 — 戦略層（未実装のエントリ）
  - monitoring/               — 監視モジュール（未実装のエントリ）

（ファイルツリーの抜粋。詳細はソースを参照してください）

---

## 開発者向けメモ

- 型注釈は Python 3.10 の構文（A | B）を使用しています。古い Python では動作しません。
- DuckDB の接続は軽量ですが、スレッド・プロセス間の共有方法に注意してください（現状は単一プロセス前提）。
- jquants_client は内部で固定レート（120 req/min）を守る RateLimiter を利用しています。
- fetch_* 系はページネーションを自動処理し、save_* 系は ON CONFLICT DO UPDATE によって冪等に保存します。
- 品質チェックは重大度（error/warning）を持つ QualityIssue を返します。ETL はチェックで error を検出しても即時終了する設計ではありません（呼び出し元で判断）。

---

## よくある操作例（まとめ）

- スキーマ初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次ETL:
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)

- 監査ログ初期化:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- 品質チェック:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)

---

必要があれば README にサンプル .env.example、追加の使用例（スケジュール設定、監視用 SQL クエリ、CI 用のテスト手順等）を追記します。どの情報を優先して追加しますか？