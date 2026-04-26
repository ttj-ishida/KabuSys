# J-Quants Bootstrap 実装設計書

**Goal:** J-Quants Bulk Download API を使って初回環境構築時に大量のヒストリカルデータを一括投入し、バックテスト・通常運用が即座に開始できる状態にする。

**Architecture:** Bulk API でファイルリストを取得 → presigned URL 経由で gzip CSV をダウンロード → ローカルキャッシュに保存 → parse & upsert → bootstrap_load_history に処理状態記録。冪等・再実行安全。

**Tech Stack:** Python 3.10+, httpx, DuckDB, gzip/csv stdlib

---

## 1. 対象データ

| Bulk エンドポイント         | Raw テーブル      | Processed テーブル | 備考                        |
| -------------------------- | ----------------- | ------------------ | --------------------------- |
| `/equities/bars/daily`     | `raw_prices`      | `prices_daily`     | AdjFactor を raw に保存     |
| `/equities/master`         | —                 | `stocks`           | 最新日のみ取得              |
| `/fins/summary`            | `raw_financials`  | `fundamentals`     | DiscDate → report_date      |
| `/markets/calendar`        | —                 | `market_calendar`  | HolDiv で is_trading_day 判定|
| `/fins/dividend`           | —                 | `dividends`        | 新規テーブル                |
| `/indices/bars/daily/topix`| —                 | `topix_daily`      | 新規テーブル・regime 用     |

---

## 2. スキーマ変更

### 2-1. `raw_prices` に `adj_factor` 列を追加

```sql
ALTER TABLE raw_prices ADD COLUMN IF NOT EXISTS adj_factor DECIMAL(18,6);
```

Bulk CSV の `AdjFactor` を保存する。差分 API 経由の行は NULL。

### 2-2. `dividends` テーブル（新規）

```sql
CREATE TABLE IF NOT EXISTS dividends (
    code         VARCHAR   NOT NULL,
    pub_date     DATE      NOT NULL,
    ref_no       VARCHAR   NOT NULL,
    ex_date      DATE,
    record_date  DATE,
    pay_date     DATE,
    div_rate     DECIMAL(18,4),
    fetched_at   TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (code, pub_date, ref_no)
)
```

Bulk CSV マッピング: `Code→code, PubDate→pub_date, RefNo→ref_no, ExDate→ex_date, RecDate→record_date, PayDate→pay_date, DivRate→div_rate`

### 2-3. `topix_daily` テーブル（新規）

```sql
CREATE TABLE IF NOT EXISTS topix_daily (
    date   DATE          NOT NULL PRIMARY KEY,
    open   DECIMAL(18,4) NOT NULL,
    high   DECIMAL(18,4) NOT NULL,
    low    DECIMAL(18,4) NOT NULL,
    close  DECIMAL(18,4) NOT NULL
)
```

Bulk CSV マッピング: `Date→date, O→open, H→high, L→low, C→close`

### 2-4. `bootstrap_load_history` テーブル（新規）

```sql
CREATE TABLE IF NOT EXISTS bootstrap_load_history (
    file_key   VARCHAR   NOT NULL PRIMARY KEY,
    endpoint   VARCHAR   NOT NULL,
    file_name  VARCHAR   NOT NULL,
    status     VARCHAR   NOT NULL DEFAULT 'pending',
    row_count  BIGINT,
    error_msg  VARCHAR,
    loaded_at  TIMESTAMP
)
```

status 遷移: `pending → loaded`（成功）/ `pending → failed`（エラー）

---

## 3. モジュール構成

```
src/kabusys/data/bootstrap/
├── __init__.py          — 公開 API: run_bootstrap()
├── bulk_client.py       — Bulk API クライアント（list / get / download）
├── loaders.py           — エンドポイント別 parse & upsert
└── runner.py            — オーケストレーション + CLI
```

### 3-1. `bulk_client.py`

```python
BASE_URL = "https://api.jquants.com/v2"

def list_files(endpoint: str, api_key: str) -> list[dict]:
    """GET /v2/bulk/list?endpoint=<ep> → [{key, date, ...}, ...]"""

def get_presigned_url(file_key: str, api_key: str) -> str:
    """GET /v2/bulk/get?key=<key> → presigned URL（有効期限5分）"""

def download_file(presigned_url: str, dest: Path) -> Path:
    """presigned URL → gzip CSV をローカルに保存"""
```

認証: すべてのリクエストに `headers={"x-api-key": api_key}` を付与。

### 3-2. `loaders.py`

各エンドポイントに対応する `load_<name>(conn, csv_path) -> int` 関数を実装。

