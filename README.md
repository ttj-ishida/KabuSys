# KabuSys

日本株自動売買システムのライブラリ（コアモジュール群）

バージョン: 0.1.0

概要
---
KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。本リポジトリは以下の主要機能を提供します。

- J-Quants API からの市場データ取得クライアント（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義と初期化
- 生データ保存（冪等な INSERT / ON CONFLICT 更新）
- 監査（audit）テーブルの初期化（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（自動 .env ロード機能）

主な特徴
---
- J-Quants クライアント設計
  - API レート制限の厳守（120 req/min、固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、408/429/5xx を対象
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して再試行（1回）
  - ページネーション対応かつページ間での id_token キャッシュ共有
  - データ取得時に fetched_at を UTC で記録して Look-ahead bias を防止
  - 取得したデータを DuckDB に冪等に保存するユーティリティ（ON CONFLICT）

- データベース / スキーマ
  - Raw / Processed / Feature / Execution 層を想定した DuckDB DDL を提供
  - インデックス定義、外部キー、チェック制約を含む堅牢なスキーマ
  - init_schema() により DB ファイル（または :memory:）を初期化
  - 監査用（audit）DDL と初期化関数を別モジュールで提供（UTC タイムゾーン強制）

- 設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み
  - 環境変数のパースはシェル形式のクォートやコメントに対応
  - 必須項目はアクセス時に ValueError を送出して明確化

セットアップ手順
---
前提
- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- pip / 仮想環境推奨

1. リポジトリをクローンし、仮想環境を作成・有効化する
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストールする
   - 必須: duckdb（その他は標準ライブラリ）
   ```
   pip install duckdb
   ```
   - 必要に応じてプロジェクトの requirements.txt を用意して pip install -r する

3. 環境変数を設定する
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

使い方（簡単な例）
---

1) settings による環境変数参照
```python
from kabusys.config import settings

print(settings.env)
print(settings.duckdb_path)
```

2) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = init_schema(settings.duckdb_path)
```

3) J-Quants から日足を取得して DuckDB に保存する
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
records = fetch_daily_quotes(code="7203")  # 銘柄コード（省略で全銘柄）
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

4) 財務データやマーケットカレンダーも同様に
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

5) 監査ログ（audit）テーブルの初期化
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で得た接続
init_audit_schema(conn)
```

環境変数一覧（主要）
---
必須（アクセス時に missing だと ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例: .env
```
JQUANTS_REFRESH_TOKEN="xxxxx"
KABU_API_PASSWORD="password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

ディレクトリ構成
---
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - audit.py                 — 監査ログ（signal / order_request / executions）初期化
  - strategy/
    - __init__.py              — 戦略モジュールプレースホルダ
  - execution/
    - __init__.py              — 発注実行モジュールプレースホルダ
  - monitoring/
    - __init__.py              — 監視モジュールプレースホルダ

開発メモ / 設計上の注意
---
- J-Quants クライアントは ID トークンを内部キャッシュし、必要に応じて自動でリフレッシュします。get_id_token() は明示的にリフレッシュするためにも使えます。
- データ保存は可能な限り冪等（ON CONFLICT DO UPDATE）を保っています。
- すべての時刻はできるだけ UTC で扱う設計です（fetched_at / created_at 等）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、テスト時や別パスでの実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化してください。

拡張 / 今後の作業
---
- strategy / execution / monitoring の実装を追加して、戦略生成→リスク管理→発注→約定のフルスタックを構成する
- Slack 通知や kabuステーション連携の実装
- CI テスト・型チェック・Lint の整備

お問い合わせ
---
利用・導入に関する質問やバグ報告はリポジトリの issue をご利用ください。