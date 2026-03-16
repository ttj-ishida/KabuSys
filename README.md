# KabuSys

日本株の自動売買プラットフォーム向けのライブラリ群。データ取得、DBスキーマ管理、監査ログ、データ品質チェックなどの基盤機能を提供します。

主な設計方針
- データの取得は外部API（J‑Quants 等）から行い、取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を防止
- DuckDB を中心とした3層データモデル（Raw / Processed / Feature）＋実行／監査テーブルを定義
- API レート制御とリトライ（指数バックオフ、401 時のトークン自動リフレッシュ）を備えたクライアント実装
- 監査ログによりシグナル→発注→約定までトレーサビリティを確保
- データ品質チェックを SQL ベースで効率的に実行

---

## 機能一覧

- 環境変数読み込み・管理（.env / .env.local の自動読み込み、プロジェクトルート検出）
- J-Quants API クライアント
  - 日足（OHLCV）データ取得（ページネーション対応）
  - 財務諸表（四半期）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レートリミット制御（120 req/min）とリトライ、トークン自動リフレッシュ
  - DuckDB への冪等な保存関数（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義
  - init_schema(), get_connection() による接続提供
- 監査（Audit）スキーマ
  - signal_events / order_requests / executions の定義、初期化
  - 監査用インデックス
  - init_audit_schema(), init_audit_db()
- データ品質チェック
  - 欠損データ、異常値（スパイク）、重複、日付不整合の検出
  - run_all_checks() で一括実行。QualityIssue オブジェクトのリストを返す
- パッケージ構成（strategy, execution, monitoring のプレースホルダあり）

---

## 前提条件

- Python 3.10 以上（PEP 604 のパイプ型等を利用）
- duckdb
- (標準ライブラリ: urllib, json, logging 等)

依存関係のインストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージをプロジェクトとして使う場合（pyproject.toml がある前提）
pip install -e .
```

---

## 環境変数 / 設定

必須の環境変数（アプリ起動前に設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live; デフォルト: development)
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml の存在）を基準に .env と .env.local を自動で読み込みます。
- 読み込み順: OS環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリを取得
```bash
git clone <repository-url>
cd <repository>
```

2. Python 仮想環境の作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# 必要に応じてパッケージを editable インストール（pyproject.toml がある場合）
pip install -e .
```

3. 環境変数を設定（上の .env 例を参照）。プロジェクトルートに `.env` または `.env.local` を置けば自動読み込みされます。

4. DuckDB スキーマの初期化（Python REPL かスクリプトで実行）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル DB
# またはインメモリ
# conn = init_schema(":memory:")
```

5. 監査テーブルを追加する場合
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
# または監査専用 DB を作る
# from kabusys.data.audit import init_audit_db
# audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な API と例）

- J-Quants の日足データを取得して DuckDB に保存する簡単な例:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DB 初期化 / 接続
conn = init_schema(settings.duckdb_path)

# データ取得
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存したレコード数: {n}")
```

- 財務諸表・カレンダー取得と保存も同様に fetch_financial_statements/save_financial_statements,
  fetch_market_calendar/save_market_calendar を使用します。

- トークン取得（明示的に使う場合）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

- データ品質チェックの実行例:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for sample in issue.rows:
        print(sample)
```

主要な挙動のポイント
- fetch_* 関数はページネーションに対応し、id_token のキャッシュを共有します
- HTTP 401 を受信した場合は自動で refresh token から id_token を再取得して 1 回リトライします（無限ループ防止）
- API 呼び出しは固定間隔スロットリング（120 req/min）で制御されます
- DuckDB への保存関数は ON CONFLICT DO UPDATE を利用して冪等性を担保します
- すべてのタイムスタンプは UTC で扱われます（監査テーブルは明示的に TimeZone='UTC' を設定）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理、.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 + DuckDB 保存）
    - schema.py                  — DuckDB スキーマ定義・初期化
    - audit.py                   — 監査ログ（signal / order_request / executions）
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略用モジュール（プレースホルダ）
  - execution/
    - __init__.py                — 発注/実行周り（プレースホルダ）
  - monitoring/
    - __init__.py                — 監視用モジュール（プレースホルダ）

---

## 注意事項 / 実運用上のヒント

- 本ライブラリは取引システムの基盤モジュールを提供します。実際の発注ロジックやリスク管理は別途実装してください（execution, strategy モジュールを拡張）。
- 本番運用（KABUSYS_ENV=live）ではログレベルや Slack 通知等、運用監視の設定を十分に行ってください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログは削除を想定していません。
- テストや CI では環境変数自動読み込みを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると安全です。

---

## 貢献・拡張

- strategy / execution / monitoring といった層を拡張して具体的な戦略やブローカー接続を追加してください。
- 追加のデータソース（ニュース、IR、Alternative Data）を raw 層に取り込み、feature 層を拡張することで性能改善が期待できます。
- QualityIssue のスキーマやしきい値は運用に合わせて調整してください。

---

README に記載の不明点や、特定の使用例（戦略実装、発注フロー、監査クエリなど）が必要であれば具体的な要件を教えてください。追加のコード例や運用ガイドを作成します。