```python
def load_prices(conn, csv_path: Path) -> int:
    """equities/bars/daily CSV → raw_prices & prices_daily"""

def load_master(conn, csv_path: Path) -> int:
    """equities/master CSV → stocks"""

def load_financials(conn, csv_path: Path) -> int:
    """fins/summary CSV → raw_financials & fundamentals"""

def load_calendar(conn, csv_path: Path) -> int:
    """markets/calendar CSV → market_calendar"""

def load_dividend(conn, csv_path: Path) -> int:
    """fins/dividend CSV → dividends"""

def load_topix(conn, csv_path: Path) -> int:
    """indices/bars/daily/topix CSV → topix_daily"""
```

共通処理:
- `gzip.open(csv_path, "rt", encoding="utf-8")` で読み込み
- チャンクサイズ 10,000 行でバッファリング
- 全列に `ON CONFLICT ... DO UPDATE SET` で冪等 upsert
- PK 欠損行はスキップしてログ警告

### 3-3. `runner.py`

```python
ENDPOINTS = [
    "/equities/bars/daily",
    "/equities/master",
    "/fins/summary",
    "/markets/calendar",
    "/fins/dividend",
    "/indices/bars/daily/topix",
]

def run_bootstrap(
    conn: duckdb.DuckDBPyConnection,
    api_key: str,
    raw_dir: Path = Path("data/bootstrap/raw"),
    dry_run: bool = False,
) -> BootstrapResult:
    """全エンドポイントを順次処理する。1ファイル失敗でも継続。"""
```

オーケストレーション:
1. `bootstrap_load_history` で `status='loaded'` のファイルはスキップ
2. `list_files()` でファイルキー一覧を取得
3. ローカルキャッシュ（`raw_dir/<endpoint>/`）があればダウンロードをスキップ
4. `get_presigned_url()` + `download_file()` でダウンロード
5. `load_<name>()` で DuckDB に投入
6. `bootstrap_load_history` に `loaded / failed` を記録

---

## 4. 設定

`Settings` クラスに追加:

```python
@property
def jquants_bulk_api_key(self) -> str:
    return _require("JQUANTS_BULK_API_KEY")
```

`config_setup.py` の `_ITEMS` に追加:

```python
{
    "key": "JQUANTS_BULK_API_KEY",
    "label": "J-Quants Bulk Download API キー",
    "secret": True,
    "description": "  J-Quants ダッシュボード → 設定 → APIキー から取得",
}
```

---

## 5. CLI

```bash
# 全エンドポイントを bootstrap
python -m kabusys.data.bootstrap

# ドライラン（ダウンロードせず件数確認のみ）
python -m kabusys.data.bootstrap --dry-run

# 特定エンドポイントのみ
python -m kabusys.data.bootstrap --endpoint /equities/bars/daily

# raw_dir を指定
python -m kabusys.data.bootstrap --raw-dir /mnt/data/bootstrap/raw
```

完了後に以下のサマリーを出力:

```
Bootstrap 完了サマリー
  /equities/bars/daily     : 1,234,567 件 (110 ファイル)
  /equities/master         :     4,321 件 (1 ファイル)
  /fins/summary            :   456,789 件 (32 ファイル)
  /markets/calendar        :     3,650 件 (1 ファイル)
  /fins/dividend           :    89,012 件 (8 ファイル)
  /indices/bars/daily/topix:     2,500 件 (1 ファイル)
  失敗ファイル: 0
```

---

## 6. 冪等性・エラー処理

| シナリオ | 対処 |
| --- | --- |
| 同じファイルを再実行 | `bootstrap_load_history.status = 'loaded'` なのでスキップ |
| ローカルキャッシュあり | ダウンロードせず直接 load |
| DuckDB upsert 重複 | `ON CONFLICT DO UPDATE` で上書き |
| 1ファイルでパースエラー | `failed` 記録 → 次ファイルに継続 |
| presigned URL 期限切れ | 再取得して retry（最大3回） |
| DuckDB 接続エラー | 即時 raise（呼び出し元でハンドリング） |

---

## 7. テスト方針

- `test_bulk_client.py`: `httpx` をモックして list / get / download をテスト
- `test_loaders.py`: tmp_path に小さな gzip CSV を置き、DuckDB への投入件数・スキーマを検証
- `test_runner.py`: `bulk_client` をモックし、履歴テーブルへの記録・スキップロジックをテスト

---

## 8. 完了条件（Issue #187 との対応）

| Issue 完了条件 | 実装対応 |
| --- | --- |
| J-Quants CSV を安全に一括投入できる | Bulk API + loaders で全6種対応 |
| 通常の日次差分更新と責務が分離される | `kabusys.data.bootstrap` は独立モジュール |
| 途中失敗しても再実行で安全にリトライできる | `bootstrap_load_history` + スキップロジック |
| bootstrap 完了後に通常運用へ移行できる | `prices_daily` 等が埋まるため即座に移行可能 |
