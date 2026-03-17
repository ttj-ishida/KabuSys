# KabuSys

日本株の自動売買プラットフォーム向けライブラリ（ミニマル実装）。データ収集、ETL、品質チェック、監査ログ、ニュース収集など、戦略や実行モジュールが利用する基盤機能を提供します。

主な特徴
- J-Quants API からの株価・財務・マーケットカレンダー取得（ページネーション対応、レート制御、リトライ・自動リフレッシュ）
- DuckDB を用いた3層データレイヤ（Raw / Processed / Feature）と実行・監査テーブルのスキーマ定義・初期化
- 日次 ETL パイプライン（差分更新 / バックフィル / 品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策、XML攻撃対策、GZip/Bomb対策）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数・設定管理（.env 自動読み込み、プロジェクトルート検出）

---

## 機能一覧

- 環境設定
  - .env/.env.local 自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - Settings オブジェクト（J-Quants トークン、kabu API パスワード、Slack トークン、DB パス、実行環境など）

- データ取得（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - 特徴:
    - レート制限（120 req/min 固定間隔スロットリング）
    - リトライ（指数バックオフ、408/429/5xx 対応）
    - 401 時に自動トークンリフレッシュ（1 回のみ）

- ニュース収集（kabusys.data.news_collector）
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)
  - 特徴:
    - URL 正規化（トラッキングパラメータ削除）
    - 記事ID は正規化 URL の SHA-256（先頭32文字）
    - SSRF 防止（スキームチェック・プライベートIP判定・リダイレクト検査）
    - defusedxml を利用した XML 攻撃対策
    - レスポンスサイズ制限（既定 10 MB）、gzip 解凍後も検査

- スキーマ / DB 初期化（kabusys.data.schema）
  - init_schema(db_path) — DuckDB に全テーブル（Raw / Processed / Feature / Execution）を作成
  - get_connection(db_path)

- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...)
  - 差分更新、バックフィル、品質チェックとの統合

- 品質チェック（kabusys.data.quality）
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)
  - run_all_checks(...)

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - シグナル / 発注要求 / 約定ログのための監査テーブルとインデックス

---

## セットアップ手順（開発環境）

前提
- Python 3.9+（typing の一部機能が使われています）
- DuckDB を利用します

1. リポジトリをクローンし、プロジェクトルートに移動

2. 依存パッケージをインストール
   - 必須（最小）:
     - duckdb
     - defusedxml
   - 例（pip）:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用に pyproject/requirements があればそちらを使ってください（本リポジトリには含まれていません）。

3. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local`）を作成すると自動的に読み込まれます（自動ロードは Settings モジュールで行われます）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（コード例）

以下はライブラリの主要な利用例です。実行は Python スクリプトや REPL から行えます。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# デフォルト path は settings.duckdb_path を参照しても良い
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- J-Quants から個別に取得して保存する
```python
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

conn = init_schema("data/kabusys.duckdb")

# トークン自動取得
id_token = jq.get_id_token()

# 銘柄コード 7203 の日足を取得して保存
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

- ニュース収集と銘柄紐付け
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")

# known_codes に有効な銘柄コードセットを渡すと、記事中の4桁コードを紐付ける
known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- 品質チェックの手動実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.quality import run_all_checks

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 環境設定項目（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須) — Slack 通知連携用
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

settings オブジェクトは kabusys.config.settings 経由でアクセス可能です。

---

## セキュリティ設計上のポイント

- J-Quants クライアントはレート制御（120 req/min）とリトライを実装。401 時のトークン自動リフレッシュを行います。
- ニュース収集では SSRF 対策（スキーム検査・プライベートIPブロック・リダイレクト検査）と XML 攻撃・Gzip Bomb 対策を実施。
- DuckDB への書き込みは冪等性を重視（ON CONFLICT … DO UPDATE / DO NOTHING を利用）。
- 監査テーブル設計はトレーサビリティ（UUID連鎖）と削除非可逆性を念頭に置いています。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 + DuckDB 保存ロジック）
    - news_collector.py            — RSS ニュース収集・正規化・保存
    - pipeline.py                  — ETL パイプライン（差分更新 / 品質チェック統合）
    - schema.py                    — DuckDB スキーマ定義・初期化
    - audit.py                     — 監査ログ（signal/order/execution）DDL と初期化
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略モジュールプレースホルダ（拡張対象）
  - execution/
    - __init__.py                  — 発注/ブローカー連携プレースホルダ（拡張対象）
  - monitoring/
    - __init__.py                  — 監視/メトリクスプレースホルダ

---

## 留意点 / 開発メモ

- 現在の実装はライブラリ層が中心で、CLI や常駐プロセス、実際のブローカー接続（kabu API 呼び出しの詳細）や戦略アルゴリズムは別途実装が必要です。
- DuckDB の型挙動や SQL 文法はバージョン差に注意してください（インデックスや制約が DB によって挙動差があるため開発時に確認を推奨します）。
- 大量データ投入時はチャンクサイズやトランザクション設計に気をつけてパフォーマンス調整を行ってください（news_collector はチャンク INSERT を使用）。
- テストでは settings の自動 .env ロードを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると便利です。

---

問題報告 / 追加要望があれば、どの機能を拡張したいか（例: ブローカー接続ラッパー、戦略テンプレート、Slack通知のワークフロー）を教えてください。README の補足やサンプルスクリプトも用意できます。