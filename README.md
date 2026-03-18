# KabuSys

日本株の自動売買 / データ基盤ライブラリ。  
J-Quants や RSS を使った市場データ収集、DuckDB ベースのスキーマ管理、ETL・品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株自動売買システム向けの共通ライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（株価日足、財務データ、JPXカレンダー）取得
- RSS からのニュース収集と記事→銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化・接続管理
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/期間の営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損、異常スパイク、重複、日付不整合など）

設計上の特徴:
- API レート制限順守（J-Quants: 120 req/min）とリトライ（指数バックオフ）
- 取得時刻（fetched_at）や UTC のタイムスタンプにより Look-ahead Bias を抑制
- DuckDB の ON CONFLICT / RETURNING を活用した冪等性と正確な挿入結果取得
- RSS 収集時の SSRF/GZipBomb/XML インジェクション対策（defusedxml、ホストチェック、サイズ制限）

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパー、環境モード判定（development / paper_trading / live）
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - トークン自動リフレッシュ、レート制御、リトライ
  - DuckDB への保存用ユーティリティ（冪等的保存）
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得・前処理・記事ID生成（URL正規化 + SHA-256）
  - raw_news 保存、news_symbols（銘柄紐付け）保存
  - SSRF/サイズ/圧縮/XML セキュリティ対策
- スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL を定義
  - init_schema / get_connection を提供
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分取得（最終取得日ベース）・バックフィル・品質チェックを含む日次 ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等
- カレンダー管理（src/kabusys/data/calendar_management.py）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（夜間バッチでのカレンダー差分更新）
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions など監査テーブルの初期化と管理
  - init_audit_schema / init_audit_db
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損、重複、スパイク、日付不整合チェック
  - QualityIssue 型を返す一括チェック run_all_checks
- 空のパッケージプレースホルダ:
  - src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring（今後の拡張領域）

---

## 必要環境 / 依存

- Python 3.10 以上（typing の | 演算子などを使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発時はローカルパッケージとしてインストールする場合:
pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## 環境変数（必須 / 任意）

config モジュールで利用する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネルID

任意（デフォルトあり）:
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動読み込み:
- プロジェクトルートにある `.env` と `.env.local` が自動で読み込まれます（OS 環境変数が優先）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

.example のサンプル（README 用）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージのインストール
   ```bash
   pip install duckdb defusedxml
   # development 用にパッケージ全体を editable install する場合
   pip install -e .
   ```

3. 環境変数設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成し、上記の必須キーを設定します。
   - テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うことがあります。

4. DuckDB スキーマ初期化
   - アプリから次を呼び出して DB を初期化します（例: Python REPL またはスクリプト）。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査用 DB を分離したい場合:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な API 例）

以下は代表的な利用例です。実環境では適切なロギング設定や例外処理を行ってください。

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline
# DB 初期化済みとする
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved={saved}")
```

- RSS ニュース収集ジョブ実行
```python
from kabusys.data import news_collector as nc
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # など、有効な銘柄コードセット
results = nc.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- マーケットカレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management as cm
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = cm.calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 監査スキーマの初期化（既存接続に追加）
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

---

## ログとデバッグ

- 設定は環境変数 LOG_LEVEL で変更できます（INFO, DEBUG など）。
- config の env 判定により is_live / is_paper / is_dev プロパティを参照可能です。
- J-Quants クライアントはリトライや月次レート制御を行います。ログでリトライや 401 リフレッシュ情報が出力されます。

---

## ディレクトリ構成

（主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (発注ロジック用パッケージ、現状プレースホルダ)
    - __init__.py
  - strategy/ (戦略実装用パッケージ、現状プレースホルダ)
    - __init__.py
  - monitoring/ (モニタリング用パッケージ、現状プレースホルダ)
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - pipeline.py             — ETL パイプライン（差分更新・品質チェック）
    - schema.py               — DuckDB スキーマ定義と初期化
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - audit.py                — 監査ログスキーマ（signal/order/execution）
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 注意点 / 運用上の留意事項

- Python バージョンは 3.10 以上を推奨します。
- J-Quants API のレート制限（120 req/min）に注意してください。モジュール内でスロットリングは行われますが、複数プロセスから同時に呼び出す場合は別途制御が必要です。
- DuckDB はシングルファイル DB として扱えますが、同一ファイルへの多重プロセス書き込みは注意が必要です（運用環境では接続方式を検討してください）。
- RSS 収集は外部 URL に接続するため、SSRF 対策やタイムアウト設定を有効にしています。それでも外部サイトの挙動によっては失敗することがあります。
- 監査ログ（audit）はトレーサビリティ目的で削除しない前提のテーブル設計です。

---

## 今後の拡張

- execution / strategy / monitoring の具体実装（ブローカー連携、戦略プラグイン、Slack 通知等）
- ETL のスケジューリング（Airflow / cron 連携サンプル）
- テストケース・CI 設定の追加
- web UI / ダッシュボードによる監視

---

README に記載の内容でわからない点や、追加してほしい使用例・セクション（例: CI 設定、デプロイ手順、実行スクリプトテンプレートなど）があれば教えてください。