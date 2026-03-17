# KabuSys

KabuSys は日本株向けの自動売買/データ基盤ライブラリです。J-Quants や RSS フィードから市場データ・財務データ・ニュースを収集し、DuckDB に保存・品質チェックを行い、戦略・発注層へデータを提供することを目的としています。

主な設計方針としては以下を重視しています。
- データ取得の冪等性（ON CONFLICT / トランザクション）
- API レート制御と堅牢なリトライ（トークン自動リフレッシュ含む）
- セキュリティ対策（RSS の SSRF/XML 攻撃対策、受信サイズ制限）
- データ品質チェックと監査トレース（監査テーブル / UUID連鎖）

---

## 機能一覧

- 環境変数管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須設定チェックを提供（settings オブジェクト経由）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務（四半期 BS/PL）、JPX カレンダーを取得
  - レートリミット（120 req/min）対応、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への保存関数（冪等）
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理（URL 除去・空白正規化）
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - SSRF 回避（スキーム・プライベート IP の検査）、XML 攻撃対策（defusedxml）、受信サイズ制限
  - 銘柄コード抽出・news_symbols による紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、init_schema / get_connection API
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分算出）、バックフィル、品質チェックの統合実行
  - run_daily_etl によりカレンダー→株価→財務→品質チェックを順次実行
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 (is_trading_day 等)、next/prev_trading_day、夜間更新ジョブ
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトのリストで結果を返す
- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定の追跡のための監査スキーマと初期化 API

---

## 前提・依存関係

- Python 3.9+
- 主要外部ライブラリ:
  - duckdb
  - defusedxml

インストール例（仮のセットアップ）:
```bash
# 開発インストール（pyproject.toml などがある場合）
pip install -e .

# もしくは最低限の依存だけをインストール
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

kabusys は設定を環境変数経由で読み込みます。プロジェクトルート（.git または pyproject.toml のある階層）から `.env` / `.env.local` を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

重要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)

コードからは次のようにアクセスします:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

未設定の必須値にアクセスすると ValueError が発生します。

---

## セットアップ手順（最小）

1. リポジトリをクローン / ソースを配置
2. Python 環境を作成（venv など）して依存をインストール
3. プロジェクトルートに `.env` を作成し、必要な環境変数を設定
   - 例: `.env` に JQUANTS_REFRESH_TOKEN=... を記載
4. DuckDB スキーマを初期化

例:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

監査ログ用 DB を別途作成する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な例）

- 日次 ETL を実行して DuckDB にデータを収集・保存する:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュース（RSS）収集ジョブを実行する:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードのセット（抽出精度向上のため）
known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- カレンダー夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar に保存された件数: {saved}")
```

- 品質チェックを個別に実行:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

- J-Quants クライアントを直接使う（トークンは settings から自動取得・リフレッシュ）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- run_daily_etl や個々の ETL 関数はエラーを内包して継続実行する設計です。戻り値（ETLResult）にエラーや品質問題が格納されます。呼び出し側でログ出力やアラート（Slack など）を行ってください。

---

## 主要 API 概要

- kabusys.config.settings — 環境設定オブジェクト（プロパティアクセス）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client.get_id_token(refresh_token=None) — ID トークン取得
- kabusys.data.jquants_client.fetch_* / save_* — データ取得 & 保存ユーティリティ
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline.run_daily_etl — 日次 ETL の統合実行
- kabusys.data.calendar_management.{is_trading_day,next_trading_day,...}
- kabusys.data.quality.run_all_checks — 品質チェックの一括実行
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査テーブル初期化

---

## ディレクトリ構成

リポジトリの主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - news_collector.py          — RSS ニュース収集・保存・銘柄抽出
    - schema.py                  — DuckDB スキーマ定義・初期化
    - pipeline.py                — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py     — 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                   — 監査ログスキーマと初期化
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略層（今後の実装エントリ）
  - execution/
    - __init__.py                — 発注/実行層（今後の実装エントリ）
  - monitoring/
    - __init__.py                — モニタリング関連（今後の実装エントリ）

---

## 開発・拡張のヒント

- テストで環境変数の自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてからテストを実行
- DuckDB の in-memory を使いたい場合は db_path に ":memory:" を渡せます（init_schema(":memory:")）
- RSS の取得は外部ネットワークに依存するため、ユニットテストでは kabusys.data.news_collector._urlopen をモックしてください
- J-Quants のページネーションやトークン処理はモジュールレベルでキャッシュされています。テストで強制リフレッシュが必要な場合は get_id_token(force_refresh) を呼び出すか、_get_cached_token の挙動を制御してください

---

必要であれば README に例となる .env.example、requirements.txt、簡単な CLI ラッパー（ETL を定期実行する cron / systemd ユニット例）なども追記できます。どのような追加ドキュメントが欲しいか教えてください。