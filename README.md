# KabuSys

日本株向けの自動売買基盤のコアライブラリ（モジュール群）。  
データ取得（J-Quants）、データベーススキーマ（DuckDB）、監査ログ（発注→約定のトレーサビリティ）など、トレーディングシステムの基盤処理を提供します。

---

## 特長（概要 / 設計方針）
- J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー）
  - API レート制限（120 req/min）を守る固定間隔スロットリング
  - 冪等性・ページネーション対応
  - リトライ（指数バックオフ、対象: 408/429/5xx）、401 を受けた際にはトークン自動リフレッシュ
  - fetched_at を UTC で記録して Look-ahead Bias を防止
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）を提供して初期化可能
- 監査ログ（signal_events / order_requests / executions）でシグナルから約定までを UUID 連鎖でトレース可能
- 環境変数管理モジュール（.env の自動読み込み、必要キーの検査、環境モード）
- ローカル開発 / ペーパートレード / 本番（live）を区別する設定

---

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 必須環境変数チェック、KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) — 全テーブル・インデックスを作成
  - get_connection(db_path) — 既存 DB への接続を取得
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) — 既存接続に監査テーブルを追加
  - init_audit_db(db_path) — 監査専用 DB を初期化して接続を返す

---

## 必要条件
- Python 3.10+
- duckdb Python パッケージ
- （ネットワーク経由の API 呼び出しに urllib を使用。追加の外部パッケージは限定的。）

pip 例:
```bash
python -m pip install "duckdb"
```

（プロジェクト全体の requirements.txt があればそちらを利用してください。）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb など）
4. .env を用意（下記参照）
5. DuckDB スキーマを初期化

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# .env を作成してから
python -c "from kabusys.data import schema; from kabusys.config import settings; schema.init_schema(settings.duckdb_path)"
```

自動 .env 読み込みは、パッケージ内の config が起動時にプロジェクトルートを検出して行います。無効化するには環境変数を設定:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 環境変数（主なもの / .env.example）
必須キー:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意／デフォルト:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の読み込み優先順:
OS 環境変数 > .env.local > .env

プロジェクトルートが特定できない場合（.git / pyproject.toml が見つからない）は自動読み込みをスキップします。

---

## 使い方（主要な API 例）

1) 設定を使う
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)    # 未設定なら ValueError
print(settings.duckdb_path)              # Path オブジェクト
```

2) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# 初期化（ファイルがなければ親ディレクトリを作成）
conn = schema.init_schema(settings.duckdb_path)
# もしくは既存 DB へ接続（初回は init_schema を推奨）
conn2 = schema.get_connection(settings.duckdb_path)
```

3) J-Quants から取得して保存する（株価日足の例）
```python
from kabusys.data.jquants_client import (
    get_id_token, fetch_daily_quotes, save_daily_quotes
)
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)

# トークン取得（内部で settings.jquants_refresh_token を使う）
id_token = get_id_token()

# 銘柄コードや日付を指定して取得（ページネーション対応）
from datetime import date
recs = fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB に保存（ON CONFLICT DO UPDATE により冪等）
n = save_daily_quotes(conn, recs)
print(f"保存件数: {n}")
```

4) 監査ログ初期化
```python
from kabusys.data import audit
from kabusys.data import schema
from kabusys.config import settings

# 既存のスキーマ接続に監査テーブルを追加
conn = schema.get_connection(settings.duckdb_path)
audit.init_audit_schema(conn)

# または監査専用 DB を初期化
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 実装上の注意点 / 動作仕様
- J-Quants クライアントはモジュールレベルで ID トークンをキャッシュし、ページネーション間で使い回します。401 を受けると自動で一度だけリフレッシュして再試行します。
- レートリミット: 120 req/min を固定間隔で守るようにスロットリング（単純実装）。連続短時間実行時は内部で sleep します。
- リトライ: ネットワークエラーや HTTP 408/429/5xx に対して最大 3 回（指数バックオフ）で再試行します。429 の場合は Retry-After ヘッダを優先します。
- DuckDB への保存関数は重複を上書きする（ON CONFLICT DO UPDATE）ので再実行しても安全（冪等）。
- 監査ログは削除しない前提で設計され、すべての TIMESTAMP は UTC で保存します（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py             — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存ロジック）
    - schema.py           — DuckDB スキーマ定義・初期化
    - audit.py            — 監査ログ（signal / order_request / execution）
    - (その他: audit 初期化等)
  - strategy/
    - __init__.py         — 戦略関連（未実装プレースホルダ）
  - execution/
    - __init__.py         — 発注/約定実装（未実装プレースホルダ）
  - monitoring/
    - __init__.py         — 監視周り（未実装プレースホルダ）

---

## 開発上の補足
- Python の型アノテーションに最近の構文（|）を使用しています。Python 3.10 以上を推奨します。
- .env パーサはシングル/ダブルクォート内のエスケープを考慮し、コメントの扱い（クォートの有無での振る舞い）に注意しています。
- 本リポジトリはコア基盤を提供するため、実際の戦略・ブローカー連携・Slack 通知などは利用側で実装／統合してください。

---

必要であれば README に以下を追加できます:
- CI / テスト実行方法
- 開発用 Docker コンテナ定義
- より詳細な API リファレンス（各関数の引数/戻り値の表）
- サンプルワークフロー（データ取得→特徴量生成→シグナル生成→発注）