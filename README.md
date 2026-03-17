# KabuSys

日本株向けの自動売買基盤ライブラリ（Python）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ管理、監査ログなどの基本機能を提供します。

> 注: これはライブラリレベルのコードベースの README です。実運用では証券会社 API や発注ロジックの実装、運用監視などを適切に組み合わせてください。

## プロジェクト概要

KabuSys は次の目的を持つモジュール群を含むパッケージです。

- J-Quants API から株価・財務・カレンダーなどを安全かつ冪等に取得
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- RSS ベースのニュース収集（正規化・SSRF 対策・トラッキング除去・銘柄抽出）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 簡易な設定管理（.env 自動読み込み、環境変数経由）

設計上のポイント：
- API レート制御（J-Quants は 120 req/min を想定）
- リトライ・トークン自動リフレッシュ
- データ取得時の fetched_at によるトレーサビリティ（Look-ahead bias 回避）
- DuckDB へは冪等に書き込む（ON CONFLICT / DO UPDATE / DO NOTHING）

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須変数チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - ページネーション対応、リトライ、レートリミット
  - DuckDB への保存ユーティリティ（raw_prices, raw_financials, market_calendar）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DDL を定義・初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック、日次 ETL 実行
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、XML パース（defusedxml）、URL 正規化、記事ID生成、DB 保存、銘柄抽出
  - SSRF 保護、受信サイズ制限、gzip 解凍検査
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル、監査用インデックス
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日算出、夜間カレンダー更新ジョブ

## セットアップ手順

前提: Python 3.9+（typing の | 型表記を利用）を推奨します。

1. リポジトリを取得して仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   - 主な依存: duckdb, defusedxml
   - （プロジェクトで pyproject.toml / requirements.txt を用意している場合はそちらを使ってください）

   例:
   ```
   pip install duckdb defusedxml
   pip install -e .
   ```
   （パッケージを editable インストールできる構成であれば上記でローカル参照可能）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須の環境変数（kabusys.config.Settings より）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## 使い方（プログラム的に）

以下は基本的な利用例です。すべて Python スクリプトや REPL から呼び出します。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を作成・初期化
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

2) 監査ログスキーマを追加
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

主要な ETL サブジョブも個別に呼べます:
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

# 例: 今日分の株価差分 ETL
fetched, saved = run_prices_etl(conn, date.today())
```

4) ニュース収集の実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う 4 桁コードの集合（省略可能）
known_codes = {"7203", "6758", "9432"}  # 例
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source: 新規保存件数}
```

5) J-Quants の直接呼び出し（トークン管理は内部で行われる）
```python
from kabusys.data import jquants_client as jq

# ID トークンは設定の refresh token から自動取得される
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

6) 品質チェックの手動実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

## よく使う設定フラグ・注意点

- 自動 .env ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants レート制限: モジュール内で 120 req/min に合わせる RateLimiter を実装
- リトライポリシー: 408/429/5xx は指数バックオフで最大 3 回、401 はトークン自動更新を 1 回実行
- news_collector は SSRF 対策・gzip 上限チェックなどを行います。外部からの URL は http/https のみ許可。

## ディレクトリ構成

概略（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                       - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント + DuckDB 保存
    - news_collector.py              - RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py                      - DuckDB スキーマ DDL と init_schema / get_connection
    - pipeline.py                    - ETL パイプライン（差分更新・品質チェック含む）
    - calendar_management.py         - 市場カレンダーの判定 / 更新ジョブ
    - audit.py                       - 監査ログ（signal / order_request / executions）
    - quality.py                     - データ品質チェック
  - strategy/
    - __init__.py                    - 戦略関連（拡張用）
  - execution/
    - __init__.py                    - 発注・ブローカーインターフェース（拡張用）
  - monitoring/
    - __init__.py                    - 監視系（拡張用）

ファイルの主要責務:
- data/schema.py: 全テーブルの DDL を管理し、init_schema() による一括初期化を提供
- data/jquants_client.py: API 呼び出しの共通処理（認証・レート制御・リトライ）と DuckDB への保存ロジック
- data/pipeline.py: 差分取得のロジック、日次 ETL のオーケストレーション
- data/news_collector.py: RSS 取得から raw_news / news_symbols への保存、記事 ID と銘柄抽出
- data/quality.py: SQL ベースの品質検査を束ねる

## 運用上の注意 / ベストプラクティス

- DuckDB ファイルはバックアップを定期的に取りましょう。大規模なデータ保管には注意が必要です。
- J-Quants の API 仕様（レート/認証/提供データ）変更に注意し、例外ハンドリングを監視してください。
- ETL は idempotent（冪等）になるよう設計されていますが、外部からの手動操作や異常時はロールバック等を適切に行ってください。
- news_collector は外部 URL を扱うため、ログや保存データに個人情報や機密情報が含まれないよう運用ポリシーを整備してください。
- 運用環境では KABUSYS_ENV=live / paper_trading を適切に切り替え、ログレベルや通知を設定してください。

---

この README はコードベースから推定できる使い方と責務をまとめたものです。実運用やデプロイの際は実際の pyproject.toml / requirements / CI/CD 設定や、証券会社 API の実装、Slack 通知や監視設定をプロジェクトに合わせて実装してください。必要であれば README を拡張して CLI（例: 日次バッチ実行スクリプト）やデプロイ手順を追記します。