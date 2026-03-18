# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API と kabuステーション（発注系モジュールは未実装の枠組み）を組み合わせて、データ取得（価格・財務・カレンダー・ニュース）、ETL、品質チェック、監査ログを行うことを目的としています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構成するための内部ライブラリ群です。主に以下を提供します。

- J-Quants API クライアント（価格、財務、JPX カレンダー）
- RSS ベースのニュース収集・前処理モジュール（SSRF対策・サイズ制限・重複排除）
- DuckDB に基づくスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 環境変数/設定管理（.env 自動ロード機構）

設計上のポイント:
- API レート制限遵守（J-Quants: 120 req/min）
- リトライ（指数バックオフ、401 の自動トークン更新）
- データ保存は冪等（ON CONFLICT を使用）
- セキュリティ対策（XML の defusedxml、SSRF 対策、受信サイズ制限 等）

---

## 主な機能一覧

- config
  - 環境変数読み込み（.env / .env.local 自動ロード）
  - 必須設定のラッパー（settings）
- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レートリミッタ・リトライ・トークンキャッシュ実装
- data.news_collector
  - fetch_rss（XMLパース、gzip対応、URL正規化、SSRF対策）
  - save_raw_news / save_news_symbols（DuckDB へのバルク保存）
  - extract_stock_codes（本文から4桁銘柄コード抽出）
- data.schema
  - DuckDB テーブル DDL 定義、init_schema / get_connection
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新、バックフィル、品質チェックの統合
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめて実行）
- data.audit
  - 監査ログ用テーブル定義、init_audit_schema / init_audit_db

（strategy, execution, monitoring はパッケージ枠のみを用意）

---

## セットアップ手順

環境に合わせて Python と依存パッケージを用意してください。最低限の依存は次の通りです（実プロジェクトでは pyproject.toml / requirements.txt を用意してください）。

必須パッケージ（例）:
- Python 3.10+
- duckdb
- defusedxml

pip の例:
```
pip install duckdb defusedxml
```

インストール例（開発時）:
```
# パッケージとしてインストールできる場合
pip install -e .

# または依存関係を手動インストール
pip install duckdb defusedxml
```

環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード（発注系が実装される想定）
- SLACK_BOT_TOKEN (必須) — 通知用 Slack トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネルID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL (任意) — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）

.env の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、
  .env を読み込み、続けて .env.local を上書き読み込みします。
- OS 環境変数は保護（.env が既に存在するキーを上書きしない）。
- 自動ロードを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（基本例）

以下は代表的な利用例です。実行前に必要な環境変数を設定し、DuckDB の初期化を行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")

# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) J-Quants トークン取得（内部で settings.jquants_refresh_token を使う）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照
```

3) 日次 ETL 実行（市場カレンダー・価格・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

4) ニュース収集ジョブ実行例
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")

# known_codes は抽出対象とする銘柄コード集合（例: 上場銘柄リスト）
known_codes = {"7203", "6758", "9984"}

results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規挿入件数}
```

5) カレンダー操作例
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = get_connection("data/kabusys.duckdb")
d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 注意点 / 設計上の特徴

- レート制御: jquants_client は 120 req/min を守るために固定間隔のスロットリングを行います。
- リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回リトライします。401 の場合はリフレッシュを一度試みます。
- 冪等性: データ保存は可能な限り ON CONFLICT で上書き or 無視（news は DO NOTHING）する設計です。
- ニュース収集: URL 正規化・トラッキングパラメータ除去、SSRF 対策（リダイレクト検査、プライベートIP検出）、受信サイズ制限（10MB）など安全対策を実装しています。
- 品質チェック: ETL の最後に run_all_checks を呼ぶことで、欠損・スパイク・重複・日付不整合を検出できます。重大度に応じて呼び出し側で処理を決めてください（ETL は Fail-Fast ではない設計）。

---

## ディレクトリ構成

プロジェクト内の主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント
      - news_collector.py              — RSS ニュース収集
      - pipeline.py                    — ETL パイプライン
      - schema.py                      — DuckDB スキーマ定義 / init_schema
      - calendar_management.py         — マーケットカレンダー管理
      - audit.py                       — 監査ログテーブル初期化
      - quality.py                     — データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（上記以外にドキュメント / CI 設定 / pyproject.toml などがプロジェクトルートにある想定）

---

## よくある操作・トラブルシューティング

- .env が読み込まれない / テストで読み込みを抑えたい  
  -> 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

- J-Quants の 401 が頻発する  
  -> get_id_token によるトークン取得や settings.jquants_refresh_token の値を確認してください。jquants_client は 401 で一度トークンを更新してリトライします。

- ニュース収集で XML パースエラーが発生する  
  -> フィードが非標準な構造や壊れている場合があります。fetch_rss はパース失敗時に警告を出して空リストを返します。

- DuckDB のテーブルが欠けている / schema.init_schema を実行してください。監査テーブルのみ追加する場合は data.audit.init_audit_schema / init_audit_db を使用します。

---

## 今後の拡張ポイント（参考）

- strategy / execution / monitoring モジュールの実装（戦略ロジック、発注ラッパー、監視ダッシュボード）
- kabuステーションとの発注実装（execution 層）
- CI 用のテストスイート、型チェック、パッケージ配布設定
- News ソースの拡充・自然言語処理による銘柄抽出精度向上

---

必要に応じて README の補足（例: requirements.txt、実行スクリプト、環境変数の .env.example など）を作成できます。追加したい内容があれば指示してください。