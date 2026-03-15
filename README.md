# KabuSys

KabuSys は日本株向けの自動売買システム向け基盤ライブラリです。データ取得・永続化（DuckDB）・スキーマ管理・監査ログの初期化・J-Quants API クライアントなど、戦略実装や発注実装の下地となるユーティリティ群を提供します。

主な設計方針：
- Look-ahead bias の防止（取得時刻を UTC で記録）
- 冪等性（DuckDB への INSERT は ON CONFLICT DO UPDATE）
- API レート制御（J-Quants: 120 req/min）
- リトライ（指数バックオフ、401 時はトークン自動リフレッシュ）

---

## 機能一覧

- 環境変数 / .env 管理
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動読み込み（無効化可能）
  - 必須値は Settings クラス経由で取得（未設定時は例外）
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - ページネーション対応、レート制限（固定間隔）、再試行（408/429/5xx）、401 時はトークン自動更新
  - DuckDB への保存用ユーティリティ（idempotent な保存関数）
- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、init_schema / get_connection API
- 監査ログ（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定を UUID 連鎖でトレース可能にする監査テーブル群
  - init_audit_schema / init_audit_db
- パッケージ構造のための初期 __init__ モジュール群

---

## 要求事項 / 前提

- Python 3.10 以上（型記法に Python 3.10 の構文 | を使用）
- 必要パッケージ（最低限）:
  - duckdb
- 他の依存は標準ライブラリ（urllib, json, logging 等）

pip 用の requirements ファイルがない場合は手動でインストールしてください:
```
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.\.venv\Scripts\activate    # Windows
pip install duckdb
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを取得
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール（例: duckdb）
4. 環境変数を用意（.env または OS 環境変数）

推奨 .env の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知など)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development       # development | paper_trading | live
LOG_LEVEL=INFO
```

自動で .env を読み込ませたくない場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本例）

以下は代表的なワークフロー例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は設定値（Path）を返す
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日次株価を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# トークンは内部で settings.jquants_refresh_token を使って自動取得/リフレッシュされます
records = fetch_daily_quotes(code="7203")  # 例: トヨタ (コード 7203)
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

3) 財務データ / カレンダーの取得も同様
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar
fin = fetch_financial_statements(code="7203")
save_count = save_financial_statements(conn, fin)

calendar = fetch_market_calendar()
save_count = save_market_calendar(conn, calendar)
```

4) 監査ログの初期化（既存の DuckDB 接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

監査ログを専用 DB に作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意:
- fetch_* 系関数はページネーションに対応し、モジュールレベルで id_token をキャッシュします。
- _request 内でレート制御（120 req/min）、リトライ（最大 3 回）、401 の自動リフレッシュを実装しています。
- save_* 関数は ON CONFLICT DO UPDATE により冪等にデータを書き込みます。

---

## 設定項目（環境変数）

主な環境変数（Settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)
  - development | paper_trading | live（小文字可）
- LOG_LEVEL (任意)
  - DEBUG | INFO | WARNING | ERROR | CRITICAL

未設定の必須値を Settings で参照すると ValueError が発生します。

---

## スキーマ / ディレクトリ構成

プロジェクトルートの主要ファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（取得・保存）
    - schema.py               # DuckDB スキーマ定義 / init_schema
    - audit.py                # 監査ログテーブル（signal_events, order_requests, executions）
- README.md (このファイル)

主要なテーブル（DuckDB）概要:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査テーブル: signal_events, order_requests, executions
- 典型的なインデックスも定義済み（頻出クエリに最適化）

---

## 実装上の注意点 / 運用メモ

- 全ての TIMESTAMP は UTC で扱うことを想定しています（監査ログ初期化時に SET TimeZone='UTC' を実行）。
- J-Quants のレート制限（120 req/min）を守るため固定間隔スロットリングを実装しています。高頻度取得は注意してください。
- 401 エラー発生時はトークン自動更新を行い 1 回リトライします。get_id_token は必要に応じて明示的に呼び出せます。
- .env ファイルのパースは Bash 風のクォートやコメントをある程度サポートしますが、複雑な構成は OS 環境変数で渡す方が確実です。
- DuckDB のスキーマ初期化は冪等です。すでに存在するテーブルは上書きされません。

---

## 拡張 / 次のステップ（例）

- strategy 層に戦略実装を追加して signal_events を書き出す
- execution 層で order_requests を発行し、signal_queue / orders / trades を連携
- monitoring 用に SQLite（SQLITE_PATH）や Slack 通知の実装を追加
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して環境依存を排除する

---

ご不明な点や README に追加したい利用例・導入手順があれば教えてください。必要であれば具体的なコード例（戦略テンプレート・発注フロー）も作成します。