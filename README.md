# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants API）、ETLパイプライン、データ品質チェック、DuckDBスキーマ定義、監査ログ（発注→約定トレース）など、マーケットデータの取り込みから監査までをカバーします。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダー等を安全に取得
  - レート制限（120 req/min）・リトライ（指数バックオフ）・トークン自動リフレッシュ対応
  - ページネーション対応、取得時刻（fetched_at）のUTC記録で Look-ahead bias を防止
- DuckDB を用いた3層データモデル（Raw / Processed / Feature）と実行（Execution）レイヤーのスキーマ定義・初期化
- ETLパイプライン（差分更新、バックフィル、品質チェック）
- 品質チェック（欠損、スパイク、重複、日付不整合）
- 監査（signal → order_request → executions）のための専用テーブル群

設計は冪等性（INSERT ... ON CONFLICT DO UPDATE）とトレーサビリティを重視しています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants の ID トークン取得（get_id_token）
  - 株価日足、財務データ、マーケットカレンダーの取得（fetch_* 関数）
  - DuckDB への保存（save_* 関数。冪等）
  - レートリミット / リトライ / トークン自動更新対応

- data/schema.py
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path)

- data/pipeline.py
  - 差分ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次一括実行（run_daily_etl）と ETL 結果クラス（ETLResult）
  - backfill、calendar lookahead、品質チェックの統合

- data/quality.py
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付不整合（future_date / non_trading_day）検出
  - run_all_checks(conn, ...) による一括実行と QualityIssue レポート

- data/audit.py
  - signal_events / order_requests / executions の監査テーブル初期化
  - init_audit_schema(conn) / init_audit_db(db_path)

- config.py
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数の優先）
  - 必須設定の取得（Settings クラス）
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD

（strategy、execution、monitoring パッケージは骨組みの __init__ のみ）

---

## 必要な環境変数

必須（未設定時は ValueError）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（将来の発注等で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

オプション（デフォルト値あり）:

- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: "http://localhost:18080/kabusapi"）
- DUCKDB_PATH        : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH        : SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV        : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL          : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に `1` を設定

.env の自動ロード順序:
1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動ロードを阻止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python 環境の準備（推奨: 3.10+）

2. リポジトリをクローンし、仮想環境作成・有効化:
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 必要パッケージのインストール（最低限 duckdb）:
   pip install duckdb

   （プロジェクトに pyproject.toml がある場合は pip install -e . や poetry 等を利用）

4. 環境変数を設定:
   プロジェクトルートに .env を作成する例:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   または OS 環境変数として設定してください。

5. DuckDB スキーマの初期化:
   - デフォルトパス（data/kabusys.duckdb）を使用する場合、親ディレクトリが自動生成されます。

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト内での基本操作例です。

- DuckDB スキーマ初期化（最初に一回）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# デフォルトパスを使う場合
conn = init_schema(settings.duckdb_path)
# またはメモリDB
# conn = init_schema(":memory:")
```

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL ジョブを実行（例: 株価のみ）
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 1, 1))
print(fetched, saved)
```

- 品質チェックのみ実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue)
```

- J-Quants から直接データを取得（テスト・開発時）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,1,31))
```

- 監査ログテーブルの初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

注意:
- run_daily_etl 等の関数はエラーを捕捉して継続する設計（各ステップで errors を集約）。戻り値 ETLResult を確認してください。
- id_token の注入が可能なのでテストしやすくなっています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント、保存ロジック
      - schema.py              — DuckDB スキーマ定義・初期化
      - pipeline.py            — ETL パイプライン（差分更新・日次バッチ）
      - quality.py             — データ品質チェック
      - audit.py               — 監査ログ（signals/orders/executions）
      - pipeline.py
    - strategy/
      - __init__.py            — 戦略関連モジュール（骨組み）
    - execution/
      - __init__.py            — 発注/約定関連モジュール（骨組み）
    - monitoring/
      - __init__.py            — モニタリング関連（骨組み）

各モジュールの役割:
- data/* : データ取得・保存・品質管理・ETL の中核
- config.py : 環境設定の集中管理
- audit.py : 発注から約定までの監査ログを確保するテーブル定義

---

## 開発・運用上の注意

- .env の読み込みはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）から行います。パッケージ配布後も __file__ を基準に探索するので CWD に依存しません。
- 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- J-Quants のレート制限（120 req/min）を _RateLimiter により守る実装です。大量取得時は待ち時間が生じます。
- DuckDB のスキーマは冪等に作成されるため、既存データがある場合は上書きしません（テーブル存在チェック）。
- 監査ログは削除しない前提で設計されています（FOREIGN KEY は ON DELETE RESTRICT 等）。

---

## 参考・次のステップ

- strategy / execution / monitoring パッケージを実装して取引ロジックや監視機能を追加してください。
- Slack 通知や kabuステーションとの連携（発注・約定受信）を実装する際には、config の KABU_API_BASE_URL / KABU_API_PASSWORD を利用してください。
- 運用時は KABUSYS_ENV を適切に設定し（paper_trading / live）、ログレベルや通知設定を見直してください。

---

もし README に追記してほしい内容（例: CI / デプロイ手順、追加のコード例、SQL スキーマ図、運用チェックリスト）があれば教えてください。