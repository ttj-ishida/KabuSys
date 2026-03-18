# KabuSys

日本株自動売買システム用のコアライブラリ (KabuSys)。  
J-Quants / kabuステーション 等の外部データソースからデータを取得・保存し、ETL・品質チェック・カレンダー管理・ニュース収集・監査ログなどの基盤機能を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コード例）
- 環境変数
- ディレクトリ構成
- 補足（設計上の注意点）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤・ETL・監査基盤を提供する Python パッケージです。主な役割は以下です。

- J-Quants API から株価（OHLCV）、財務、JPX カレンダーを安全に取得するクライアント。
- DuckDB を用いたスキーマ定義・初期化。
- 日次 ETL パイプライン（差分取得、バックフィル、保存、品質チェック）。
- RSS ベースのニュース収集・前処理・銘柄紐付け。
- 市場カレンダー管理（営業日判定、next/prev/trading days）。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を保持するテーブル定義と初期化。
- 各種品質チェック（欠損・スパイク・重複・日付不整合）。

設計面のポイント:
- API レート制限（例: J-Quants 120 req/min）を守る RateLimiter を実装
- リトライ（指数バックオフ）、401 の自動トークンリフレッシュ対応
- DuckDB への保存は冪等的（ON CONFLICT / DO UPDATE / DO NOTHING）
- RSS 収集では SSRF、XML Bomb、メモリ DoS 対策を実施

---

## 機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
  - レート制御・リトライ・トークン自動更新・fetched_at 記録

- data.schema
  - DuckDB のスキーマ定義と init_schema / get_connection

- data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（ETL の統合）
  - 差分更新、backfill、品質チェック統合

- data.news_collector
  - fetch_rss（RSS 取得と前処理）、save_raw_news、save_news_symbols、run_news_collection
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA256）で冪等

- data.calendar_management
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでのカレンダー更新）

- data.audit
  - 監査ログ用テーブル定義・初期化（init_audit_schema / init_audit_db）
  - order_request の冪等制御・UTC タイムゾーン固定

- data.quality
  - 欠損チェック、スパイク検出、重複検査、日付整合性検査
  - run_all_checks で一括実行

- config
  - .env 自動読み込み（プロジェクトルートにある .env / .env.local）、環境変数管理（Settings クラス）
  - 必須環境変数チェック（_require）

---

## セットアップ手順

1. Python と仮想環境を準備
   - Python 3.10+ を推奨（コードは typing の union 型 | を使用）
   - 仮想環境を作成して有効化

2. 依存パッケージをインストール
   - 本リポジトリに依存記載がある前提で、通常は以下のようにインストールします（例）:
     - pip install -r requirements.txt
     - もしくは pip install duckdb defusedxml
   - 主要依存:
     - duckdb
     - defusedxml

3. リポジトリをプロジェクトルートにクローン（.git または pyproject.toml がプロジェクトルート特定に使われます）

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと、config モジュールが自動で読み込みます。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DB スキーマ初期化
   - DuckDB を使ってスキーマを初期化します（例は次節の使い方参照）。

---

## 環境変数

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

.env のパースはシェル風の export 記法、クォート、インラインコメント等に対応しています。

---

## 使い方（コード例）

以下は基本的な操作例です。Python スクリプト内で直接呼び出せます。

- DuckDB スキーマ初期化:

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイルパスは settings.duckdb_path で取得可能
conn = init_schema(settings.duckdb_path)
# あるいはメモリ DB:
# conn = init_schema(":memory:")
```

- 日次 ETL を実行（J-Quants トークンは Settings から自動取得されます）:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- RSS ニュース収集（既知銘柄セットを与えて銘柄紐付けを行う例）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

# 既知銘柄セット (例)
known_codes = {"7203", "6758", "9984"}

conn = get_connection(settings.duckdb_path)
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- 監査ログ用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/kabusys_audit.duckdb"))
```

- 品質チェックの実行:

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## ディレクトリ構成

リポジトリは src 配下にパッケージとして配置されています。主要ファイルは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py           — RSS ニュース収集・保存
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分更新・統合）
    - calendar_management.py      — カレンダー管理（営業日判定等）
    - audit.py                    — 監査ログテーブル定義・初期化
    - quality.py                  — データ品質チェック
  - strategy/                      — 戦略関連（拡張ポイント）
  - execution/                     — 発注関連（拡張ポイント）
  - monitoring/                    — 監視・メトリクス（拡張ポイント）

---

## 補足（設計上の注意点）

- .env 自動ロード:
  - config._find_project_root は .git または pyproject.toml を基準にプロジェクトルートを特定します。CWD に依存しないため、パッケージ配布後も正しく動作します。
  - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

- J-Quants クライアント:
  - 内部で固定間隔のレートリミッタを利用しており、120 req/min の制約を守る設計です。
  - リトライは指数バックオフ（最大 3 回）、408/429/5xx が対象。401 は自動で一度だけ id_token をリフレッシュして再試行します。
  - データ取得時には fetched_at を UTC で保存し、Look-ahead bias の追跡が可能です。

- ニュース収集:
  - defusedxml を使った XML パースで XML Bomb を防止。
  - リダイレクト時や接続先のホストがプライベートアドレスでないかを検査して SSRF を防止しています。
  - レスポンス最大サイズを制限（デフォルト 10MB）してメモリ DoS を防ぐ仕組みがあります。

- DuckDB スキーマ:
  - init_schema は冪等（既存テーブルはスキップ）で、親ディレクトリがなければ自動作成します。
  - 監査用スキーマは別の初期化関数 init_audit_schema / init_audit_db を提供します。init_audit_schema は `SET TimeZone='UTC'` を実行します。

- テストしやすさ:
  - jquants_client のトークン取得や news_collector の _urlopen はモック可能で、テスト容易性を考慮しています。

---

必要であれば README に含めるサンプル .env.example、CI 実行コマンド、ユニットテスト手順、あるいは strategy/execution の設計ガイドラインを追加できます。どの情報を追加したいか教えてください。