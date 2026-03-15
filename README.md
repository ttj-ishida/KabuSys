# KabuSys

日本株自動売買プラットフォームのコアライブラリ（KabuSys）。データ取得、スキーマ管理、監査ログ、設定管理など自動売買システムに必要な基盤機能を提供します。

- バージョン: 0.1.0

## 概要

KabuSys は以下の主要機能を提供する Python モジュール群です。

- J-Quants API からの市場データ（株価日足、財務データ、JPXカレンダー）取得
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（信号→発注→約定のトレーサビリティ）用スキーマ管理
- 環境変数を中心とした設定管理（.env 自動ロード、必須値チェック）
- API クライアントはレート制御、リトライ、トークン自動リフレッシュ等の堅牢な設計

主な設計方針は「冪等性」「トレーサビリティ」「Look‑ahead bias の防止」「外部 API の健全な利用（レート制限・リトライ）」です。

## 機能一覧

- config
  - .env ファイル（および .env.local）の自動読み込み（プロジェクトルートは .git または pyproject.toml で探索）
  - 必須環境変数の取得（未設定時は ValueError）
  - KABUSYS_ENV（development / paper_trading / live）による環境判定
  - LOG_LEVEL 管理

- data.jquants_client
  - get_id_token：リフレッシュトークンから ID トークンを取得（POST）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応で API から取得
  - _request：レート制御（120 req/min 固定）、リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - save_* 系関数：DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）

- data.schema
  - init_schema(db_path)：DuckDB の全テーブルを作成（Raw / Processed / Feature / Execution）
  - get_connection(db_path)：既存 DB へ接続（初回は init_schema を推奨）
  - 多数のテーブル定義とインデックス（prices_daily, raw_prices, features, signals, orders, trades, positions 等）

- data.audit
  - init_audit_schema(conn)：監査ログ用テーブル（signal_events / order_requests / executions）を追加
  - init_audit_db(db_path)：監査用独立 DB を初期化して返す（UTC タイムゾーン固定）
  - 監査用に UUID ベースの冪等キーとステータス管理を想定

## 前提（Requirements）

- Python 3.9+
- duckdb
- 標準ライブラリの urllib 等（外部 HTTP クライアントは使用していません）

必要ならプロジェクト固有の依存を追加してください（例: pip install duckdb）。

## セットアップ手順

1. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb
   ```

   プロジェクトがパッケージ化されている場合は:
   ```
   pip install -e .
   ```

3. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - プロジェクトルートはこのパッケージファイル位置を基に .git または pyproject.toml を探索します

4. DuckDB 用ディレクトリ（デフォルト: data/）が自動で作成されます。必要に応じて `DUCKDB_PATH` を設定してください。

## 環境変数 (.env) — 必須/オプション

必須（システムが動作するのに必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack ボットトークン（通知等に使用）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）

オプション（デフォルト値あり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパース仕様（主な挙動）
- 空行・# で始まる行は無視
- export KEY=val 形式に対応
- シングル/ダブルクォート内はバックスラッシュエスケープ対応で値を扱う
- クォートなしで # がコメント扱いとなるのは '#' の直前が空白またはタブの場合のみ

## 使い方（簡単なコード例）

DuckDB のスキーマ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

J-Quants から株価日足を取得して保存する:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"{n} 件を保存しました")
```

監査ログスキーマの初期化（既存接続へ追加）:
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)
```

監査専用 DB を新規作成:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

注意点（J-Quants クライアント）
- レート制限: 120 req/min（内部で固定間隔スロットリングを実装）
- リトライ: 最大 3 回（指数バックオフ）、408/429/5xx を対象
- 401 受信時はトークンを自動リフレッシュして1回リトライ
- 取得データには fetched_at（UTC）を付与して Look‑ahead bias を防止
- save_XXX 系は ON CONFLICT DO UPDATE による冪等性を保証

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（src 以下）:

- src/kabusys/
  - __init__.py  — パッケージ初期化（version 等）
  - config.py    — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック、レート・リトライ）
    - schema.py         — DuckDB スキーマ定義と初期化（全テーブル / インデックス）
    - audit.py          — 監査ログ（signal_events / order_requests / executions）用スキーマ
    - (その他: audit/init 用ユーティリティ等)
  - strategy/
    - __init__.py  — 戦略モジュールのエントリ（実装はここに追加）
  - execution/
    - __init__.py  — 発注・実行関連のエントリ（実装はここに追加）
  - monitoring/
    - __init__.py  — 監視・モニタリング関連（将来的に実装）

ファイルごとの役割は上記コメントに詳述しています。

## 運用上の注意

- KABUSYS_ENV を正しく設定して本番（live）環境とテスト（paper_trading / development）を分離してください。
- .env.local は .env より優先され上書きされます。OS 環境変数は常に最優先で保護されます。
- 大量リクエストを送る場合は J-Quants のレート制限に注意し、/_request 内の制御に従ってください。
- DuckDB のファイルパスは settings.duckdb_path で管理されます（デフォルト: data/kabusys.duckdb）。
- 監査ログテーブルは削除しない前提で設計されています（ON DELETE RESTRICT 等）。監査データの運用方針を決めてから運用してください。

---

この README はコードベースの現状に基づいて作成しています。戦略・発注の具体的な実装（strategy, execution, monitoring パッケージ）はプロジェクトの要件に応じて追加・拡張してください。必要であれば README に具体的なユースケースや CLI / サービス起動方法の追記も対応します。