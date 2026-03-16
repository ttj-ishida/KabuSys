# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）
バージョン: 0.1.0

このリポジトリは、データ取得・スキーマ管理・データ品質チェック・監査ログなど、
自動売買システムの基盤となる共通コンポーネントを提供します。
J-Quants API や kabuステーション等と連携して市場データを収集し、
DuckDB に格納・管理することを想定しています。

---

## 主な機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルートの検出、.env/.env.local の優先度管理）
  - 必須環境変数チェックと便利なプロパティ（settings オブジェクト）
- J-Quants データ取得クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の厳守、リトライ（指数バックオフ）、
    401 時の自動トークンリフレッシュ、ページネーション対応
  - 取得タイムスタンプ（fetched_at）を UTC で記録（Look-ahead バイアス対策）
  - DuckDB への冪等的な保存関数（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - テーブル作成・インデックス作成・接続ユーティリティ（init_schema / get_connection）
- 監査ログ（data/audit.py）
  - シグナル → 発注 → 約定 のトレーサビリティテーブル群（冪等キー、ステータス管理）
  - UTC タイムゾーン固定、監査向けインデックス
- データ品質チェック（data/quality.py）
  - 欠損、重複、スパイク（急騰/急落）、日付不整合（未来日や非営業日）検出
  - QualityIssue を返す設計（Fail-Fast ではなく全検査結果を収集）
- その他
  - パッケージ化された名前空間 kabusys（strategy、execution、monitoring 等の拡張ポイント）

---

## 要求環境

- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- 主要依存:
  - duckdb
- ネットワーク接続（J-Quants API 等）
- その他、運用中に Slack クライアントや kabuAPI クライアント等の追加依存が必要になる場合があります

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb
   - （プロジェクトを editable インストールする場合）
     - pip install -e .

   > 注: 本リポジトリに requirements.txt が無い場合、上記以外に運用で必要なライブラリ（例: slack_sdk 等）を適宜追加してください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` ファイルを置くと自動でロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 省略可（デフォルトあり）

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（必要に応じて変更）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

必須環境変数（Settings によって参照されるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（上記が未設定の場合、Settings のプロパティアクセス時に ValueError が発生します）

---

## 初期化（DuckDB スキーマの作成）

Python REPL やスクリプト内で簡単に初期化できます。

例: DuckDB データベースを初期化する
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
```

監査ログのみ別 DB に分ける場合:
```python
from kabusys.data import audit, schema
# 既存の conn に監査スキーマを追加する場合
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)

# 監査専用 DB を初期化する場合
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 基本的な使い方（コード例）

J-Quants から日足を取得して DuckDB に保存する一連の処理例:

```python
from kabusys.data.jquants_client import (
    fetch_daily_quotes,
    save_daily_quotes,
    get_id_token
)
from kabusys.data import schema

# DB を初期化（既存ならスキップ）
conn = schema.init_schema("data/kabusys.duckdb")

# 必要に応じて id_token を先に取得（通常は fetch 関数が自動でキャッシュする）
# token = get_id_token()

# 銘柄コードを指定して取得
records = fetch_daily_quotes(code="7203")  # 例: トヨタ (7203)
n = save_daily_quotes(conn, records)
print(f"{n} 件を保存しました")
```

財務データ・マーケットカレンダーも同様の API を使用できます:
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

データ品質チェックの実行例:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続
issues = run_all_checks(conn, target_date=None)  # 全チェック
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)
```

---

## 補足（設計上のポイント）

- J-Quants クライアントはレート制限（120 req/min）に従うため、内部的にスロットリングを行います。
- ネットワークエラーや 408/429/5xx に対しては最大 3 回の再試行（指数バックオフ）を行います。401 を受けた場合はリフレッシュトークンで自動的に id_token を更新して 1 回リトライします。
- DuckDB への挿入は冪等性を確保するため ON CONFLICT DO UPDATE を利用しています。
- すべてのタイムスタンプは UTC を基本とする設計（監査ログでは SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージエントリ; __version__ = "0.1.0")
  - config.py    (環境変数・設定管理: settings)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、保存関数)
    - schema.py          (DuckDB スキーマ定義・初期化)
    - audit.py           (監査ログ用スキーマ・初期化)
    - quality.py         (データ品質チェック)
    - (その他ファイル: raw/execution など)
  - strategy/
    - __init__.py        (戦略モジュール拡張ポイント)
  - execution/
    - __init__.py        (発注・ブローカー連携拡張ポイント)
  - monitoring/
    - __init__.py        (監視・メトリクス拡張ポイント)

---

## 開発・運用における注意点

- KABUSYS_ENV は development / paper_trading / live を受け付けます。live を指定すると本番用の挙動（将来的に実装される安全機構）が有効になる想定です。
- .env.local は .env の上書きとして読み込まれます。OS 環境変数は自動ロードで上書きされません（保護）。
- テーブル DDL やチェックロジックはプロトタイプ段階の設計が含まれます。運用前に要件に合わせた監査・テストを強く推奨します。

---

ご質問や追加のドキュメント（API 使用例、運用手順、バージョン管理方針等）が必要であればお知らせください。