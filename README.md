# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ/バックエンドコンポーネント群）

本リポジトリはデータ取得・ETL、スキーマ定義、品質チェック、監査ログ（トレーサビリティ）など、自動売買システムのバックエンド基盤を提供します。戦略・注文実行・モニタリングの骨組みを含み、外部API（J-Quants、kabuステーション等）と連携してデータを収集・永続化し、品質チェックを行い、監査可能な発注フローを保持します。

バージョン: 0.1.0

---

## 主な機能

- 環境設定
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルートを検出）
  - 必須変数未設定時はエラーで通知
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- データ取得（J-Quants API クライアント）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 初期化ユーティリティ（init_schema、init_audit_schema）
  - インデックス定義付きでクエリ性能を考慮

- ETL パイプライン
  - 差分取得（DB 上の最終取得日を基準に backfill を行う）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - ETL 結果を集約する ETLResult クラス

- データ品質チェック
  - 欠損データ検出（OHLC 欄）
  - スパイク検出（前日比閾値）
  - 主キー重複チェック
  - 日付整合性チェック（未来日／非営業日）
  - チェック結果は QualityIssue リストとして取得、重大度に基づく判断が可能

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル
  - UUID ベースのトレーサビリティ（signal_id → order_request_id → broker_order_id）
  - 全て UTC タイムスタンプ、削除しない前提の構造

---

## 事前準備 / システム要件

- Python 3.10 以上（型ヒントで Python 3.10+ の union 型記法を使用）
- pip, virtualenv 等
- 依存パッケージ
  - duckdb
  - （標準ライブラリの urllib 等を使用。外部 HTTP クライアントは不要）

例（仮想環境作成〜依存インストール）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発時にパッケージを editable install する場合
pip install -e .
```

※ packaging の設定があれば `pip install -e .` でインストールできます。最小限の依存は duckdb です。

---

## 環境変数（必要なもの）

以下はコード内で参照される主な環境変数です（必須/任意を示します）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — 通知用 Slack Bot Token
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は "1" を設定
- KABUSYS_*（プロジェクト固有の追加設定がある場合）

DB パス（デフォルト値あり）:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env の読み込み優先順位:
1. OS 環境変数
2. .env.local
3. .env

自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

例: .env（簡易）

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

1. リポジトリをクローンし、仮想環境を作成
2. 必要パッケージをインストール（duckdb など）
3. .env または環境変数を用意（.env.example を参照）
4. DuckDB スキーマを初期化

例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

監査ログ用テーブルを追加する場合:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（主な API とサンプル）

以下はライブラリの主要な使い方の一例です。

- ETL（日次）を実行する

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token, run_quality_checks 等を指定可能
print(result.to_dict())
```

- J-Quants API を直接使う（トークン取得・データ取得・保存）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
id_token = jq.get_id_token()  # settings からリフレッシュトークンを使用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックを個別に実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None, reference_date=None)
for i in issues:
    print(i)
```

- 監査ログ（order_requests / executions）を初期化

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 注意点 / 設計上のポイント

- J-Quants クライアントはレート制限（120 req/min）を固定間隔スロットリングで遵守します。
- HTTP リクエストはリトライ（指数バックオフ）を行い、401 受信時は refresh token から id_token を再取得して再試行します（1 回のみ）。
- データ保存は冪等（ON CONFLICT DO UPDATE）設計になっており、差分ETL の再実行が安全です。
- ETL では「バックフィル」機能を持ち、最終取得日の数日前から再取得して API の後出し修正を吸収します。
- すべてのタイムスタンプは UTC を原則としています（監査テーブルは明示的に TimeZone='UTC' をセットします）。
- KABUSYS_ENV の有効値は "development", "paper_trading", "live" のみです。

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - .env の自動読み込み、Settings クラス（環境変数のラッパー）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得、リトライ、保存ロジック）
    - schema.py
      - DuckDB スキーマ定義と初期化 (Raw/Processed/Feature/Execution)
    - pipeline.py
      - ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py（戦略関連モジュールのプレースホルダ）
  - execution/
    - __init__.py（注文実行関連のプレースホルダ）
  - monitoring/
    - __init__.py（モニタリング関連のプレースホルダ）

（上記は現在のソースに基づく主要ファイル群の説明です）

---

## 今後の拡張案（例）

- 実際のブローカー接続（kabuステーション）の実装（execution 層）
- 戦略実装テンプレート、バッチ／リアルタイムの戦略実行エンジン
- Slack 等への通知ハンドラの統合（settings でトークンは読み込み済み）
- CI 用の DB 初期化・テスト用モード、モック API の導入

---

必要であれば README に含める CLI コマンド例や .env.example、開発環境での詳細なセットアップ手順（pytest, linters, pre-commit 設定など）を追加します。どの情報を追加しますか？