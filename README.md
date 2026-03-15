# KabuSys

日本株自動売買システムのライブラリ（パッケージ）。  
データ取得、DBスキーマ管理、監査ログ、戦略／実行／モニタリングの骨組みを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants 等の外部 API から市場データ（株価日足、財務データ、マーケットカレンダー等）を取得するクライアント
- DuckDB を用いた三層（Raw / Processed / Feature）データスキーマ定義と初期化
- 発注フローを完全にトレース可能にする監査ログスキーマ（order_request / executions 等）
- 環境変数管理と簡易設定ラッパー
- 将来的な戦略 / 実行 / モニタリング機能のためのモジュール群の骨格

設計上のポイント:
- J-Quants クライアントはレート制限（120 req/min）を自動的に守る RateLimiter を備え、リトライ／トークン自動リフレッシュを行います。
- DuckDB のテーブル作成は冪等で、ON CONFLICT / CHECK 制約等を活用してデータ整合性を担保します。
- 監査ログは削除せず、UUID ベースの連鎖でシグナルから約定までトレース可能にします。

---

## 主な機能一覧

- 環境変数読み込みと設定ラッパー（kabusys.config.settings）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要なら自動ロードを無効化可能）
  - 必須環境変数チェックを提供
- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - レートリミット制御、指数バックオフリトライ、401 時の自動リフレッシュ
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - init_schema(db_path) で DB を初期化
  - get_connection(db_path) で既存 DB に接続
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL とインデックス
  - init_audit_schema(conn) / init_audit_db(path)

---

## 必要環境・依存ライブラリ

- Python 3.9+
  - （型注釈で `|` を使用しているため 3.10 以降を想定している箇所もありますが、プロジェクトでの最終サポートバージョンに合わせてください）
- 必要パッケージ（最低限）
  - duckdb

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# またはパッケージ化されている場合:
# pip install -e .
```

---

## 環境変数（主なもの）

KabuSys は環境変数から設定を読み込みます。プロジェクトルートの `.env` / `.env.local` を自動で読み込む仕組みがあります（.git または pyproject.toml を起点に探索）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu ステーション API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development, paper_trading, live)
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（任意）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- `.env` → `.env.local` の順で読み込まれ、.env.local は上書き（override=True）されます。ただし OS 環境変数は保護されます。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # .venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール
   必要最小限:
   ```bash
   pip install duckdb
   ```
   プロジェクトで requirements.txt / pyproject.toml があればそれを使ってください:
   ```bash
   pip install -r requirements.txt
   # or
   pip install -e .
   ```

4. 必要な環境変数を設定（.env をプロジェクトルートに作成）
   - 上記の .env 例を参考に設定してください。

5. DuckDB スキーマを初期化
   Python REPL またはスクリプト内で:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # またはメモリ DB を使う場合:
   # conn = schema.init_schema(":memory:")
   ```

6. 監査ログスキーマの初期化（必要に応じて）
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   # または専用 DB を作成する場合:
   # conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な API の例）

- 設定値にアクセス:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- J-Quants から株価日足を取得して DuckDB に保存:
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data import schema

# DB 初期化／接続
conn = schema.init_schema("data/kabusys.duckdb")

# データ取得（例: 特定銘柄・期間）
records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))

# 保存（冪等）
count = save_daily_quotes(conn, records)
print(f"保存件数: {count}")
```

- 財務データの取得と保存:
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements

financials = fetch_financial_statements(code="7203")
cnt = save_financial_statements(conn, financials)
print(cnt)
```

- マーケットカレンダー取得:
```python
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

calendar = fetch_market_calendar()
save_market_calendar(conn, calendar)
```

- 監査ログの初期化（既存接続に追加）:
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

内部的に J-Quants クライアントは以下を行います:
- 120 req/min を守るための固定間隔スロットリング（_RateLimiter）
- 408/429/5xx に対する指数バックオフのリトライ（最大 3 回）
- 401 受信時はリフレッシュトークンで ID トークンを更新して 1 回リトライ
- ページネーションに対応し pagination_key を使って全件取得
- 取得時刻（fetched_at）を UTC で保存して Look-ahead Bias を防止

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要ファイル／モジュールです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py  -- J-Quants API クライアント（取得/保存ロジック）
      - schema.py          -- DuckDB スキーマ定義・初期化
      - audit.py           -- 監査ログスキーマ定義・初期化
      - (その他: raw / processed / feature 用テーブル DDL)
    - strategy/
      - __init__.py  -- 戦略関連モジュール（骨組み）
    - execution/
      - __init__.py  -- 発注／Execution 層（骨組み）
    - monitoring/
      - __init__.py  -- モニタリング関連（骨組み）

---

## 注意事項 / 運用上のポイント

- 環境変数の自動ロードは便利ですが、本番環境やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。
- DuckDB のパスはデフォルトで data/kabusys.duckdb です。運用では適切な永続化先を指定してください。
- J-Quants API のレート制限やエラーハンドリングはクライアント側でかなり考慮していますが、運用時は追加のスロットリングや監視を検討してください。
- 監査ログ（audit）は削除しない前提で設計されています。バックアップ・アーカイブ方針を必ず策定してください。
- 本リポジトリはライブラリ部分を提供するもので、実際の売買（ライブ取引）を行う前には十分なテストとリスク管理が必要です（ペーパートレードでの検証推奨）。

---

## 今後の展開（想定）

- strategy モジュールに標準的な戦略（例: momentum, mean-reversion）を追加
- execution モジュールで kabu ステーションや証券会社 API との接続を実装（発注・約定処理）
- monitoring モジュールで Slack 通知やダッシュボード連携を提供

---

問題や貢献、バグ報告があればリポジトリの Issue へお願いします。