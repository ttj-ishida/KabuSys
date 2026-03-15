# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ取得、永続化（DuckDB）、監査ログ、戦略・発注レイヤーの骨組みを提供します。J-Quants API や kabuステーション API と連携し、Look-ahead バイアス対策やレート制御、冪等性を考慮した実装になっています。

---

## 主な機能

- 環境変数ベースの設定管理（.env / .env.local の自動読み込み）
- J-Quants API クライアント
  - 日次株価（OHLCV）の取得（ページネーション対応）
  - 四半期財務データの取得
  - JPX マーケットカレンダーの取得
  - レート制限（120 req/min）とリトライ/トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead 防止）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層を含むテーブル群
  - インデックス、制約、冪等な INSERT（ON CONFLICT DO UPDATE）
- 監査ログ（audit）
  - シグナル → 発注 → 約定のトレーサビリティを担保するテーブル群
  - order_request_id による冪等制御、UTC タイムスタンプ、ステータス管理
- 拡張用のパッケージ領域（strategy, execution, monitoring）のスケルトン

---

## 動作要件

- Python 3.10 以上（型アノテーションで `|` を使用）
- 必要パッケージ（例）
  - duckdb
- 推奨: 仮想環境（venv, pipenv, poetry 等）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```
（プロジェクトの requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境設定 (.env)

プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / 既定値あり:
- KABUSYS_ENV: `development`（既定） / `paper_trading` / `live`
- LOG_LEVEL: `INFO`（既定） 他に `DEBUG`, `WARNING`, `ERROR`, `CRITICAL`
- KABU_API_BASE_URL: kabu API のベース URL（既定: `http://localhost:18080/kabusapi`）
- DUCKDB_PATH: DuckDB ファイルパス（既定: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite パス（既定: `data/monitoring.db`）

簡易 .env.example:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を用意して依存ライブラリをインストール
   - 最低限: duckdb
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を配置して環境変数を設定
4. DuckDB スキーマを初期化

例（対話的に）:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

監査ログ（audit）テーブルを追加する場合:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema の返り値
```

監査用 DB を別ファイルで用意する場合:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（基本的な例）

設定オブジェクトにアクセス:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
log_level = settings.log_level
```

J-Quants から日足を取得して DuckDB に保存する基本フロー:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 全銘柄・期間指定なしで取得（ページネーション対応）
records = fetch_daily_quotes()

# raw_prices テーブルに冪等的に保存
n = save_daily_quotes(conn, records)
print(f"{n} 件を保存しました")
```

財務データの取得・保存:
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements

fin = fetch_financial_statements(date_from=date(2022,1,1), date_to=date(2023,12,31))
save_financial_statements(conn, fin)
```

市場カレンダー:
```python
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

認証トークンの明示取得（通常は内部で自動管理される）:
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
```

ログ・例外・リトライ等はクライアント実装側で自動的に扱われます（レート制限や 401 リフレッシュ対応など）。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（src/kabusys 配下）。

- src/kabusys/
  - __init__.py                      - パッケージ定義（version 等）
  - config.py                         - 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py               - J-Quants API クライアント（取得・保存ロジック）
    - schema.py                       - DuckDB スキーマ定義と初期化関数
    - audit.py                        - 監査ログ（signal / order_request / executions）定義
  - strategy/
    - __init__.py                      - 戦略モジュール用の名前空間（拡張ポイント）
  - execution/
    - __init__.py                      - 発注 / ブローカー連携用の名前空間（拡張ポイント）
  - monitoring/
    - __init__.py                      - モニタリング / アラート用の名前空間（拡張ポイント）

各モジュールの短い説明:
- config.py: .env ファイルパース、強力なパース（クォート・エスケープ・コメント処理）、自動ロードロジック、Settings プロパティで必須チェック。
- data/jquants_client.py:
  - レート制御（120 req/min）を固定間隔で保証する RateLimiter 実装
  - リトライ（指数バックオフ）、401 時の一度だけのトークンリフレッシュ
  - 取得したレコードを DuckDB に冪等に保存する save_* 関数
- data/schema.py:
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - init_schema() で一括作成、get_connection() で接続取得
- data/audit.py:
  - 監査目的のテーブルとインデックス定義、init_audit_schema / init_audit_db

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリ自体は発注・実運用を行う土台を提供しますが、実際の発注ロジック（リスク管理、ポジション管理、ブローカー固有の API 呼び出し）は strategy / execution 層で実装してください。
- 本番運用時は KABUSYS_ENV=live を設定して、安全係数や追加の確認フローを有効化することを推奨します。
- DuckDB のバックアップやマイグレーション戦略を設計してください。監査ログは基本的に削除しない前提です。
- 環境変数やシークレットは Git 管理に含めないでください（`.env` は通常 .gitignore に追加）。

---

## 追加情報 / 今後の拡張案

- kabuステーションとの発注・約定連携ラッパー（execution 層）の実装
- Slack / Prometheus 等を用いたモニタリング・アラート実装（monitoring）
- strategy 用のサンプル実装（バックテスト・ペーパー取引モード）
- CI でのスキーマ検証・簡易 E2E テスト

---

この README は現状のコードベース（src/kabusys）に基づいています。追加のモジュールや要件があれば README を更新してください。