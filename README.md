# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や kabu API からのデータ取得、DuckDB によるデータ保管、ETL パイプライン、ニュース収集、データ品質チェック、監査ログなどを提供します。

## プロジェクト概要
KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを安全に取得するクライアント
- DuckDB ベースのデータスキーマと初期化ユーティリティ
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF / XML 攻撃対策、トラッキングパラメータ除去、冪等保存）
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ

設計上の主な考慮点：
- API レート制限・リトライ（指数バックオフ、401 の自動トークンリフレッシュ等）
- DuckDB へ冪等に保存（ON CONFLICT / INSERT ... RETURNING 等）
- データ品質チェックにより欠損・スパイク・重複・日付不整合を検出
- 安全性（SSRF 対策、defusedxml、取得サイズ制限等）

## 機能一覧
主な機能：
- jquants_client
  - 株価日足 / 財務データ / マーケットカレンダーの取得（ページネーション対応）
  - トークン自動リフレッシュ、レートリミット、リトライ実装
  - DuckDB へ冪等保存（save_* 関数）
- data.schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化
- data.pipeline
  - run_daily_etl(...) による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィルロジック
- data.news_collector
  - RSS フィードの取得・前処理・記事の冪等保存
  - URL 正規化（トラッキングパラメータ除去）、記事ID = SHA-256 の先頭 32 文字
  - SSRF / gzip サイズ制限 / XML セキュリティ対応
- data.calendar_management
  - 営業日判定、前後営業日取得、期間内営業日一覧取得、夜間カレンダー更新ジョブ
- data.quality
  - 欠損 / スパイク / 重複 / 日付不整合チェック
  - QualityIssue オブジェクトで詳細を返す
- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）と初期化ユーティリティ

## セットアップ手順

前提
- Python 3.9+（型アノテーションや一部 API を想定）
- DuckDB, defusedxml 等の依存パッケージ

1. リポジトリをクローン
   - git clone ... （レポジトリ URL）

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布用に pyproject.toml / requirements.txt があればそれに従ってください）
   - 開発インストール（リポジトリルートで）:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートの .env または環境変数から読み込みます。自動読み込みは、パッケージ内で .git または pyproject.toml を探して行われます（CWD に依存しません）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（アプリケーション実行に必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabu API 用パスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

任意 / デフォルト値あり
- KABUSYS_ENV            : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動.envロードを抑制するフラグ（1 で無効）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## 使い方

以下は主要な操作の例です。Python REPL やスクリプトで実行してください。

1. DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema
# ファイル DB を作成して全テーブルを作成
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

2. 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 省略で本日を対象に実行
print(result.to_dict())
```

run_daily_etl は次の処理を安全に実行します：
- 市場カレンダーの先読み更新
- 株価日足の差分取得（バックフィル対応）
- 財務データの差分取得
- 品質チェック（デフォルトで有効）

3. ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄抽出に用いる有効な銘柄コード集合（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存件数, ...}
```

fetch_rss / save_raw_news / save_news_symbols を個別に利用してカスタム処理することも可能です。

4. カレンダー更新ジョブ（夜間バッチ等）
```python
from kabusys.data.calendar_management import calendar_update_job
conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

5. 監査スキーマの初期化（監査専用 DB または既存接続へ追加）
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
# 監査専用 DB を作る
audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn に追加する場合
# init_audit_schema(conn, transactional=True)
```

6. データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点（実装に基づく重要ポイント）
- J-Quants のレート制限（120 req/min）はクライアント側で制御されます。
- API エラー（408/429/5xx）はリトライ（指数バックオフ）され、401 は自動リフレッシュして 1 回リトライします。
- news_collector は SSRF 対策、gzip サイズチェック、XML の安全パーサを利用しています。
- ETL や保存処理は可能な限り冪等に設計されています（ON CONFLICT/INSERT ... RETURNING 等）。

## ディレクトリ構成
リポジトリ内の主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ベースのニュース収集・保存ロジック
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー運用ヘルパー
    - audit.py               — 監査ログスキーマ初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

データベース関連ファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db

## 開発・運用メモ
- 自動で .env ファイルをロードします（プロジェクトルートを .git または pyproject.toml で判定）。テストや一時的にロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB によるトランザクション管理は、重いバルク INSERT をトランザクションでまとめることで整合性とパフォーマンスを確保しています。
- 監査スキーマを追加する際は init_audit_schema の transactional 引数に注意（既にトランザクション中に呼ぶとネスト不可のため振る舞いに注意）。

---

この README はコードベースからの抜粋に基づく概要です。実運用前に `.env.example`（存在する場合）を参照し、J-Quants と kabu API の認証情報、Slack トークン、DB パス等を正しく設定してください。必要であれば README を拡張して CI / デプロイ手順、運用監視フロー、スケジュール設定（cron / Airflow 等）の例を追加できます。