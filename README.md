# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けデータ基盤および補助モジュール群です。J-Quants API や RSS フィードから市場データ・財務データ・ニュースを収集し、DuckDB に冪等（idempotent）に保存、品質チェックやカレンダー管理、監査ログ用スキーマなどを提供します。将来的な戦略実装・発注実行・監視モジュールとの連携を想定した基盤ライブラリです。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を回避
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）
  - backfill による直近再取得（API の後出し修正吸収）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- RSS ニュース収集
  - RSS からニュース記事を収集し raw_news に保存（記事ID は正規化 URL の SHA-256 を利用）
  - SSRF や XML Bomb 対策（リダイレクト検査、defusedxml、受信サイズ制限）
  - 記事の前処理（URL除去・空白正規化）と銘柄コード抽出（既知コードとの照合）

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - DB 未取得時は曜日（週末）ベースのフォールバック

- 監査ログスキーマ（audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル群
  - order_request_id による冪等性、UTC タイムスタンプ固定、インデックス最適化

- データ品質チェック
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - チェック結果は QualityIssue オブジェクトで返却

---

## 必要条件 / 依存パッケージ（例）

下記は主要な依存パッケージの例です。実際はプロジェクトの packaging / requirements を参照してください。

- Python 3.10 以上（型注釈に PEP 604 などを想定）
- duckdb
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または requirements.txt がある場合:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-root>
```

2. 仮想環境作成・有効化（任意）
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール
```bash
pip install duckdb defusedxml
# プロジェクトがパッケージ化されていれば:
# pip install -e .
```

4. 環境変数 (.env) を用意する
プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

例: `.env`
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須となる環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（その他はデフォルト値あり）

5. DuckDB スキーマ初期化
Python REPL またはスクリプトからスキーマを初期化します（デフォルトで parent ディレクトリを自動作成）。

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ専用 DB を別に初期化する場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な例）

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェックを含む）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection, init_schema

conn = init_schema("data/kabusys.duckdb")  # または get_connection
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 株価差分 ETL の個別実行
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効銘柄コードのセット（例: {'7203','6758'}）
results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- 監査テーブルの初期化（既存接続へ追加）
```python
from kabusys.data.schema import init_schema
from kabusys.data import audit

conn = init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

---

## 環境変数の自動読み込み挙動

- パッケージの config モジュールは、`.git` または `pyproject.toml` を基準にプロジェクトルートを探索して `.env` / `.env.local` を自動読み込みします。
- 読み込み優先順位:
  - OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（主にテスト用）。
- 値の取得は `kabusys.config.settings` を経由します（必須変数が未設定の場合は ValueError）。

主要な設定プロパティ（settings）:
- jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
- kabu_api_password (KABU_API_PASSWORD)
- kabu_api_base_url (KABU_API_BASE_URL, デフォルト: http://localhost:18080/kabusapi)
- slack_bot_token (SLACK_BOT_TOKEN)
- slack_channel_id (SLACK_CHANNEL_ID)
- duckdb_path (DUCKDB_PATH, デフォルト: data/kabusys.duckdb)
- sqlite_path (SQLITE_PATH, デフォルト: data/monitoring.db)
- env (KABUSYS_ENV: development | paper_trading | live)
- log_level (LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL)

---

## 実装上の注意・設計ポイント

- J-Quants クライアントは 120 req/min のレート制御を実装（内部 RateLimiter）。
- リクエストは最大 3 回のリトライ（408 / 429 / 5xx）を行い、429 の場合は Retry-After を優先。
- 401 を受けた場合はリフレッシュトークンから id_token を再取得して 1 回だけリトライ。
- ニュース収集は SSRF 対策（リダイレクト先検査、プライベートIP拒否）、受信サイズ上限、defusedxml による XML 脆弱性対策を実施。
- DuckDB への INSERT は ON CONFLICT / RETURNING を活用して冪等性と挿入数の正確な把握を実現。
- 品質チェックは Fail-Fast ではなく全件収集（重大度に応じて呼び出し側で判断）。

---

## ディレクトリ構成

主要ファイル / モジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
    - news_collector.py     # RSS ニュース収集・保存・銘柄抽出
    - schema.py             # DuckDB スキーマ定義と初期化
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py# 市場カレンダー管理
    - audit.py              # 監査ログスキーマ（signal/order/execution）
    - quality.py            # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（strategy、execution、monitoring はプレースホルダとして存在し、戦略/発注/監視の実装が追加される想定です）

---

## 開発・テストメモ

- テスト実行時は `.env` 自動ロードを無効化したい場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。
- ネットワークや外部 API をモックしたい場合、各モジュール内のネットワーク呼び出し関数（例: news_collector._urlopen、jquants_client._request など）を差し替えることで容易にテスト可能です。
- DuckDB のインメモリ DB（":memory:"）を使えば副作用なしにテストできます：
  ```python
  conn = init_schema(":memory:")
  ```
- ログは標準 logging を利用しているため、呼び出し側でハンドラやログレベルを設定してください。

---

もし README にサンプル .env.example、CI の手順、またはパッケージ化の手順（pyproject.toml / setup.cfg）を追加したい場合は、その内容に合わせて追記できます。必要であれば実際の例やテンプレートを作成します。