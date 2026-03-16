# KabuSys

日本株自動売買システム用のコアライブラリ（データプラットフォーム・ETL・監査ログ・APIクライアントなど）

このリポジトリは、J-Quants API からのマーケットデータ取得、DuckDB ベースのスキーマ管理、データ品質チェック、ETL パイプライン、監査ログ（発注→約定のトレーサビリティ）など、自動売買システムの基盤機能を提供します。

---

## プロジェクト概要

主な目的：
- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得して DuckDB に保存する。
- ETL（差分更新・バックフィル）を実行し、データ品質チェックを行う。
- 監査ログ（シグナル→発注→約定）を保持してフロー全体のトレーサビリティを確保する。
- kabuステーション API や Slack 等との連携に必要な設定を環境変数で管理する。

設計上の特徴：
- API レート制限（120 req/min）遵守（固定間隔スロットリング）。
- リトライ（指数バックオフ）と 401 時の自動トークンリフレッシュ対応。
- データ取得は Look-ahead バイアスを避けるため fetched_at を UTC で記録。
- DuckDB の INSERT は冪等（ON CONFLICT DO UPDATE）で実装。
- データ品質チェックは fail-fast ではなく全問題を収集して返す。

---

## 機能一覧

- J-Quants API クライアント
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存用関数: save_daily_quotes, save_financial_statements, save_market_calendar

- DuckDB スキーマ管理
  - データレイヤ（Raw / Processed / Feature / Execution）をカバーする DDL
  - init_schema(db_path) — スキーマ初期化と接続取得
  - get_connection(db_path)

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得）
  - backfill による後出し修正吸収
  - run_daily_etl(conn, target_date=..., ...) — 日次 ETL の統合実行

- データ品質チェック
  - 欠損検出、スパイク検出（前日比）、重複チェック、日付整合性チェック
  - run_all_checks(conn, ...) — すべてのチェックを実行して QualityIssue リストを返す

- 監査ログ（audit）
  - signal_events, order_requests, executions のテーブル
  - init_audit_schema(conn), init_audit_db(path)

- 環境変数管理
  - .env / .env.local を自動ロード（プロジェクトルート検出）
  - Settings クラス経由で設定値を取得（settings オブジェクト）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 要件

- Python 3.10+
- duckdb (pip install duckdb)
- 標準ライブラリ（urllib, json, logging 等）
- J-Quants / kabuステーション / Slack のアクセストークン（環境変数で提供）

（パッケージ化用に pyproject.toml 等がある前提）

---

## 環境変数（主なもの）

以下は本ライブラリが参照する主要な環境変数です。プロジェクトルートに `.env` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development, paper_trading, live; デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト: INFO）

例（.env）:
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

1. Python 3.10+ を用意
2. 依存ライブラリをインストール
   - duckdb のみが明示的に必要
   - pip install duckdb
3. リポジトリルートに `.env`（または `.env.local`）を作成し、上記の必須変数を設定
4. DuckDB スキーマを初期化（次の「使い方」を参照）

※ テスト環境や CI で自動的に `.env` の読み込みを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要な利用例）

以下は Python REPL やスクリプトからライブラリを使う基本例です。

1) スキーマ初期化（DuckDB）と接続取得
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を経由して決定される
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

引数例:
- target_date: ETL の対象日（省略で今日）
- id_token: テスト目的で明示的な J-Quants ID トークンを渡せる
- run_quality_checks: 品質チェックの実行有無
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）

3) 監査ログテーブルの初期化（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

または監査専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

4) J-Quants API を直接使う例
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

# トークンは settings.jquants_refresh_token から自動取得される
quotes = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# 保存
saved = jq.save_daily_quotes(conn, quotes)
```

5) 品質チェックを単独で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue)
```

---

## 典型的な運用フロー（例）

- 夜間バッチ: run_daily_etl をスケジュール（cron / Airflow 等）で実行し、当日の営業データ・先読みカレンダーを取得する。
- ETL 実行後に品質チェック結果を Slack に通知し、重大なエラーがあればアラートを上げる。
- 戦略層は features / ai_scores を参照してシグナルを生成、signal_queue → 発注処理 → executions を audit テーブルでトレースする。

---

## 注意点 / 補足

- Python の型ヒントに 3.10 以降の構文（`X | None`）を使用しているため、Python 3.10+ を想定しています。
- J-Quants API のレート制限（120 req/min）を守るため内部でスロットリングがかかります。
- ネットワークエラーや 5xx 等に対するリトライロジック（指数バックオフ、最大 3 回）を備えています。401 は自動トークンリフレッシュを試みます（1 回のみ）。
- DuckDB スキーマは冪等に作成されます。既存データは ON CONFLICT DO UPDATE により上書きされます。
- ETL・品質チェックは可能な限りエラーを集約して返す設計です（Fail-Fast ではありません）。

---

## ディレクトリ構成

リポジトリの主要ファイル / ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / 設定管理（settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py              -- DuckDB スキーマ定義と init_schema / get_connection
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - quality.py             -- データ品質チェック
      - audit.py               -- 監査ログテーブル定義・初期化
      - pipeline.py            -- ETL の差分・バックフィル・品質チェックの統合
    - execution/                -- 発注/約定関連（未実装ファイルがプレースホルダ）
    - strategy/                 -- 戦略層（未実装ファイルがプレースホルダ）
    - monitoring/               -- 監視関連（プレースホルダ）

実装済みの主要モジュール：
- kabusys.config — Settings, 自動 .env ロード
- kabusys.data.jquants_client — API クライアント + 保存関数
- kabusys.data.schema — DDL と init_schema/get_connection
- kabusys.data.pipeline — ETL ロジック
- kabusys.data.quality — 品質チェック
- kabusys.data.audit — 監査ログ用 DDL と初期化

---

## 開発 / 貢献

- まずは `DUCKDB_PATH`（.env）を設定し、ローカルで init_schema → run_daily_etl を実行して挙動確認してください。
- 単体テスト・CI の導入、戦略層・実行層の実装、発注連携（kabuAPI）や Slack 通知は今後の拡張ポイントです。

---

もし README に追加したい別の使用例（Airflow タスク例、Slack 通知サンプル、kabuステーション連携の具体例など）があれば教えてください。必要に応じてサンプルコードや CI 設定の雛形も作成します。