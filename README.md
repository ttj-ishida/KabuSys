# KabuSys

日本株向け自動売買基盤のコンポーネント群です。データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ等を提供します。

この README ではプロジェクト概要、主な機能、セットアップ手順、簡単な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された共通ライブラリ群です。主に次を扱います。

- J-Quants API からの株価（OHLCV）・財務データ・マーケットカレンダーの取得（レートリミット・リトライ・トークン自動更新対応）
- RSS からのニュース収集と前処理、銘柄コード抽出、DuckDB への冪等保存
- DuckDB スキーマ定義 / 初期化（Raw / Processed / Feature / Execution レイヤ）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴として、Look-ahead bias 回避のため取得時刻を記録、冪等操作（ON CONFLICT 処理）、SSRF 対策や XML パースの安全化（defusedxml）などが組み込まれています。

---

## 機能一覧

- config
  - 環境変数読み込み（`.env` / `.env.local` の自動ロード、オーバーライド仕様）
  - 必須設定の取得（Settings クラス）

- data
  - jquants_client
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存関数（save_daily_quotes 等）
    - レートリミット、リトライ、トークン自動リフレッシュ
  - news_collector
    - RSS フィード取得（gzip / リダイレクト / SSRF 対策）
    - 記事の前処理、ID 生成（正規化 URL の SHA-256）、DuckDB への保存、銘柄抽出
  - schema
    - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
    - init_schema / get_connection
  - pipeline
    - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
    - 日次 ETL エントリ（run_daily_etl）と ETL 結果オブジェクト（ETLResult）
  - calendar_management
    - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job
  - audit
    - 監査用テーブル定義 / 初期化（init_audit_schema, init_audit_db）
  - quality
    - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

- strategy / execution / monitoring
  - パッケージ用プレースホルダ（戦略・発注・監視ロジックを実装するための名前空間）

---

## セットアップ手順

以下は開発 / 実行環境の最低限の手順例です。実際はプロジェクトの packaging / CI 設定に合わせてください。

前提
- Python 3.9+（コードは型ヒントで modern な構文を使用しています）
- DuckDB を利用します（Python パッケージ duckdb）
- defusedxml（安全な XML パーサ）

例: 仮想環境の作成と必要パッケージのインストール

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb defusedxml
# 必要に応じてその他パッケージを追加
```

環境変数 / .env
- プロジェクトルートに `.env` と `.env.local` を置くと、自動的に読み込まれます。
- 読み込み順は: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

必須環境変数（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

その他（省略時はデフォルトが使用されます）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動ロードを無効化
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

サンプル .env（.env.example に相当する内容の例）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

データベース初期化（DuckDB）
- スキーマを作成するには Python で次を実行します:

```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db
init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（簡単な例）

以下は主要なモジュールの簡単な利用例です。実行前に必ず環境変数を設定・DB 初期化してください。

1) 設定の取得

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
```

2) J-Quants トークン取得 / データ取得

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

id_token = get_id_token()  # settings.jquants_refresh_token を使う
quotes = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
```

3) DuckDB にスキーマを作成して ETL を実行（日次 ETL）

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL 実行
print(result.to_dict())
```

4) RSS ニュース収集と保存

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) マーケットカレンダーの判定ヘルパー

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = get_connection("data/kabusys.duckdb")
d = date(2026, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) 品質チェック

```python
from kabusys.data.quality import run_all_checks
res = run_all_checks(conn, target_date=None)
for issue in res:
    print(issue.check_name, issue.severity, issue.detail)
```

注意点
- jquants_client は内部で 120 req/min のレート制限を守る実装です。多数の同時プロセスからの呼び出しは注意してください。
- fetch_* 関数はページネーションを考慮しています。get_id_token は自動でリフレッシュする場合があります。
- news_collector は SSRF 対策、gzip サイズチェック、defusedxml を利用した安全な XML 解析を行います。

---

## ディレクトリ構成

（主要なファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                          -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py                -- J-Quants API クライアント + 保存処理
      - news_collector.py                -- RSS ニュース収集と保存
      - schema.py                        -- DuckDB スキーマ定義 / init_schema
      - pipeline.py                      -- ETL パイプライン（差分更新、日次 ETL）
      - calendar_management.py           -- マーケットカレンダー管理
      - audit.py                         -- 監査ログ（トレーサビリティ）定義 / 初期化
      - quality.py                       -- データ品質チェック
    - strategy/
      - __init__.py                       -- 戦略ロジック用名前空間（実装は各自）
    - execution/
      - __init__.py                       -- 発注 / 実行ロジック用名前空間（実装は各自）
    - monitoring/
      - __init__.py                       -- 監視系（実装は各自）

---

## その他メモ / 実運用時の注意

- 環境設定: 本番運用時は KABUSYS_ENV を `live` に設定し、ログレベル等を適切に調整してください。
- 機密情報管理: トークンやパスワードは `.env` に直書きするよりセキュアなシークレット管理を推奨します。
- データベース: DuckDB はシングルファイル DB で利便性が高いですが、複数プロセスが同時に重い書き込みを行う場合は運用設計（ロック戦略や専用 DB）を検討してください。
- テスト: 自動ロードを無効にするために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。jquants_client などは id_token を外部注入できるためユニットテストが容易です。
- ロギング: 各モジュールは logger を使用しています。アプリ側でハンドラとレベルを設定してお使いください。

---

この README はコードベースの概要と主な使い方をまとめたものです。各モジュールの詳細な API や拡張点については該当するソース内の docstring を参照してください。必要であれば README に導入手順のスクリプト例や CI/CD、Docker 化の説明を追加できます。