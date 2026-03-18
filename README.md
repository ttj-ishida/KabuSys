# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ KabuSys のリポジトリ用 README。

この README はプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、およびディレクトリ構成を日本語でまとめたものです。

※ 本ドキュメントはコードベース（src/kabusys 以下）を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主な役割は以下の通りです。

- J-Quants API から市場データ（株価日足、財務データ、JPX カレンダー）を取得して DuckDB に蓄積する ETL パイプライン
- RSS フィードからニュースを収集・前処理し、記事と銘柄の紐付けを行うニュース収集モジュール
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- 市場カレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ用スキーマ）
- 環境設定および自動 .env 読み込み処理

設計上の特徴として、API のレート制御・リトライ・トークン自動更新、DuckDB への冪等保存（ON CONFLICT）や SSRF 対策、XML の安全なパース（defusedxml）などを備えています。

---

## 機能一覧

主な機能（モジュール別）：

- kabusys.config
  - .env または環境変数から設定を読み込み、Settings オブジェクトでアクセス可能
  - 自動 .env 読み込み：プロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を順に読み込む
  - 自動読み込み無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- kabusys.data.jquants_client
  - J-Quants API クライアント（ID トークン取得、ページネーション対応）
  - レートリミッタ、指数バックオフ、401 時のトークンリフレッシュ
  - データ取得: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - DuckDB への保存: save_daily_quotes、save_financial_statements、save_market_calendar（冪等）

- kabusys.data.news_collector
  - RSS 取得・前処理・記事ID生成（正規化 URL の SHA-256 を先頭32文字）
  - SSRF 対策（スキーム検証、プライベート IP 検査、リダイレクト検査）
  - XML を defusedxml で安全に解析、受信サイズ制限（10MB）、gzip 対応
  - DuckDB への保存（raw_news / news_symbols）をトランザクションで実行、挿入件数を正確に返す

- kabusys.data.schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) でテーブルとインデックスを冪等的に作成

- kabusys.data.pipeline
  - ETL パイプライン（差分更新、backfill、品質チェックの呼び出し）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェックの一連処理を実行し ETLResult を返す

- kabusys.data.calendar_management
  - 営業日判定・前後営業日探索・期間内営業日取得
  - calendar_update_job: 夜間バッチで JPX カレンダーを差分更新

- kabusys.data.audit
  - シグナル/発注/約定の監査ログテーブルを初期化する機能（init_audit_schema / init_audit_db）
  - UTC タイムゾーン固定などトレーサビリティ設計

- kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合等の品質チェック（QualityIssue を返す）
  - run_all_checks により一括実行可能

---

## 必要な環境変数

主に次の環境変数を使用します。必須項目には (必須) と記載しています。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token により ID トークンを取得します。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（execution 等で使用想定）。
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
  - Slack ボットトークン（通知等に使用）。
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID（通知先）。
- DUCKDB_PATH (任意)
  - DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 環境 (development / paper_trading / live)。デフォルトは development。
- LOG_LEVEL (任意)
  - ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト INFO。

例: .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動で .env を読み込むため、`.env.local` を用いてローカル上書きが可能です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境に設定してください。

---

## セットアップ手順

以下は一般的なセットアップ例です。プロジェクトに requirements ファイルがある場合はそれに従ってください。

1. Python 環境を用意（推奨: Python 3.9+）

2. 依存パッケージのインストール（最低限の主要依存）
```
pip install duckdb defusedxml
```
（必要に応じて他のパッケージを追加）

3. リポジトリをクローン／ソースを配置し、プロジェクトルートに `.env` を作成して環境変数を設定

4. DuckDB スキーマを初期化（例）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要ワークフローとサンプル）

ここでは代表的な操作例を示します。実運用でのエラーハンドリングやロギング設定は各自追加してください。

- スキーマ初期化（最初に一度実行）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants トークンは settings を通じて自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブを実行（既知の銘柄コードセットを渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

- 品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- J-Quants の個別取得 API を直接使う（テスト・カスタム処理向け）
```python
from kabusys.data import jquants_client as jq
# トークンを渡すことも、settings 経由で自動取得させることも可能
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 監査スキーマの初期化（オプション）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

---

## 注意点 / 設計上の留意事項

- J-Quants API はレート制限（120 req/min）があるため、jquants_client は内部で固定間隔スロットリングとリトライ処理を行います。大量取得時は実行時間に注意してください。
- DuckDB への保存は冪等を意識して設計されています（ON CONFLICT … DO UPDATE / DO NOTHING）。ETL は通常上書き可能です。
- RSS 取得では SSRF や XML Bomb 等に対する対策（スキーマ検査、ホストプライベート判定、受信サイズ上限、defusedxml）を実装していますが、外部 RSS ソース使用時は追加の監査を推奨します。
- 環境変数は `.env` / `.env.local` から自動的に読み込まれます（プロジェクトルートを探索）。テスト時などで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続はシングルプロセスの想定で使われることが多く、並列処理やマルチプロセスでの同時書き込みは別途検討が必要です。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース（src/kabusys）の主要ファイル一覧と簡単な役割です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定管理 (Settings)
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得、保存ロジック）
    - news_collector.py
      - RSS 収集・前処理・保存・銘柄抽出
    - schema.py
      - DuckDB のテーブル/インデックス定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、update_job）
    - audit.py
      - 監査ログ（signal/order/execution）用スキーマ初期化
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - strategy/
    - __init__.py
    - （戦略関連モジュールを配置する想定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携モジュールを配置する想定）
  - monitoring/
    - __init__.py
    - （監視・アラート関連モジュールを配置する想定）

---

## 追加情報 / 今後の拡張

- strategy / execution / monitoring サブパッケージは骨組みのみで、実際の戦略実装やブローカー API 連携、監視機能はここに追加していく設計です。
- J-Quants の追加エンドポイント、ニュースソースの追加、Slack 通知連携、発注フローの実装（kabuステーションや証券会社 API）は本リポジトリで拡張できます。

---

もし README に追加したい具体的な使い方（例: サンプルスクリプト、デプロイ手順、CI 設定、要件ファイル）や、インストール指示（pip install 方式・editable install）などがあれば教えてください。それに合わせて README を拡張します。