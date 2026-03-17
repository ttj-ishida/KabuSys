# KabuSys

KabuSys は日本株のデータ収集・品質管理・監査・ETL を行う自動売買プラットフォーム基盤ライブラリです。J-Quants API や RSS などからデータを取得して DuckDB に格納し、品質チェックや監査ログを備えたデータパイプラインを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価日足、財務情報、マーケットカレンダーを取得する
- RSS フィードからニュースを収集して前処理・銘柄紐付けする
- DuckDB に対して冪等的（ON CONFLICT）にデータを保存するスキーマとユーティリティを提供する
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）を実行する
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマを提供する
- マーケットカレンダーを基に営業日判定などを行うユーティリティを提供する

設計上の特徴：

- API レート制御（J-Quants: 120 req/min）
- リトライ（指数バックオフ、401 の場合はトークン自動リフレッシュ）
- Look-ahead bias を防ぐため取得時刻（UTC）を記録
- DuckDB への保存は冪等（ON CONFLICT）を基本とする
- RSS 収集では SSRF、XML Bomb、大容量レスポンス対策などの安全機構を備える

---

## 機能一覧

- 環境設定管理（`kabusys.config`）
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数の取得
- J-Quants クライアント（`kabusys.data.jquants_client`）
  - 株価日足、財務データ、マーケットカレンダー取得
  - トークン管理、レートリミット、リトライ
  - DuckDB への保存用ユーティリティ（冪等保存）
- RSS ニュース収集（`kabusys.data.news_collector`）
  - RSS 取得、前処理、記事ID生成、DuckDB への保存、銘柄抽出と紐付け
- DuckDB スキーマ管理（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- ETL パイプライン（`kabusys.data.pipeline`）
  - 差分取得、バックフィル、日次 ETL 実行、品質チェックの統合
- カレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定、next/prev trading day、夜間カレンダー更新ジョブ
- 監査ログ（`kabusys.data.audit`）
  - signal_events / order_requests / executions テーブル、監査向け初期化
- 品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク、重複、日付不整合チェック
- （将来）strategy / execution / monitoring 用のパッケージ雛形

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの `X | None` 記法を使用）
- DuckDB（Python パッケージ）、defusedxml などの依存が必要

例: 仮想環境作成とパッケージインストールの手順（必要なパッケージはプロジェクトごとに管理してください）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （実際のプロジェクトでは requirements.txt や pyproject.toml を用意して依存管理してください）

3. このパッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数
- 必須（アプリ起動時や一部関数呼び出しで使用）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルトあり:
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
- 自動 .env ロードを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の自動読み込み
- プロジェクトルートは __file__ の親階層から `.git` または `pyproject.toml` を探して決定します。
- 読み込み順: OS 環境変数 > .env.local > .env
- `.env` のパースはシェル風（export, quotes, コメントなど）に対応します。

---

## 使い方

以下は主要なユースケースの最小例です。適切な環境変数を設定した上で実行してください。

1) DuckDB スキーマ初期化

Python REPL やスクリプトで：

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
```

監査ログテーブル（別途）を初期化する場合：

```python
from kabusys.data import audit
# 既に init_schema() で conn を作成済みならその conn を渡す
audit.init_audit_schema(conn)
# あるいは監査専用 DB を作る場合
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

2) 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# DB 初期化済みの接続を取得
conn = schema.get_connection("data/kabusys.duckdb")

# ETL 実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)

# 結果を確認
print(result.to_dict())
```

3) RSS ニュース収集ジョブ（既存の known_codes を渡して銘柄紐付けを行う例）

```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")

# known_codes は valid な銘柄コードの集合
known_codes = {"7203", "6758", ...}

results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4) カレンダー更新ジョブ（夜間バッチなどで定期実行）

```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

5) J-Quants のデータ取得単体呼び出し（テスト・デバッグ用）

```python
from kabusys.data import jquants_client as jq
# 取得（id_token は省略可能: settings からリフレッシュトークンを使う）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点
- API 呼び出しはレート制限・リトライの対象となります。ライブラリの設計を尊重してください。
- DuckDB への接続は同一プロセス内で共有することを推奨します（多重接続や並列書き込みは別途考慮）。

---

## ディレクトリ構成

主要ファイルと役割（リポジトリのルートに `src/kabusys` 配下で提供される想定）:

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）
- src/kabusys/config.py
  - 環境変数の自動読み込みと Settings クラス
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、トークン、レートリミット、保存ユーティリティ
  - news_collector.py
    - RSS 取得・前処理・ID生成・DuckDB 保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義（Raw/Processed/Feature/Execution 層）、init_schema
  - pipeline.py
    - 差分 ETL（prices/financials/calendar）と日次 ETL の統合、品質チェック呼び出し
  - calendar_management.py
    - market_calendar に関するユーティリティ、営業日判定、更新ジョブ
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）定義と初期化
  - quality.py
    - データ品質チェック（欠損、スパイク、重複、日付不整合）
- src/kabusys/strategy/
  - 戦略関連モジュールのプレースホルダ
- src/kabusys/execution/
  - 発注・ブローカー連携関連のプレースホルダ
- src/kabusys/monitoring/
  - 監視用モジュールのプレースホルダ

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの判定は `.git` または `pyproject.toml` が存在するディレクトリを基準に行います。CI やテストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB にテーブルが作成されない
  - `schema.init_schema(db_path)` を呼んでテーブルを作成してください。初期化は冪等（何度実行しても安全）です。
- J-Quants API が 401 を返す
  - ライブラリはリフレッシュトークンから id_token を取得し自動リトライします。`JQUANTS_REFRESH_TOKEN` が正しいか確認してください。
- RSS 取得で外部への接続が遮断される
  - リダイレクト先のスキーム検査、プライベートアドレス検査、受信サイズ制限、gzip の検査など複数の防御を行っています。接続先が私的IPの場合は拒否されます。

---

## 今後の拡張案（参考）

- strategy / execution / monitoring モジュールの具体実装（発注ロジック、約定処理、監視ダッシュボード）
- Slack 通知や Prometheus メトリクスの統合（config の Slack 関連は準備済み）
- 並列 ETL 実行時のロック機構やジョブスケジューラ連携（Airflow / Prefect 等）

---

README に記載の動作例は最小限のものであり、実運用や本番環境では適切なエラーハンドリング、認証情報管理、監査設定を行ってください。必要であれば README を拡張して具体的なデプロイ手順や CI/CD、Docker 化の例も追加できます。要望があれば続けて作成します。