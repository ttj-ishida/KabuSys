# KabuSys

日本株向けの自動売買データ基盤・ETL・監査モジュール群です。J-Quants / kabuステーション 等と連携して、
データ取得（OHLCV・財務・マーケットカレンダー）、DuckDB スキーマ管理、ETL パイプライン、品質チェック、
監査ログ（シグナル→発注→約定トレース）を提供します。

主に内部ライブラリとして利用することを想定しており、戦略・実行層は別モジュールで拡張できます。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）と指数バックオフによるリトライ、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead-bias を防止

- データベーススキーマ（DuckDB）
  - 3 層構造（Raw / Processed / Feature）＋ Execution / Audit 用テーブルを定義
  - ON CONFLICT DO UPDATE を用いた冪等な保存処理
  - 頻出クエリを想定したインデックス定義

- ETL パイプライン
  - 差分更新（最終取得日から不足分のみ取得）＋バックフィル（後出し修正対応）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行し結果を集約

- データ品質チェック
  - 複数チェックを実行して QualityIssue のリストを返す（Fail-Fast ではなく全件収集）
  - スパイク閾値等をパラメータで制御可能

- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査用テーブル群
  - UUID によるトレーサビリティ（戦略 → シグナル → 発注 → 約定）
  - すべての TIMESTAMP は UTC 保存を前提

---

## 必要条件（依存関係）

- Python 3.10+
- duckdb
- （標準ライブラリ: urllib, json, logging 等を使用）

必要パッケージはプロジェクトの packaging / requirements ファイルに合わせてインストールしてください。開発時の最低限の例:

pip install duckdb

（プロジェクトに pyproject.toml / requirements.txt があればそちらを参照してください）

---

## 環境変数（必須 / 任意）

自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings._require により未設定時は例外）:
- JQUANTS_REFRESH_TOKEN     （J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD         （kabu API パスワード）
- SLACK_BOT_TOKEN           （Slack 通知用ボットトークン）
- SLACK_CHANNEL_ID         （通知対象チャネル ID）

任意 / デフォルトあり:
- KABUSYS_ENV               （development / paper_trading / live、デフォルト: development）
- LOG_LEVEL                 （DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH               （DuckDB ファイル、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH               （監視 DB 等、デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD （自動 .env ロードの無効化）

例: .env（最低限のキー）
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

1. リポジトリをクローン / プロジェクトを取得
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb
   - その他プロジェクトの requirements に応じてインストール
4. プロジェクトルートに `.env` を作成し、必須環境変数を設定
5. DuckDB スキーマを初期化（下記の使い方参照）

---

## 使い方（簡単な例）

以下は Python スクリプト / REPL からの基本的な使い方例です。

- DuckDB スキーマ初期化（メインスキーマ）
```python
from kabusys.data.schema import init_schema

# デフォルトパスを使いたい場合は settings.duckdb_path を参照するか、明示的に指定
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログスキーマの初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema

# conn は init_schema() で得た接続をそのまま渡して問題ありません
init_audit_schema(conn)
```

- J-Quants トークン取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って POST 呼び出し
```

- データ取得（例: 日次株価を API から直接取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

- 日次 ETL の実行（市場カレンダー取得 → 株価・財務の差分更新 → 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトは今日を対象
print(result.to_dict())
# result.quality_issues は QualityIssue オブジェクトのリスト
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 主なモジュール API 概要

- kabusys.config
  - settings: 環境変数から設定を取得する Settings インスタンス（jquants_refresh_token, kabu_api_password, duckdb_path 等）

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection（全テーブル作成、冪等）
  - get_connection(db_path) -> duckdb connection

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
  - get_last_price_date / get_last_financial_date / get_last_calendar_date

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]
  - check_missing_data / check_spike / check_duplicates / check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn)  # 監査ログ用テーブル追加
  - init_audit_db(db_path)   # 監査ログ専用 DB を初期化して接続を返す

---

## よくある運用上の注意

- API レート制限
  - J-Quants は 120 req/min を想定。クライアントは内部で固定間隔スロットリングを行います。

- トークンリフレッシュ
  - 401 受信時は自動でリフレッシュし 1 回だけリトライします。get_id_token の内部呼び出しでは無限再帰を防ぐため allow_refresh=False にしています。

- 冪等性
  - save_* 関数は ON CONFLICT DO UPDATE を利用して同じ (PK) に対する重複挿入を排除します。

- 品質チェック
  - run_all_checks は error/warning を集めて返します。ETL は基本的に各ステップ独立して継続する設計です。呼び出し元で重大度に応じた運用判断を行ってください。

- タイムゾーン
  - 監査ログ初期化時に `SET TimeZone='UTC'` を実行し、監査テーブルのタイムスタンプは UTC 前提です。

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env`, `.env.local` を読み込みます。テストなどで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（抜粋 — 実際のプロジェクトルートに合わせて調整してください）
```
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント + 保存ロジック
      pipeline.py                  # ETL パイプライン（差分更新、バックフィル、品質チェック）
      schema.py                    # DuckDB スキーマ定義と初期化
      audit.py                     # 監査ログ（signal/order/execution）定義
      quality.py                   # 品質チェック
    strategy/
      __init__.py                  # 戦略関連のエントリ（拡張ポイント）
    execution/
      __init__.py                  # 発注・ブローカー連携関連（拡張ポイント）
    monitoring/
      __init__.py                  # 監視ロジック（将来的に拡張）
```

---

## 開発・拡張ポイント（メモ）

- strategy / execution / monitoring は空のパッケージとして用意されています。ここに戦略ロジック、ポートフォリオ管理、ブローカー API ラッパー、監視ツール等を実装してください。
- DuckDB スキーマは DataPlatform.md / DataSchema.md に基づく想定です。運用に合わせてカラム追加やインデックス調整を行ってください。
- 品質チェックは SQL ベースで効率的に実行されますが、大量データや複雑チェックはパフォーマンスに注意してください。

---

## サポート / 貢献

バグ報告・機能追加の提案は Issue 経由でお願いします。プルリクエスト歓迎です。実装方針（冪等性・トレーサビリティ・UTC）を尊重して拡張してください。

---

以上が README の概要です。実運用向けのサンプルスクリプトや CI / cron からの定期実行例、モニタリング・アラート設定などが必要であれば、用途に合わせた具体的な README セクションを追加します。どの例がほしいか教えてください。