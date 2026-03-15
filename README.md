# KabuSys

KabuSys は日本株向けの自動売買基盤（ライブラリ）です。データ取得、永続化（DuckDB）、監査ログ、戦略・発注レイヤのためのスキーマを備え、J-Quants API などから市場データを取得して保存するためのユーティリティを提供します。

バージョン: 0.1.0

---

## 主な特徴（概要）

- J-Quants API クライアントを内蔵
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レートリミット（120 req/min）を遵守する固定間隔スロットリング
  - 再試行（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録（Look-ahead bias 対策）
- DuckDB を用いた永続化用スキーマ
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - 監査ログ用テーブル（signal_events / order_requests / executions）を別途初期化可能
  - 冪等性を考慮した INSERT（ON CONFLICT DO UPDATE）を採用
- 環境変数管理
  - プロジェクトルートの .env / .env.local を自動読み込み（必要に応じて無効化可）
  - 必須環境変数未設定時は例外を投げて明示
- モジュール構成は data / strategy / execution / monitoring（実装を拡張可能）

---

## 機能一覧（抜粋）

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- data.schema
  - init_schema(db_path) — DuckDB スキーマ初期化（全テーブル）
  - get_connection(db_path) — 既存 DB への接続取得
- data.audit
  - init_audit_schema(conn) — 監査ログテーブルを既存接続に追加
  - init_audit_db(db_path) — 監査ログ専用 DB の初期化
- config
  - settings — 環境変数経由の設定（JQUANTS_REFRESH_TOKEN 等）

---

## 必要条件 / 依存パッケージ

- Python 3.10+（typing の | 記法を使用）
- duckdb

インストール例（仮に pyproject.toml がある場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発中はパッケージを編集可能インストール
pip install -e .
```

（パッケージ配布方法により pip install コマンドは変わります）

---

## 環境変数（必須 / 推奨）

必須（アクセス時に settings が参照すると例外になります）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用など）パス（デフォルト: data/monitoring.db）

.env 自動読み込み:
- パッケクトの起点（src/kabusys/config.py の位置から親ディレクトリを辿り、.git または pyproject.toml を検出）をプロジェクトルートと見なし、ルート/.env とルート/.env.local を読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などで利用）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
2. 依存パッケージをインストール（上記参照）
3. プロジェクトルートに .env または .env.local を作成し、必要な環境変数を設定
   - 例 (.env.example として):
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
4. DuckDB スキーマを初期化:
   - Python REPL またはスクリプトで下記を実行（例）:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     ```
5. （必要に応じて）監査ログを初期化:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（コード例）

- J-Quants から株価日足を取得して保存する例:
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client
from kabusys.data import schema
from kabusys.config import settings

# DB 初期化（初回）
conn = schema.init_schema(settings.duckdb_path)

# データ取得
records = jquants_client.fetch_daily_quotes(
    date_from=date(2024, 1, 1),
    date_to=date(2024, 1, 31),
)

# 保存（冪等）
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"挿入/更新件数: {inserted}")
```

- 財務データやマーケットカレンダーも同様:
```python
fin = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, fin)

cal = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, cal)
```

- ID トークン取得（明示的にリフレッシュしたい場合）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 監査ログ専用 DB を作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は executions/order_requests 等が作成済み
```

注意点:
- jquants_client の HTTP 層は urllib を使用し、内部でレート制御・リトライ・401 リフレッシュを行います。
- save_* 系は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取り、ON CONFLICT DO UPDATE により冪等に保存します。
- すべてのタイムスタンプは UTC を意図しています（監査ログ初期化時に SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

以下は主要ファイルのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数／設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント / データ保存
      - schema.py              — DuckDB スキーマ定義と初期化
      - audit.py               — 監査ログ（トレーサビリティ）定義
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py            — 戦略層（拡張ポイント）
    - execution/
      - __init__.py            — 発注実行層（拡張ポイント）
    - monitoring/
      - __init__.py            — 監視／メトリクス（拡張ポイント）

（README の作成時点では strategy / execution / monitoring モジュールはインターフェースの土台が用意されています。実際の戦略ロジックやブローカ接続はプロジェクト側で実装してください。）

---

## 設計に関する補足

- レート制限:
  - J-Quants の仕様に合わせて 120 req/min（最小間隔 = 60 / 120 秒）でスロットリングしています。
- リトライ:
  - 最大 3 回、408/429/5xx に対して指数バックオフを行います。429 の場合は Retry-After ヘッダを優先します。
- トークン管理:
  - id_token はモジュールレベルでキャッシュされ、401 を受けた場合は 1 回だけリフレッシュして再試行します。
- データのトレーサビリティ:
  - 生データには fetched_at を付与し、「いつそのデータを知り得たか」を明示的に残します。
- 冪等性:
  - DuckDB 側は PRIMARY KEY / ON CONFLICT DO UPDATE を用いて冪等的なデータ取り込みを実現します。

---

## 今後の拡張ポイント

- strategy モジュールに戦略クラスの実装（バージョン管理、シグナル生成）
- execution モジュールに証券会社 API 連携（kabu ステーション等）
- monitoring モジュールでメトリクス収集・アラート（Slack 連携）
- テストスイート・CI の整備

---

ライセンスや貢献方法などはリポジトリのルートに別途追記してください。何か追加してほしい情報（例: CI 設定、実際の発注ワークフロー例など）があれば教えてください。