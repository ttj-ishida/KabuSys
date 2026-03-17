# KabuSys

KabuSys は日本株の自動売買を支えるデータ基盤と簡易 ETL / ニュース収集 / 監査ロギングを含むライブラリです。J-Quants API や RSS フィードを使ってデータを取得・整備し、DuckDB に冪等的に保存します。将来的な戦略実行や監視・監査のための枠組みを提供します。

主な設計方針:
- API レート制御とリトライ（指数バックオフ）を備えた堅牢なデータ取得
- DuckDB への冪等保存（ON CONFLICT/DO UPDATE / DO NOTHING）
- ニュース収集での SSRF / XML 攻撃対策、サイズ制限
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → execution のトレース）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - RSS ベースのニュース収集（ニュース記事の正規化・保存・銘柄抽出）
- データ保存
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
  - 冪等的な保存関数（raw_prices, raw_financials, market_calendar, raw_news など）
- ETL パイプライン
  - 差分取得（最終取得日からの差分／バックフィル）
  - 日次 ETL エントリポイント（品質チェック含む）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合を検出
- カレンダー管理
  - 営業日判定、前後営業日の取得、カレンダーの夜間更新ジョブ
- 監査ログ
  - signal_events / order_requests / executions を含む監査テーブルの初期化と管理
- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（自動読み込みを無効化可能）

---

## 要件（概略）

- Python 3.9+
- ライブラリ（例）:
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib 等を使用）
- （実行環境によって）J-Quants、kabuステーション、Slack 用の資格情報

依存はプロジェクトの pyproject.toml / requirements.txt を参照してください（本 README はコードベースから生成されています）。

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動します。
2. 仮想環境を作成して有効化します（任意）。
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
3. パッケージを開発モードでインストール:
   - pip install -e .
4. 必要な OS パッケージや Python パッケージをインストール（プロジェクト依存に応じて）。
5. 環境変数を設定します（下記参照）。プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（テスト時は自動ロードを無効化可能）。

注: 自動的に .env ファイルをロードする際、優先順位は OS 環境変数 > .env.local > .env です。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 設定（環境変数）

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

オプション／デフォルト:
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化

例: `.env`（簡易）
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

## 初期化（DuckDB スキーマ）

DuckDB スキーマを初期化するには Python から次のように実行します:

例:
```
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- init_schema(db_path) は必要なテーブルとインデックスをすべて作成します（冪等）。
- ":memory:" を渡すとインメモリ DB を使用します。
- audit 用スキーマは data.audit.init_audit_schema / init_audit_db を使って別途初期化できます。

監査スキーマの初期化例:
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.db")
```

---

## 使い方（よく使う API）

以下は主要なユースケースのサンプルです。

1) 日次 ETL を実行する
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB を初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース収集を実行する（RSS）
```
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# 既知の銘柄コードセット（抽出用）
known_codes = {"7203", "6758", "9984"}  # 例

results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

3) 市場カレンダー更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

4) 監査スキーマを既存接続に追加
```
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) J-Quants の個別 API 呼び出し（テスト用）
```
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 実装上のポイント（運用メモ）

- J-Quants クライアントは API レート（120 req/min）を守るため内部でスロットリングし、HTTP エラーやネットワーク障害に対してリトライ（最大 3 回）します。401 はトークン自動リフレッシュを試みます。
- ニュース収集は SSRF・XML BOM 等の攻撃対策を実装しています（スキーム検証、プライベートアドレス拒否、defusedxml、レスポンスサイズ制限など）。
- DuckDB への保存は基本的に ON CONFLICT を使い冪等化しています。
- ETL は差分取得（最終取得日の利用）とバックフィル（デフォルト 3 日）で API の後出し訂正を吸収する設計です。
- 品質チェックはエラー/警告を列挙し、呼び出し側がその重大度に応じて判断する仕組みです。

---

## ディレクトリ構成

（省略されているファイルを除く、主要なモジュール構成）

- src/kabusys/
  - __init__.py           (パッケージ定義、バージョン)
  - config.py             (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、保存ロジック)
    - news_collector.py   (RSS ニュース収集・前処理・保存)
    - schema.py           (DuckDB スキーマ定義・初期化)
    - pipeline.py         (ETL パイプライン / run_daily_etl 等)
    - calendar_management.py (カレンダー更新・営業日ロジック)
    - audit.py            (監査ログテーブル定義・初期化)
    - quality.py          (データ品質チェック)
  - strategy/
    - __init__.py         (戦略関連のエントリプレースホルダ)
  - execution/
    - __init__.py         (発注 / execution 層のエントリプレースホルダ)
  - monitoring/
    - __init__.py         (監視関連のエントリプレースホルダ)

---

## 開発・テストのヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を検知）から行われます。ユニットテスト等で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ネットワーク呼び出しを伴う箇所（_urlopen / J-Quants の HTTP 呼び出し）はモック可能な設計です。テストではこれらを差し替えて下さい。
- DuckDB のテストには ":memory:" を渡すとインメモリ DB が使えて便利です。

---

この README はコードベース（src/kabusys 以下）を参照して作成しています。実運用時は J-Quants の利用規約や証券会社 API の仕様に従い、十分なテストとリスク管理を行ってください。