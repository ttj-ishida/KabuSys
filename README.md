# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
データ収集（J-Quants、RSS）、ETLパイプライン、データ品質チェック、DuckDBスキーマ、監査ログなどを提供します。

---

## 概要

KabuSys は日本株の自動売買基盤の一部を構成するライブラリ群です。主な役割は以下です。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集（SSRF対策、XML攻撃対策、トラッキングパラメータ除去）
- DuckDB による3層データスキーマ（Raw / Processed / Feature）および Execution / Audit 層
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレース）

パッケージルート: `kabusys`  
バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 機能一覧

- 環境設定管理（`.env` 自動読み込み、必須キー検査）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レート制御（120 req/min）、再試行（指数バックオフ）、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集
  - RSS フィード取得、記事正規化、トラッキングパラメータ除去、SHA256 による記事ID生成
  - defusedxml を利用した XML 攻撃対策
  - SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検査）
  - レスポンスサイズ制限（メモリDoS、Gzip bomb対策）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁コード）
- データスキーマ
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義
  - `init_schema()` / `get_connection()` / `init_audit_schema()` を提供
- ETL パイプライン
  - 差分更新、バックフィル、カレンダー先読み
  - 品質チェックの実行（収集は続行し、問題は検出して戻す）
- 品質チェック
  - 欠損データ検出、スパイク検出、重複検出、日付整合性チェック
  - 検出結果は `QualityIssue` 型で返却
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル
  - UTC タイムスタンプ強制、冪等キー、豊富なステータス管理

---

## 要件

- Python 3.10 以上（型注釈に `X | None` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

プロジェクトに requirements ファイルがある場合はそれを利用してください。最低限の例:

pip install duckdb defusedxml

（パッケージ化されている場合は `pip install .` / `pip install -e .` を推奨）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

2. 依存パッケージをインストールします。

   bash
   pip install -r requirements.txt
   # あるいは最小
   pip install duckdb defusedxml

3. 環境変数を設定します。プロジェクトルートに `.env` を置くと自動読み込みされます（`.env.local` は `.env` 上書き）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack ボットトークン（通知に使用）
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション（デフォルト値）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

例 `.env`:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## データベース初期化

DuckDB スキーマを初期化するサンプル:

python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 必要なら監査スキーマを追加
from kabusys.data import audit
audit.init_audit_schema(conn)

`init_schema()` は既存テーブルがあればスキップするため冪等です。パス `" :memory: "` を渡すとインメモリ DB を使用します。

---

## 使い方（簡単な例）

- J-Quants の ID トークン取得（内部で refresh token を使用）:

python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照

- 株価データ取得と保存:

python
import duckdb
from kabusys.data import jquants_client as jq
conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)

- RSS ニュース収集（保存まで）:

python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection, init_schema
conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 既知銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)

- 日次 ETL 実行:

python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

- 品質チェックだけ実行したい場合:

python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)

---

## 設計上のポイント（実装上の重要事項）

- 環境変数自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を読み込み。
  - OS 環境変数を保護し、`.env.local` で上書き可能。
  - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
- J-Quants クライアント:
  - レート制御: 120 req/min（固定間隔スロットリング）
  - リトライ: 最大3回、指数バックオフ、408/429/5xx を再試行
  - 401 受信時はリフレッシュトークンで自動再取得して1回リトライ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への保存は冪等（ON CONFLICT）
- ニュース収集:
  - defusedxml による XML 攻撃防止
  - SSRF 対策（スキーム、プライベートIPチェック、リダイレクト検査）
  - レスポンス上限（10MB）と gzip 解凍後サイズチェック
  - 記事IDは正規化URLの SHA-256（先頭32文字）
  - 銘柄抽出は正規表現で 4 桁数字を抽出し known_codes でフィルタ
- ETL & 品質管理:
  - 差分取得（DB の最終日を確認）とバックフィル（デフォルト3日）
  - 市場カレンダーは先読み（デフォルト90日）
  - 品質チェックは全項目を収集（Fail-Fast ではなく報告）
- スキーマ:
  - Raw / Processed / Feature / Execution / Audit の各レイヤーを定義
  - 外部キーやインデックスを定義し検索性とトレーサビリティを重視

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py      # J-Quants API クライアント
      news_collector.py      # RSS ニュース収集
      pipeline.py            # ETL パイプライン
      schema.py              # DuckDB スキーマ定義・初期化
      audit.py               # 監査ログスキーマ
      quality.py             # データ品質チェック
      pipeline.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

（上記は今回のコードベースに含まれるファイル構成を要約したものです）

---

## 追加情報 / 注意事項

- 環境や運用モード:
  - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかを指定。`is_live` や `is_paper` 判定に利用。
- ロギング:
  - LOG_LEVEL 環境変数で制御（デフォルト INFO）。
- セキュリティ:
  - J-Quants のトークンや kabu API のパスワード等を `.env` または環境変数で安全に管理してください。
- テスト:
  - ネットワークリクエストやファイルアクセス部はモック可能（例: news_collector._urlopen を差し替え）。

---

必要であれば README に以下を追記できます:
- CI / テスト実行方法
- 具体的な .env.example ファイル
- API 使用例のより詳細なコードサンプル（kabuステーション連携、Slack 通知など）
- デプロイ / 運用手順（systemd / docker-compose 例）

ご希望があれば、上記のいずれかを追記して README を拡張します。