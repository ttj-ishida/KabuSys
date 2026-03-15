# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。データ収集（J-Quants）、データベーススキーマ（DuckDB）、監査ログ、戦略／実行／モニタリングのための基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（株価日足・財務データ・マーケットカレンダー）の取得と DuckDB への保存
- データ層（Raw / Processed / Feature / Execution）を想定した DuckDB スキーマの定義・初期化
- 発注フローをトレース可能にする監査ログ（監査テーブル群）の提供
- 環境変数管理（.env 自動読み込み）や設定取得のユーティリティ

設計上のポイント:
- API のレート制限（120 req/min）に準拠するレートリミッタを搭載
- HTTP エラーに対するリトライと指数バックオフ、401 時のトークン自動リフレッシュ対応
- 取得タイミング（fetched_at）を UTC で記録して Look-ahead Bias を防止
- DuckDB への INSERT は冪等（ON CONFLICT DO UPDATE）を採用

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（OS 環境変数優先、保護）
  - 必須環境変数取得とバリデーション
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - JPX マーケットカレンダー（fetch_market_calendar）
  - DuckDB へ保存するユーティリティ（save_* 系）
  - レートリミット、リトライ、トークン管理を内蔵
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL とインデックス
  - init_schema(db_path) による初期化
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブル
  - init_audit_schema(conn) / init_audit_db(db_path)
- パッケージの名前空間（kabusys.__init__）で主要モジュールを公開

---

## 必要条件

- Python 3.10 以上（タイプヒントで | 演算子を使用）
- duckdb（DuckDB 用 Python バインディング）
- ネットワークアクセス（J-Quants API）
- 必要な環境変数（下記参照）

実際の実行環境では kabu ステーション API や Slack との連携に必要な鍵も必要です。

---

## 環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり / 調整可能）:
- KABUSYS_ENV — one of development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（値が存在すれば無効化）

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。
読み込み優先順位: OS 環境変数 > .env.local > .env
（OS 環境変数は保護され、.env で上書きされません）

サンプル .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （その他、プロジェクトで使用する追加パッケージがあれば適宜インストール）
4. .env をプロジェクトルートに作成（または環境変数を設定）
5. DuckDB スキーマを初期化する（下記参照）

---

## 使い方（簡単な例）

以下は J-Quants から日足を取得して DuckDB に保存する簡単なスクリプト例です。

```python
from pathlib import Path
import duckdb
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 1. DB 初期化（初回のみ）
db_path = settings.duckdb_path  # 環境変数 DUCKDB_PATH を利用
conn = init_schema(db_path)

# 2. J-Quants からデータ取得（例: 特定銘柄）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 3. 取得データを保存
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

監査ログ（order_requests / executions）を別 DB に作る場合:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を渡して監査テーブルを利用する
```

備考:
- fetch_* 系は内部でレート制御・リトライを行います。
- get_id_token() を内部で使用しており、401 の際は自動でリフレッシュを試みます。
- save_* は冪等性を持ち、重複レコードは UPDATE によって上書きされます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                — パッケージのエントリ（__version__ など）
  - config.py                  — 環境変数 / 設定管理、.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - audit.py                 — 監査ログ（signal_events, order_requests, executions）初期化
  - strategy/
    - __init__.py              — 戦略モジュール（雛形）
  - execution/
    - __init__.py              — 発注実行関連（雛形）
  - monitoring/
    - __init__.py              — モニタリング関連（雛形）

その他:
- .env / .env.local            — 環境変数（プロジェクトルートに置く）
- data/                       — デフォルトのデータ格納先（DuckDB 等）

---

## 注意事項 / 運用上のヒント

- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を用います。パッケージを配布したあとやテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを無効化できます。
- DuckDB の初期化は init_schema() を一度だけ実行してください（冪等なので複数回でも安全ですが、ディレクトリ作成等の副作用があります）。
- J-Quants のレート制限（120 req/min）に従うため大量取得を行う場合は時間を考慮してください。ライブラリは内部でスロットリングしますが、長時間の大量取得処理では全体設計を検討してください。
- すべてのタイムスタンプは UTC で扱うことを前提としています（監査ログ等で明示）。

---

## ライセンス / 貢献

（このテンプレートでは省略しています。実運用時は LICENSE ファイルを追加してください。）

---

以上。README の内容に追加したい具体的な使用例や CI / packaging 手順があれば教えてください。必要に応じて英語版や短いチュートリアルも作成します。