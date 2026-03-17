# KabuSys

日本株向けの自動売買/データ基盤ライブラリです。  
J-Quants からの市場データ取得、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、監査ログなどを備えています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのための基盤ライブラリです。  
主に以下を提供します。

- J-Quants API からの株価（日足）、財務データ、マーケットカレンダーの取得（レート制御・リトライ付き）
- DuckDB を用いた三層（Raw / Processed / Feature）データスキーマと初期化機能
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄コード紐付け
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ用スキーマ（シグナル → 発注 → 約定までのトレース）

設計上のポイント:
- API レート制限厳守（J-Quants: 120 req/min の固定間隔スロットリング）
- 冪等性（DuckDB 側で ON CONFLICT を用いた更新）
- トレーサビリティ（全ての監査テーブルにタイムスタンプ等）
- SSRF / XML Bomb 等への基本対策（news_collector）

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_* 系で DuckDB へ冪等保存
- data/schema.py
  - init_schema(db_path)、get_connection(db_path) によるスキーマ初期化・接続
- data/pipeline.py
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
- data/news_collector.py
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - 記事 ID は正規化 URL の SHA-256 先頭 32 文字
- data/quality.py
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
- data/calendar_management.py
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- data/audit.py
  - 監査用テーブル初期化（init_audit_schema / init_audit_db）

設定管理:
- config.py: .env 自動読み込み（.env → .env.local、OS 環境変数優先）と Settings クラス（環境変数名は下記参照）

パッケージ入口:
- kabusys.__init__ にてサブパッケージを公開

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の `X | Y` 型注記を使用しているため）
- Git, virtualenv 等

1. リポジトリをクローン／配置し、開発用仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt/pyproject があればそちらを利用してください。上は最低依存例です。標準ライブラリの urllib 等も使用しています。）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を配置できます。
   - 自動ロードはデフォルトで有効。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須となる主な環境変数（Settings クラスより）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

任意／デフォルト:
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python REPL やスクリプトからの基本的な操作例です。

1. DuckDB スキーマの初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2. 監査ログ用スキーマを追加
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
# 監査専用 DB を別ファイルで作る場合
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3. 日次 ETL を実行（J-Quants トークンは settings が参照）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

4. ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと銘柄抽出・紐付けを行う
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5. J-Quants API を直接叩く（テストや部分取得）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

token = jq.get_id_token()  # settings.jquants_refresh_token を用いて取得
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

ログレベルは環境変数 `LOG_LEVEL` で制御します。

---

## 自動環境変数読み込みの挙動

- 起点はこのパッケージのファイル位置からプロジェクトルート（親ディレクトリ）を探し、`.git` または `pyproject.toml` を目印にします。
- 読み込み順（優先度）:
  1. OS 環境変数（常に最優先）
  2. .env（既存の環境変数を上書きしない）
  3. .env.local（.env の上から上書き）
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env ファイルのパースは一般的なフォーマット（export の許容、クォート処理、コメント処理など）に対応します。

---

## ディレクトリ構成

以下は主要なファイル/モジュールの構成（src/kabusys 以下）です。実際のツリーはリポジトリルートに `src/` がある想定です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      # RSS ニュース取得・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - audit.py               # 監査ログ用スキーマ初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略関連（将来的な拡張）
  - execution/
    - __init__.py            # 発注/実行関連（将来的な拡張）
  - monitoring/
    - __init__.py            # 監視用モジュール（将来的な拡張）

---

## 注意事項・運用上のポイント

- Python バージョンは 3.10 以上を推奨します（型注記に `X | Y` を使用）。
- J-Quants の API レート制限（120 req/min）を守るため、jquants_client は内部でスロットリングを行います。外部からの連続的大量呼び出しは控えてください。
- news_collector は RSS の XML を安全にパースするため defusedxml を使用しています。SSRF 対策や受信サイズ上限チェックを行っていますが、外部フィード利用時は信頼できるソースに限定することを推奨します。
- DuckDB のスキーマは冪等に作成されます。既存データベースに対して init_schema を実行しても既存テーブルは壊れません。
- ETL は Fail-Fast ではなく、各ステップを独立して実行し、発生した問題を結果にまとめて返します。運用側で結果を評価してアラートやリトライを行ってください。

---

## 発展・拡張案

- execution モジュールを実装して kabu API との注文送信フローを組み込む
- strategy 層の具象実装、バックテスト機能の追加
- 監視（monitoring）で Prometheus や Slack 連携を追加
- ETL のスケジューリング（cron や Airflow 等）統合

---

この README はコードベース（src/kabusys 以下）から主要な仕様・使い方をまとめたものです。追加の実行スクリプトや CLI、外部依存のバージョン固定がある場合はプロジェクトの pyproject.toml / requirements.txt / docs を参照してください。