# KabuSys

日本株向け自動売買プラットフォーム向けのユーティリティパッケージ群です。  
データ取得・スキーマ管理・データ品質チェック・監査ログなど、バックテスト／本番運用の基盤となる機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の領域をカバーします。

- 外部データ取得（J-Quants API からの株価・財務・市場カレンダー）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 環境変数管理（.env 自動読み込み、必須変数の取得ラッパー）

設計方針として、API レート制限とリトライ制御、UTC タイムスタンプによるトレーサビリティ、冪等性（ON CONFLICT）などを重点的に取り入れています。

---

## 機能一覧

- 環境設定
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須環境変数取得 & 検証（settings オブジェクト）
- J-Quants クライアント（kabusys.data.jquants_client）
  - IDトークンの取得（自動リフレッシュ）
  - 日足（OHLCV）・財務データ（四半期）・JPX 市場カレンダーの取得（ページネーション対応）
  - API レート制限（120 req/min）対応のスロットリング
  - 再試行（指数バックオフ・特定ステータスでのリトライ）実装
  - DuckDB への保存関数（冪等性を維持）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - init_schema() でファイルを作成・初期化、get_connection() で接続取得
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル
  - 冪等キー（order_request_id）やインデックスを備えた監査用スキーマ
  - init_audit_schema() / init_audit_db()
- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）・スパイク（前日比閾値）・重複（PK）・日付不整合（未来日・非営業日）
  - run_all_checks() でまとめてチェック、QualityIssue リストを返す

---

## 動作環境 / 依存

- Python 3.10 以上（型注釈に `|` を使用）
- 必須ライブラリ（例）
  - duckdb
- 標準ライブラリ：urllib, json, logging, datetime, pathlib など

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# package を editable install したい場合はプロジェクトルートに setup / pyproject があれば:
# pip install -e .
```

---

## 環境変数（主なもの）

kabusys.config.Settings により参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は `1` を設定

自動 .env 読み込みについて:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
- 既存の OS 環境変数は上書きされません（`.env.local` は override=True だが protected により OS 環境は保護）。
- 自動読み込みを停止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secretpassword
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install duckdb
   - その他プロジェクトで必要なパッケージがあれば追加
4. .env を作成（上記参照）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます
5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで init_schema を実行（後述参照）

---

## 使い方（主要な API と例）

以下は代表的な利用フローの例です。

1) DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# :memory: を渡すとインメモリ DB になります
```

2) J-Quants から日足を取得して保存:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# トークンは settings.jquants_refresh_token に基づき自動取得/リフレッシュされます
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
count = save_daily_quotes(conn, records)
print(f"保存件数: {count}")
```

3) 財務データ / 市場カレンダーの取得と保存:
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fins = fetch_financial_statements(code="7203")
save_financial_statements(conn, fins)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査スキーマの初期化（既存 conn に追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを追加
```

5) データ品質チェックの実行:
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  sample:", row)
```

6) 設定値の参照:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 環境変数が未設定だと ValueError を送出
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

注意点:
- J-Quants API 呼び出しは内部でレート制限（120 req/min）とリトライを扱います。ただし短時間で大量ページネーションを行う場合は注意してください。
- get_id_token() では allow_refresh=False を使って無限再帰を防止しています（内部実装参照）。
- DuckDB の INSERT は ON CONFLICT DO UPDATE を用い冪等性を確保していますが、外部からの直接挿入などで不整合が発生し得るため品質チェックを推奨します。

---

## ディレクトリ構成

プロジェクト内の主なファイルとモジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py           -- J-Quants API クライアント（取得 + DuckDB 保存）
      - schema.py                   -- DuckDB スキーマ定義・初期化
      - audit.py                    -- 監査ログテーブル定義・初期化
      - quality.py                  -- データ品質チェック（欠損・スパイク・重複・日付不整合）
      - (その他: news/auditing などの将来的拡張点)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

README に記載していないモジュール（strategy, execution, monitoring）はエントリ用のパッケージプレースホルダとして準備されています。

---

## 運用上の注意 / ベストプラクティス

- 環境変数管理は慎重に行ってください。特に本番（live）ではシークレットを安全に保管してください。
- duckdb のファイルはバックアップやローテーションを検討してください。大規模取引ログや監査ログは肥大化し得ます。
- API キーのレート制限に留意し、定期バッチや並列処理はスロットリングを適切に行ってください。
- 品質チェックは ETL パイプラインの一部として自動実行し、重大な error はパイプライン停止処理へつなげることを推奨します。
- 監査ログテーブルは削除しない方針（ON DELETE RESTRICT）を基本としているため、データ保持ポリシーを事前に設計してください。

---

## 開発 / 貢献

バグ報告や機能提案はリポジトリの Issue でお願いします。プルリクエストは unit test と簡単な説明を添えて送ってください。

---

以上がこのリポジトリの README です。必要であればサンプルスクリプトや .env.example、docker-compose（Kabuステーションのモック等）の追加案も作成できます。希望があれば教えてください。