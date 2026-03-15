# KabuSys

日本株向け自動売買プラットフォームの軽量ライブラリ群です。  
データ収集（J-Quants）、データベーススキーマ（DuckDB）、監査ログ（発注 → 約定のトレーサビリティ）、環境設定ユーティリティなど、アルゴリズム売買システムの基盤機能を提供します。

---

## 主な特徴
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）に合わせたスロットリング
  - 再試行（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB への冪等的な保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - 頻出クエリのためのインデックス定義
  - 簡単な初期化 API（init_schema, get_connection）
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定を UUID 連鎖でトレース
  - 冪等キー（order_request_id）により二重発注を防止
  - UTC タイムスタンプ、ステータス管理、インデックス備え
- 環境設定管理
  - .env と OS 環境変数の自動読み込み（プロジェクトルート基準）
  - 必須設定のチェックと便利なプロパティ（settings）

---

## 要件
- Python 3.10 以上（型注記で | を利用）
- 依存パッケージ（例）
  - duckdb
- （プロジェクト配布形態に応じてその他パッケージが必要になる場合があります）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# またはプロジェクトのパッケージ化に合わせて pip install -e .
```

---

## 環境変数（.env）
自動的にプロジェクトルートの `.env`、`.env.local` をロードします（環境変数が優先、`.env.local` は上書きされます）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite パス（監視用など、デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

簡易 `.env.example`:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（概要）
1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成し有効化
3. 必要なパッケージをインストール（例: duckdb）
4. プロジェクトルートに `.env` を作成して必須変数を設定
5. DuckDB スキーマを初期化する

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# .env を作成（JQUANTS_REFRESH_TOKEN 等を設定）
python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"
```

---

## 使い方（簡単な例）

- DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path に基づいてファイルを作成・初期化
```

- J-Quants から日足を取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)

records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 監査ログ（audit）テーブルの初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
# conn は上の init_schema で取得した DuckDB 接続
init_audit_schema(conn)
```

注意点:
- J-Quants API はレート制限が厳しいため、fetch 関数は内部でスロットリングと再試行制御を行います。
- 401 を受け取ると自動的にリフレッシュトークンで ID トークンを再取得し、1 回リトライします。
- DuckDB への INSERT は ON CONFLICT DO UPDATE を使って冪等に保存します。

---

## ディレクトリ構成（抜粋）
以下は本リポジトリの主要ファイル / モジュールの構成です（与えられたソースに基づく）:

- src/
  - kabusys/
    - __init__.py
    - config.py               -- 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py     -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py             -- DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
      - audit.py              -- 監査ログスキーマ（signal, order_request, executions）
    - strategy/
      - __init__.py           -- 戦略層のエントリポイント（将来的な拡張ポイント）
    - execution/
      - __init__.py           -- 発注・ブローカー連携層（将来的な拡張ポイント）
    - monitoring/
      - __init__.py           -- 監視・アラート関連（拡張ポイント）

---

## 開発上の注意事項
- Python の型記法（A | B）を用いているため Python 3.10 以上を推奨します。
- .env のパースはシェル風のクォート/エスケープ、コメントをある程度考慮しますが、複雑なケースはテストして下さい。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml 存在ディレクトリ）を探索して行います。テスト時などに無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初期化後は conn をプロセス内で再利用してください（接続回数を抑えるため）。

---

必要であれば、README に例となる .env.example ファイル全文、より詳細な API 使用例（財務データ取得・マーケットカレンダー取得・監査ログのサンプル挿入）や CI / デプロイ手順も追記します。どの情報を追加しますか？