# KabuSys

日本株自動売買プラットフォームのコアライブラリ群です。データ取得・スキーマ管理・品質チェック・監査ログなど、戦略実行に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下を提供します。

- J-Quants API からの市場データ取得（OHLCV、財務データ、マーケットカレンダー）
- DuckDB ベースの永続化スキーマ（Raw / Processed / Feature / Execution 層）
- 監査（audit）ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数 / 設定の取り回しユーティリティ

設計上の注目点:
- API レート制御（120 req/min）とリトライ（指数バックオフ、401 時のトークンリフレッシュ対応）
- DuckDB への冪等的保存（ON CONFLICT DO UPDATE を利用）
- 監査ログは削除しない前提で設計（ON DELETE RESTRICT）
- すべての TIMESTAMP は UTC で扱う（監査周りなど）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN）
  - 実行環境切替（development / paper_trading / live）とログレベル検証
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 認証（refresh token → id_token 自動取得）
  - レートリミッタ・リトライ・ページネーション対応
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス
  - init_schema(), get_connection()
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義と初期化
  - init_audit_schema(), init_audit_db()
- データ品質チェック（kabusys.data.quality）
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付不整合（future_date / non_trading_day）
  - run_all_checks() による一括実行（QualityIssue のリストを返す）

---

## セットアップ手順

前提:
- Python 3.10 以上（コードは type union（|） を使用）
- Git ベースのプロジェクトルートを持つ想定（自動 .env ロードのため）

1. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージのインストール（最低限）
   ```bash
   pip install duckdb
   ```
   ※ ネットワークアクセス用に標準ライブラリの urllib を使用しているため追加の HTTP クライアントは不要ですが、実環境ではロギングやテスト用に requests 等を使う可能性があります。

3. 環境変数の設定
   プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置することで自動読み込みされます。`.env.local` は `.env` の上書きとして読み込まれます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. プロジェクトルートの検出
   config モジュールは `__file__` を起点に親ディレクトリを探索し、`.git` または `pyproject.toml` の存在をもってプロジェクトルートと判断します。

---

## 使い方（基本例）

以下は主要 API の使用例です。実際はエラーハンドリングやログ出力を適切に追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(code="7203")  # 銘柄コード省略で全銘柄
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

3) 財務データ・マーケットカレンダー取得例
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar
fs = fetch_financial_statements(code="7203")
mc = fetch_market_calendar()
# save_financial_statements / save_market_calendar も同様に使用可能
```

4) 監査ログスキーマ初期化（既存 DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

あるいは監査専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

5) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
    for row in i.rows:
        print(row)
```

---

## 環境変数（主要）

必須（呼び出す機能により使用）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL） デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルのパス デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

注意: config.Settings は必須環境変数が未設定の場合 ValueError を投げます。

---

## 実装のポイント（運用上の注意）

- J-Quants API は 120 req/min のレート制限を想定しています。jquants_client は固定間隔（スロットリング）で待機します。
- HTTP エラー（408/429/5xx）に対するリトライ、429 に対する Retry-After 優先、401 に対するトークン自動リフレッシュ（1回）を実装しています。
- データ保存は冪等化されており、重複挿入は ON CONFLICT DO UPDATE によって上書きされます。
- 監査ログは削除を想定しておらず、order_request_id を冪等キーとして再送制御ができます。
- 監査系の TIMESTAMP は UTC 固定。このため init_audit_schema() は接続に対して `SET TimeZone='UTC'` を実行します。

---

## ディレクトリ構成

主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/  (実装の入り口)
      - __init__.py
    - strategy/   (戦略実装の入り口)
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存）
      - schema.py                # DuckDB スキーマ定義・初期化
      - audit.py                 # 監査ログスキーマ定義・初期化
      - quality.py               # データ品質チェック
      - audit.py
      - quality.py

（上記は本リポジトリに含まれている主要モジュールです。実際のツリーは .git や pyproject.toml 等を含むことを想定しています。）

---

必要であれば README に加えて以下も作成できます:
- .env.example のテンプレート
- 実運用時のデプロイ / cron / Airflow での ETL 実行例
- 単体テスト・モック戦略（HTTP レスポンス mock、DuckDB の :memory: 利用例）

必要な追加情報・サンプルを教えてください。README を拡張して具体的なサンプルや運用手順（cron, Docker, CI）を追記します。