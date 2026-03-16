# KabuSys

日本株向け自動売買システムのコアライブラリ（データ収集・ETL・スキーマ・監査ログ・品質チェック等）

このリポジトリは、J-Quants API を用いた市場データの取得、DuckDB を用いたデータ格納とスキーマ管理、日次 ETL パイプライン、品質チェック、および監査ログ用スキーマを提供します。実際の発注・ストラテジー実行部分はモジュール分割されており、将来的な拡張を想定しています。

主な設計方針
- Look-ahead bias を防ぐためにデータ取得時刻（fetched_at）は UTC で記録
- J-Quants API のレート制限（120 req/min）を厳守
- リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ対応
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast とせず、検出結果を集約して呼び出し元が判断できるようにする

---

## 機能一覧
- J-Quants API クライアント（株価日足、四半期財務、マーケットカレンダー取得）
  - レート制限制御、リトライ、トークン自動リフレッシュ実装
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- ETL パイプライン（差分取得、バックフィル、保存、品質チェック）
- データ品質チェックモジュール（欠損、スパイク、重複、日付不整合）
- 環境変数管理（.env / .env.local の自動ロード、プロジェクトルート検出）

---

## 要件
- Python 3.10 以上（型注釈に Python 3.10 の `X | None` 記法を使用）
- duckdb（DuckDB Python パッケージ）
- ネットワーク接続（J-Quants API へのアクセス）
- （任意）.env ファイル管理用にテキストエディタ

必要ライブラリの最小例:
- duckdb

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# その他の依存がある場合は requirements.txt を用意して pip install -r requirements.txt
```

---

## 環境変数（.env）
このパッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して以下の順で .env を自動ロードします:
1. OS 環境変数（既存の環境変数は保護される）
2. .env （既存の環境変数を上書きしない）
3. .env.local （上書きを許可）

自動ロードを無効にする場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）

主な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

例（.env）
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

## セットアップ手順（概要）
1. Python 仮想環境を作成・有効化
2. duckdb 等の依存をインストール
3. .env をルートに配置して必要な環境変数を設定
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

監査ログスキーマ（audit）を既存の接続に追加:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

または監査専用 DB を作成:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（簡単なワークフロー例）
基本的な日次 ETL を実行する手順例:

1. スキーマ初期化（初回のみ）
2. 日次 ETL の実行

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# 1) DB とスキーマ初期化
conn = init_schema("data/kabusys.duckdb")

# 2) 日次 ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn)

# 結果を確認
print(result.to_dict())
```

J-Quants の ID トークンを手動取得して ETL に渡す例:
```python
from kabusys.data.jquants_client import get_id_token
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
id_token = get_id_token()  # settings.jquants_refresh_token を使用
result = run_daily_etl(conn, id_token=id_token)
```

品質チェックのみ実行する:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意点
- J-Quants API 利用にはリフレッシュトークンが必須です（環境変数 JQUANTS_REFRESH_TOKEN）。
- API のレート制限（120 req/min）を超えないよう内部で制御していますが、大量のページネーションが発生する場合は時間がかかります。
- run_daily_etl は各処理（calendar, prices, financials, quality）を個別に例外処理し、可能な限り継続して他の処理を実行します。結果は ETLResult に集約されます。

---

## 開発 / テスト向けヒント
- 自動で .env を読み込みたくないときは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてからテストを実行してください。
- テスト時に外部 API を叩きたくない場合は、jquants_client.get_id_token や fetch_* 関数をモックしてください。
- DuckDB のインメモリ(":memory:") を使えば簡易な単体テストが高速に実行できます。

---

## ディレクトリ構成
リポジトリ内の主要モジュールとファイル（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制限、リトライ）
    - schema.py
      - DuckDB の DDL 定義・init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログスキーマ（signal_events, order_requests, executions）
    - audit.py / schema.py に定義されたインデックスや制約でトレーサビリティを保証
  - strategy/
    - __init__.py（戦略用プレースホルダ）
  - execution/
    - __init__.py（発注・約定管理プレースホルダ）
  - monitoring/
    - __init__.py（監視用プレースホルダ）

---

## 実装上の重要ポイント（短く）
- J-Quants クライアントは 120 req/min（_MIN_INTERVAL_SEC = 60/120）でスロットリング
- リトライは最大 3 回（指数バックオフ）、401 はトークンリフレッシュを試みて再リクエスト
- DuckDB の各 INSERT は ON CONFLICT DO UPDATE で冪等化
- 品質チェックは複数のチェックをまとめて返し、致命的エラーかどうかは呼び出し側で判断

---

## 貢献・問い合わせ
このドキュメントやコードに関するフィードバックは Issue を通じてお願いします。PR は既存の設計方針（冪等性・トレーサビリティ・UTC タイムスタンプ）を崩さない範囲で歓迎します。

---

以上。必要であれば、README に追加で「例: crontab による日次実行」「Slack 通知の設定例」「より詳細な .env.example」などの追記を行います。どの情報を補足しますか?