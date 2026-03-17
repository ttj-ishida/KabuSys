# KabuSys

日本株自動売買システム用の共通ライブラリ群 / ETL・データ基盤コンポーネント集

このリポジトリは、J-Quants API や RSS を用いた市場データの取得・前処理、DuckDB を用いた永続化、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなど、自動売買システムのデータ基盤とユーティリティを提供します。戦略層・実行層・監視層との連携を前提に設計されています。

主な設計方針のポイント
- API レート制限とリトライ（指数バックオフ）を組み込み、認証トークンの自動リフレッシュに対応
- DuckDB に対して冪等（idempotent）な保存（ON CONFLICT / DO UPDATE / DO NOTHING）を実装
- News収集では SSRF 防止、XML 攻撃対策、受信サイズ上限などセキュリティ・堅牢性を重視
- データ品質チェック（欠損・重複・スパイク・日付不整合）を提供
- 監査ログスキーマによりシグナル → 発注 → 約定までトレース可能

---

## 機能一覧

- 環境変数読み込み・設定管理（自動でプロジェクトルートの .env / .env.local をロード）
- J-Quants API クライアント（株価日足・財務データ・市場カレンダーの取得）
  - レートリミット制御（120 req/min）
  - リトライ、401 自動リフレッシュ、ページネーション対応
  - fetched_at による取得時刻トレースで Look-ahead Bias を低減
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、前後営業日取得、夜間更新ジョブ）
- ニュース収集（RSS → raw_news 保持、銘柄抽出・news_symbols 紐付け）
  - URL 正規化（トラッキングパラメータ除去）、記事ID は正規化 URL の SHA-256 の先頭 32 文字
  - SSRF / XML 脆弱性対策、レスポンスサイズ制限、チャンク INSERT
- データ品質チェック（missing / duplicates / spike / date consistency）
- 監査ログ用スキーマ（signal_events / order_requests / executions 等）

---

## 動作要件

- Python 3.10+
- 必要主要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等）
- 任意：kabuステーション API（実運用時の発注連携）

（開発時は pyproject.toml / requirements.txt に実際の依存がある想定で、それに従ってください）

---

## 環境変数（主なもの）

KabuSys は .env/.env.local または OS 環境変数から設定を読み込みます。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須（ライブラリ内で _require により検査される）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu API のパスワード（発注連携時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 開発環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

サンプル .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け・例）

1. Python 3.10+ を用意する
2. 仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate
3. 依存をインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
4. リポジトリルートに `.env`（または `.env.local`）を作成し、必要な環境変数を設定
5. DuckDB のスキーマ初期化（下記参照）

---

## スキーマ初期化（DuckDB）

Python REPL やスクリプトから DuckDB スキーマを初期化できます。

例: data/schema.init_schema を使う
```python
from pathlib import Path
import kabusys.data.schema as schema

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)
# 以降 conn を ETL 等で使用
```

監査ログ用スキーマを別 DB に作る場合:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/kabusys_audit.duckdb"))
```

---

## 使い方（主要ユースケース）

### 1) 日次 ETL 実行（株価・財務・カレンダー取得と品質チェック）
```python
from datetime import date
from pathlib import Path
from kabusys.data import schema, pipeline

conn = schema.init_schema(Path("data/kabusys.duckdb"))
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
- run_daily_etl は市場カレンダー取得 → 株価差分取得（バックフィル可）→ 財務差分取得 → 品質チェック を順に実行します。
- ETLResult に処理結果・品質問題・エラーが含まれます。

### 2) ニュース（RSS）収集ジョブ
```python
from pathlib import Path
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # source_name -> 新規挿入数
```
- fetch_rss は SSRF/サイズ/圧縮/XML に対する堅牢性を持っています。
- save_raw_news は INSERT ... RETURNING を使って実際に挿入された記事IDを返します。

### 3) J-Quants からの個別データ取得
```python
from kabusys.data import jquants_client as jq
# id_token を明示的に渡すことも、モジュールのキャッシュと自動リフレッシュを利用することも可能
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
```

### 4) マーケットカレンダーのユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_open = is_trading_day(conn, date(2024,3,20))
next_day = next_trading_day(conn, date(2024,3,20))
```

---

## 開発メモ / 注意点

- Python バージョン: 本コードは 3.10 の構文 (X | None 型) を使用しているため 3.10 以上が必須です。
- 自動環境変数ロード: パッケージ import 時にプロジェクトルート（.git または pyproject.toml の存在）から .env/.env.local を自動ロードします。テスト時などで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants のレート制限（120 req/min）に合わせた RateLimiter とリトライロジックを実装済みです。
- DuckDB の接続はスレッドセーフ性や複数プロセスでの同時書き込みに注意が必要です（運用設計で適宜調整してください）。
- ETL は「Fail-Fast ではなく全件収集」に設計されており、個別ステップの失敗は結果に記録されつつ他ステップは継続します。

---

## ディレクトリ構成

以下は主要なディレクトリ / ファイルの説明（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
    - news_collector.py
      - RSS 取得・パース・前処理・DuckDB 保存・銘柄抽出
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py
      - 市場カレンダーの管理・営業日判定・夜間更新ジョブ
    - audit.py
      - 監査ログ用スキーマ（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
    - （戦略関連モジュールを配置する想定）
  - execution/
    - __init__.py
    - （注文送信・ブローカー連携ロジックを配置する想定）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連を配置する想定）

---

## ライセンス / コントリビュート

（ここにプロジェクトのライセンスや貢献方法を記載してください。リポジトリに LICENSE があればその内容に従ってください。）

---

README は以上です。必要であれば、README に含めるサンプルスクリプト、CI 設定、デプロイ手順（スケジューラ / cron / Airflow 連携例）やより具体的な env.example のテンプレートを追加作成します。どの情報を詳しく追記しますか？