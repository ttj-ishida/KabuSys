# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（軽量プロトタイプ実装）。  
データ取得・ETL・データ品質チェック・ニュース収集・監査ログ用スキーマなど、トレーディングシステムの基盤機能を提供します。

主な設計方針：
- データの冪等保存（DuckDB 上で ON CONFLICT / DO UPDATE / DO NOTHING を利用）
- API レート制御・リトライ・トークン自動更新
- Look-ahead bias を避けるための fetched_at / UTC 保存
- RSS 収集での SSRF 対策・XML 安全パーシング
- 品質チェックを集約して ETL 後に実行（Fail-Fast ではなく全件収集）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得 API（Settings）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務諸表、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）、リトライ（指数バックオフ）、401 での自動トークン更新
  - DuckDB へ冪等保存用ユーティリティ（save_* 関数）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得 + 前処理（URL除去、空白正規化）
  - 記事ID = 正規化URL の SHA-256（先頭32文字）で冪等性確保
  - SSRF 対策、gzip サイズ上限、defusedxml による安全パース
  - raw_news / news_symbols への保存 API

- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でテーブルとインデックスを冪等に作成

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分/バックフィル）、保存、品質チェックの一括実行
  - run_daily_etl() による日次パイプライン
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日取得、期間内営業日列挙
  - calendar_update_job() による夜間差分更新

- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査用テーブル、インデックス、UTC タイムゾーン設定
  - init_audit_schema で監査テーブルを追加

- 品質チェック（kabusys.data.quality）
  - 欠損検出、スパイク（前日比）検出、重複チェック、日付整合性チェック
  - run_all_checks でまとめて実行し QualityIssue リストを返す

---

## 要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- defusedxml

（その他、標準ライブラリのみを多用しています。詳細は setup/pyproject によって変わります。）

---

## セットアップ手順

1. リポジトリをクローン（もしくはパッケージを入手）し、仮想環境を作成・有効化します。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストールします（例）。

   ```bash
   pip install duckdb defusedxml
   # または開発用にパッケージを編集可能インストール:
   pip install -e .
   ```

3. 環境変数を用意します。プロジェクトルートに `.env` と `.env.local`（任意）を置くことで自動読み込みされます。
   - 自動ロードは以下の優先度：
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる主な環境変数：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API パスワード
   - SLACK_BOT_TOKEN : Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID : 通知先チャンネル ID

   任意 / デフォルト：
   - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）

4. データ格納ディレクトリ（デフォルト data/）は自動作成されますが、必要に応じて作成してください。

---

## 使い方（主要 API の例）

以下は最小限の利用例です。実運用ではエラーハンドリングやロギング設定を行ってください。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルの親ディレクトリを自動作成
```

- 監査スキーマの初期化（既存 conn を拡張）

```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

- J-Quants の ID トークン取得（refresh token は settings から自動取得されます）

```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()
```

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult を辞書化して出力
```

- RSS ニュース収集と保存

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# sources を None にするとデフォルトの RSS ソースを使用
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count}
```

- カレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved_count = calendar_update_job(conn)
print("saved:", saved_count)
```

- 品質チェック（個別または一括）

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 重要な挙動・注意点

- .env ロード
  - パッケージ読み込み時に自動で .env/.env.local をプロジェクトルートから読み込みます（CWD に依存しない検出）。テストなどで自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数は上書きされません（保護）。`.env.local` は `.env` より優先して読み込まれます。

- J-Quants クライアント
  - レート制御（120 req/min）とリトライを実装しています。
  - 401 が返された場合はリフレッシュトークンから ID トークンを再取得して1回だけリトライします。
  - ページネーションに対応し、ページ間でのトークン共有のためのキャッシュを持ちます。

- RSS / ニュース収集
  - URL を正規化して記事 ID を生成し、トラッキングパラメータを除去します。
  - SSL リダイレクトやリダイレクト先のホストがプライベートアドレスの場合は接続をブロックします（SSRF 対策）。
  - レスポンスはサイズ上限（10MB）で保護されます。

- DuckDB スキーマ
  - init_schema は冪等。既存のテーブルやインデックスがあっても安全に実行できます。
  - 監査スキーマは init_audit_schema で追加します（UTC タイムゾーンを使用）。

- 環境（KABUSYS_ENV）
  - 許容値は "development", "paper_trading", "live" のいずれかです。これにより一部挙動や保護レベルを切り替えられる想定です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境設定読み込み（Settings）
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
      - news_collector.py             — RSS ニュース収集 / 保存
      - schema.py                     — DuckDB スキーマ定義・init_schema
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py        — 市場カレンダー更新・営業日判定
      - audit.py                      — 監査ログスキーマ（signal/order/execution）
      - quality.py                    — データ品質チェック
    - strategy/
      - __init__.py                    — 戦略層（拡張用）
    - execution/
      - __init__.py                    — 発注 / ブローカ接続（拡張用）
    - monitoring/
      - __init__.py                    — 監視（将来的な機能）

- data/                                — デフォルトの DB 保存先（例: data/kabusys.duckdb）

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージは拡張の起点です。戦略ロジック、ブローカ API 実装、モニタリングプラグインをここに実装してください。
- DuckDB スキーマは DataPlatform.md を想定した多層構造です。追加の列・インデックスが必要な場合は schema.py に追記し、init_schema を実行してください。
- テストを行う場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、環境変数注入を手動で行うと安全です。
- ETL のテストでは get_id_token や network 呼び出しをモックして id_token を注入すると簡単に分離テストできます（pipeline 関数は id_token を引数で受け取れるようになっています）。

---

もし README に追記したい内容（例: CLI スクリプト例、CI 設定、.env.example のテンプレート、実運用での注意点など）があれば教えてください。必要に応じてサンプル .env.example も作成します。