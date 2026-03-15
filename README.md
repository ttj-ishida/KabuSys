# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）の README。  
このリポジトリはデータ取得、DuckDB スキーマ定義、監査ログ（トレーサビリティ）など、自動売買プラットフォームのインフラ的な部分を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支える基盤モジュール群です。主に以下を提供します。

- J-Quants API からの市場データ取得クライアント（株価日足・財務データ・マーケットカレンダー）
- DuckDB を用いたスキーマ定義および初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ用スキーマ（シグナル→発注→約定を UUID 連鎖でトレース可能にする）
- 環境変数管理（.env 自動読み込み・検証用の Settings）

設計上のポイント:
- J-Quants クライアントは API レート制限（120 req/min）を守る仕組み、リトライ・トークン自動リフレッシュを備えています。
- DuckDB の DDL は冪等的（既に存在するテーブルはスキップ）で、初回のみのセットアップを簡便にします。
- 監査ログは削除を前提とせず、すべてのイベントにタイムスタンプを持たせて追跡可能にします。

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証（Settings）
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token (リフレッシュトークンから idToken を取得)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レート制限（120 req/min）固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時はトークン自動リフレッシュ
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar） — ON CONFLICT による冪等保存

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) : 全テーブル作成（Raw / Processed / Feature / Execution）
  - get_connection(db_path) : 既存 DB への接続（初期化は行わない）
  - 定義済みテーブル例: raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions など
  - インデックス定義を含む

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) : 監査ログ用テーブルを既存接続へ追加
  - init_audit_db(db_path) : 監査ログ専用 DB の初期化
  - テーブル例: signal_events, order_requests, executions
  - すべての TIMESTAMP は UTC で保存

---

## 要求環境 / 依存関係

- Python >= 3.10（PEP 604 の union 型（A | B）を使用）
- 依存パッケージ（最低限）:
  - duckdb

インストール例:
- 仮想環境作成（推奨）:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip を更新して duckdb をインストール:
  - python -m pip install --upgrade pip
  - pip install duckdb
- 開発中のパッケージとしてインストール可能であれば:
  - pip install -e .  （プロジェクトに pyproject.toml / setup がある前提）

---

## 環境変数（.env）

自動読み込みの挙動:
- プロジェクトルートはこのファイルの位置から上方向に `.git` または `pyproject.toml` を探索して特定します。
- 自動ロードの順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

主要な環境変数（必須／任意）:
- 必須:
  - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD      — kabuステーション API のパスワード
  - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL      — kabuAPI のベース URL（既定: http://localhost:18080/kabusapi）
  - DUCKDB_PATH            — DuckDB ファイルパス（既定: data/kabusys.duckdb）
  - SQLITE_PATH            — 監視用 SQLite（既定: data/monitoring.db）
  - KABUSYS_ENV            — 実行環境 (development | paper_trading | live)（既定: development）
  - LOG_LEVEL              — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO）

簡単な .env 例:
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

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化する（任意）。
2. 依存ライブラリをインストール:
   - pip install duckdb
   - （プロジェクトがパッケージ化されている場合）pip install -e .
3. プロジェクトルートに `.env` を作成し、必要な環境変数を設定する。
4. 初期 DB を作成する（例: DuckDB）:
   - Python から schema.init_schema() を呼び出す（下記の使用例参照）。

---

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化（永続 DB）:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数から取得される
conn = init_schema(settings.duckdb_path)
```

- インメモリ DB（テスト）:

```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

- J-Quants から日次株価を取得して DuckDB に保存:

```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- id_token を直接取得（例: カスタム処理に利用）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

- 監査ログの初期化（既存の DuckDB 接続に追加）:

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

注意点:
- fetch_* 系はページネーション対応、内部で ID トークンキャッシュを使いトークン期限切れの際は自動リフレッシュ（1 回）します。
- レートリミット（120 req/min）は固定間隔スロットリングで守られます。
- save_* 系は ON CONFLICT によるアップサートで冪等的に保存します。

---

## ディレクトリ構成

（主要ファイルのみ、抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存）
    - schema.py                    — DuckDB スキーマ定義・初期化
    - audit.py                     — 監査ログ（signal_events / order_requests / executions）
    - audit.py
    - (その他: news / audit などの拡張モジュール)
  - strategy/
    - __init__.py                   — 戦略層（未実装のプレースホルダ）
  - execution/
    - __init__.py                   — 発注・ブローカー連携（未実装のプレースホルダ）
  - monitoring/
    - __init__.py                   — モニタリング関連（未実装のプレースホルダ）

主要モジュールのエントリポイント:
- kabusys.config.settings — アプリケーション設定オブジェクト
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.jquants_client.fetch_* / save_*
- kabusys.data.audit.init_audit_schema / init_audit_db

---

## 運用上の注意 / ヒント

- 自動ロードされる .env / .env.local は OS 環境変数を上書きしません（.env.local は上書きするが Protected として最初にあった OS 環境変数は保護されます）。テストなどで明示的に別の設定を使いたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境を読み込んでください。
- J-Quants API のトークンは短期有効な ID トークンとリフレッシュトークンの構成になっています。get_id_token を用いる際はリフレッシュトークンを正しく設定してください（Settings から取得可能）。
- DuckDB のファイルパスは既定で `data/kabusys.duckdb`。永続化先ディレクトリは init_schema が自動作成します。
- 監査ログは削除を前提にしていないため、保守方針（バックアップ・アーカイブ）が必要になった場合は運用で対応してください。

---

## 貢献・拡張

- 戦略（strategy）および実取引（execution）モジュールはプレースホルダになっており、ここにアルゴリズムやブローカー連携を実装していく想定です。
- 追加のデータソース（ニュースプロバイダ等）やモニタリング機能は data/monitoring 以下に実装してください。
- PR は各モジュールに対してユニットテスト（特に schema と audit の DDL、jquants_client の HTTP エラー・リトライ挙動）を追加するとレビューが速くなります。

---

必要であれば README を英語版で出力したり、より詳細な API リファレンス（各関数の引数・戻り値・例外）を自動生成するドキュメントを追加できます。どの情報を優先して拡充したいか教えてください。