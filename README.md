# KabuSys

日本株向け自動売買プラットフォームのライブラリ／コアモジュール群です。データ取得、スキーマ管理、監査ログ、データ品質チェックなど、実運用を念頭に置いた構成になっています。

---

## プロジェクト概要

KabuSys は次の目的を持つ Python モジュール群です。

- J-Quants API から市場データ（OHLCV／財務／取引カレンダー）を安全に取得する
- 取得データを DuckDB に冪等的に格納する（Raw / Processed / Feature / Execution の多層スキーマ）
- 発注フローの監査ログを DuckDB に記録してトレーサビリティを確保する
- データ品質チェック（欠損・スパイク・重複・日付整合性）を行い ETL の健全性を担保する
- 実取引（kabuステーション等）や監視（Slack 通知等）との連携を想定した設定管理を提供する

設計上の特徴：
- API レート制限（J-Quants: 120 req/min）を守る RateLimiter を内蔵
- リトライ（指数バックオフ）、401 受信時の自動トークンリフレッシュ等の堅牢な HTTP ロジック
- すべてのタイムスタンプは UTC を前提に設計（監査ログなど）
- DuckDB を用いたスキーマ定義は冪等（存在時はスキップ）で安全に初期化可能

---

## 主な機能一覧

- 環境・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）
  - 必須設定を参照する Settings（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）/ 四半期財務 / JPX マーケットカレンダーの取得
  - レートリミット制御・リトライ・自動トークン更新・ページネーション対応
  - DuckDB への冪等的保存関数（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - インデックス定義
  - init_schema(db_path) による初期化と接続取得
  - get_connection(db_path) による既存 DB への接続

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義
  - init_audit_schema(conn) / init_audit_db(db_path)

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比による急変検知）
  - 主キー重複検出
  - 日付整合性（未来日付・非営業日データ）
  - run_all_checks(conn, ...) で一括実行・issue 集約

---

## セットアップ手順

前提：
- Python 3.9+ を想定 (typing の | 型注釈利用のため)
- duckdb を使用

例: 仮想環境を作成して依存を入れる手順

```bash
# 仮想環境作成（Windows / macOS / Linux のいずれでも）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 開発インストール（プロジェクト直下に pyproject.toml / setup.py がある想定）
pip install --upgrade pip
pip install duckdb
pip install -e .
```

環境変数の準備：
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env または .env.local を置くと自動読み込みされます。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- KABUSYS_ENV (development | paper_trading | live) 既定: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) 既定: INFO
- DUCKDB_PATH 既定: data/kabusys.duckdb
- SQLITE_PATH 既定: data/monitoring.db

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な操作例）

以下はライブラリを使った基本的な操作例です。

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルを自動作成してテーブルを作成
```

インメモリ DB を使う場合:

```python
conn = init_schema(":memory:")
```

2) J-Quants から日足を取得して保存する

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 例: 2023-01-01 から 2023-12-31 まで、特定銘柄を取得
from datetime import date
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB に保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務データやマーケットカレンダーも同様に fetch_* と save_* を利用できます。

4) 監査ログテーブルの初期化（既存接続に追加）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema で取得した接続
```

あるいは監査専用 DB を別ファイルで初期化:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

5) データ品質チェックの実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # 全件チェック
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

6) 環境設定の参照例

```python
from kabusys.config import settings
print(settings.env)          # development | paper_trading | live
print(settings.is_live)      # bool
print(settings.duckdb_path)  # Path オブジェクト
```

---

## 実装上の注意点（運用ガイド）

- 自動 .env ロードはプロジェクトルート検出に依存します（.git または pyproject.toml を基準）。CI 等で意図せず読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API はレート制限が厳しいため、複数プロセスで同時に呼ぶと制限超過する可能性があります。単一のプロセスからの取得やプロセス間で適切に制御してください。
- DuckDB のファイルはローカルファイルシステム上で排他制御が必要です。マルチプロセスでの同時書き込みは注意してください（運用上は単一ライターにする／適切なロックを追加する等）。
- 監査ログは原則削除しない設計です。FK は ON DELETE RESTRICT を採用しており、トレーサビリティを保つために更新運用を厳密に管理してください。
- すべての TIMESTAMP は UTC で扱うことを前提に設計されています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py               # J-Quants API クライアント（取得・保存）
      - schema.py                       # DuckDB スキーマ定義・初期化
      - audit.py                        # 監査ログ（signal/order/execution）
      - quality.py                      # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主な公開 API（抜粋）:
- kabusys.config.settings
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.audit.init_audit_schema / init_audit_db
- kabusys.data.quality.run_all_checks

---

## 開発／コントリビューション

- コーディング規約、テスト、CI 等はプロジェクト固有のルールに従ってください。
- .env.example を用意し、必須変数の説明を明記すると利用者に親切です。
- 大きなデータ取得はテスト時に外部 API を叩かないようモックや KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。

---

## ライセンス / 免責

この README はコードベースのドキュメント補助です。実際の運用では証券会社 API の利用規約・法令順守・リスク管理（資金管理・注文制御）を厳密に行ってください。本プロジェクトは投資助言を目的とするものではありません。

---

必要であれば、README に含める .env.example のテンプレートや、より詳細な API 使用例、運用チェックリスト（起動順序、バックアップ、監査ログの監視）を追加で作成します。どの情報を追加しますか？