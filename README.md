# KabuSys

日本株向け自動売買プラットフォームのライブラリ群。データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、戦略実行基盤に必要な機能を揃えています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズムトレーディング基盤のためのモジュール群です。主な役割は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX マーケットカレンダー）
- DuckDB を用いたスキーマ定義と冪等的な保存
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF対策、XML攻撃対策）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env / .env.local を自動読み込み）

設計上のポイント：
- API レート制御（J-Quants: 120 req/min）
- 自動トークンリフレッシュ、リトライ（指数バックオフ）
- データ保存は冪等（ON CONFLICT）で安全に上書き
- データ品質チェックを柔軟に実行可能

---

## 機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レート制御、リトライ、トークン自動更新
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) / get_connection(db_path)
- data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次 ETL 統合エントリ（run_daily_etl）
- data.news_collector
  - RSS 取得（fetch_rss）、前処理、記事保存（save_raw_news）、銘柄紐付け（save_news_symbols）
  - SSRF 対策、XML インジェクション対策、受信サイズ制限
- data.calendar_management
  - 営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - 夜間バッチでカレンダー更新（calendar_update_job）
- data.quality
  - 欠損検出、スパイク検出、重複チェック、日付不整合チェック（run_all_checks）
- data.audit
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
- config
  - 環境変数管理（自動 .env 読み込み、必須変数チェック、環境モード判定）

---

## 前提／依存関係

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt を参照して最終的な依存をインストールしてください）

---

## 環境変数

自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先され、`.env.local` が `.env` を上書き）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須変数（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意/デフォルト:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - git clone <リポジトリURL>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - pip install -e .
   （プロジェクト配布の要件ファイルがある場合はそちらを利用）
4. 環境変数を用意
   - プロジェクトルートに `.env` を作成（上の例を参照）
   - 必須変数を設定すること

---

## 使い方（簡単なサンプル）

以下は Python から主要処理を実行する例です。

- DuckDB スキーマ初期化（最初に一度だけ）

```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# これでテーブルが作成されます（既存ならスキップ）
conn.close()
```

- 監査 DB 初期化（監査専用 DB を別途作る場合）

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/audit.duckdb")
audit_conn.close()
```

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- RSS ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄コードセット（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)
conn.close()
```

- マーケットカレンダー更新（夜間バッチ想定）

```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
conn.close()
```

- 設定値の参照

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 実装上の注意点 / 設計メモ

- J-Quants クライアントは 120 req/min のレートを守るために固定間隔スロットリングを使用します。リトライは最大3回、408/429/5xx を対象に指数バックオフを実行します。401 を受けた場合はリフレッシュトークンで自動更新し 1 回リトライします。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）に設計してあります。
- news_collector は SSRF 対策（スキーム検証、プライベートホストブロック、リダイレクト検査）、XML 攻撃対策（defusedxml）、受信サイズ制限（デフォルト 10MB）などを実装して堅牢化しています。
- data.pipeline は差分更新（最終取得日ベース）とバックフィル（デフォルト 3 日）により API の後出し修正を吸収する設計です。
- 品質チェックは fail-fast ではなく問題を収集して呼び出し元に渡す方式です（呼び出し側で運用方針に応じて処理を決定します）。

---

## ディレクトリ構成

主要ファイル／ディレクトリ構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
    - news_collector.py       — RSS ニュース取得・前処理・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義 & 初期化
    - pipeline.py             — ETL パイプライン（差分更新・統合）
    - calendar_management.py  — マーケットカレンダー管理ロジック
    - audit.py                — 監査ログ用スキーマ（トレーサビリティ）
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（strategy / execution / monitoring は拡張用の空モジュールが配置されています）

---

## よくある運用フロー（例）

- 夜間バッチ（Cron / Airflow 等）
  1. calendar_update_job でカレンダーを更新
  2. run_daily_etl を呼び ETL と品質チェックを実行
  3. ETLResult を Slack などへ通知し、品質問題があればアラート発報

- リアルタイム / 発注フロー
  - strategy 層で signals を生成 → audit / order_request を作成 → execution 層で証券会社 API へ送信 → executions を監査テーブルへ記録

---

## テスト / 開発

- 単体テストは各モジュールの関数をインメモリ DuckDB（":memory:"）やモックした HTTP/ネットワークを使って行うと安定します。
- news_collector._urlopen や jquants_client のネットワーク呼び出しはテスト用にモック可能です（コード内で関数を差し替えられる設計）。

---

## ライセンス・貢献

リポジトリの LICENSE を参照してください。バグ報告やプルリクエストは歓迎します。

---

README に不足する点や、特定のユースケース（例: 戦略の信号保存の流れ、kabuステーション連携サンプル）についての追加ドキュメントが必要であれば教えてください。