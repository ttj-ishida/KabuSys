# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ／ツール群です。  
J-Quants API や RSS を利用したデータ収集、DuckDB ベースのスキーマ、ETL パイプライン、品質チェック、カレンダー管理、ニュース収集、監査ログ（オーダー〜約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応の固定間隔スロットリング
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
  - データ取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のスキーマを定義
  - インデックスや制約を含む冪等な初期化関数（init_schema）
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）

- ETL パイプライン
  - 差分取得（最終取得日からの差分・backfill 対応）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集（RSS）
  - RSS から記事を取得して raw_news に保存
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性を担保
  - SSRF 対策、受信サイズ制限、gzip 対応、defusedxml による XML 攻撃対策
  - 銘柄コード抽出と news_symbols への紐付け

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ、営業日判定・前後営業日検索など

- データ品質チェック
  - 欠損、スパイク、重複、将来日付 / 非営業日データ検出
  - QualityIssue オブジェクトで詳細を返す（severity: error/warning）

---

## 必要条件 / 依存

- Python 3.10+
  - コード中で `|` 型注釈等を使用しているため Python 3.10 以上を想定
- 必要パッケージ（一例）
  - duckdb
  - defusedxml
- 開発環境では setuptools / poetry 等を用意してください

インストール（ローカル開発例）:
```bash
# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate

# 必要パッケージをインストール
pip install duckdb defusedxml
# パッケージを editable インストール（プロジェクトルートで）
pip install -e .
```

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージ位置から `.git` または `pyproject.toml` を探索）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（Settings で参照）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — environment: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意: 必須キーは Settings のプロパティアクセス時に ValueError が発生します。`.env.example` を参照して `.env` を用意してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
2. 依存をインストール（duckdb, defusedxml など）
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

例:
```bash
# 仮想環境
python -m venv .venv
source .venv/bin/activate

# 依存インストール
pip install duckdb defusedxml

# .env を作成 (エディタで JQUANTS_REFRESH_TOKEN 等を設定)
cp .env.example .env
# EDIT .env as needed

# パッケージをローカルインストール（任意）
pip install -e .
```

DuckDB スキーマ初期化（Python から）:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

監査ログ専用 DB の初期化:
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

または既存接続に監査テーブルを追加する:
```python
from kabusys.data import audit
# conn は schema.init_schema の返り値など
audit.init_audit_schema(conn)
```

---

## 使い方（主要ユースケース）

以下は代表的な呼び出し例です。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡すことも可能
print(result.to_dict())
```

オプション例:
- run_daily_etl(..., run_quality_checks=False)
- run_daily_etl(..., backfill_days=5, spike_threshold=0.6)

- 個別 ETL ジョブ
  - 株価 ETL:
    from kabusys.data.pipeline import run_prices_etl
  - 財務 ETL:
    from kabusys.data.pipeline import run_financials_etl
  - カレンダー ETL:
    from kabusys.data.pipeline import run_calendar_etl

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出用の set[str]（省略可）
result = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(result)  # {source_name: saved_count, ...}
```

- J-Quants から日次株価を直接取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
```

- カレンダーの営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_trading_day(conn, date(2024,1,1))
next_trading_day(conn, date(2024,1,1))
```

---

## 運用上の注意

- J-Quants API のレート制御（120 req/min）とリトライロジックが組み込まれていますが、運用時にも過剰リクエストにならないよう注意してください。
- get_id_token はリフレッシュトークンから ID トークンを取得します。token の漏洩に注意し、`.env` を安全に管理してください。
- ニュース収集は外部 URL をダウンロードするため SSRF 対策や受信サイズ制限等の保護が組み込まれています。テスト時は _urlopen をモックできます（news_collector._urlopen を差し替え）。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップや排他アクセスに注意してください（同時書き込みなど）。

---

## ディレクトリ構成

プロジェクトの主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース取得・保存
    - schema.py               -- DuckDB スキーマ定義・初期化
    - pipeline.py             -- ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py  -- 市場カレンダー管理・営業日ユーティリティ
    - audit.py                -- 監査ログ（order_requests / executions 等）
    - quality.py              -- データ品質チェック
  - strategy/
    - __init__.py             -- 戦略モジュールのトップ（未実装領域のエントリ）
  - execution/
    - __init__.py             -- 発注 / ブローカー連携（未実装領域のエントリ）
  - monitoring/
    - __init__.py             -- 監視用モジュール（未実装領域のエントリ）

README に載せきれない細かい仕様は各モジュールの docstring を参照してください。API の挙動（例: ETL の backfill、news_collector の SSRF 対策、jquants_client のリトライ条件など）はソースコメントで詳細に説明しています。

---

## 追加情報 / 開発者向けメモ

- 自動 .env 読み込みはパッケージ実行時に働きます。テストから環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境をロードしてください。
- DuckDB の接続オブジェクトはそのまま渡して処理を行います。トランザクション制御は各モジュール内で適切に行われています（news_collector の save_raw_news など）。
- 品質チェックは Fail-Fast にはしていないため、問題を検出しても ETL を継続して情報を収集します。呼び出し側で結果（QualityIssue の severity）に応じたアクションを実装してください。

---

不明点や追加で欲しい情報（例: CLI コマンドの例、Docker イメージ化手順、より詳細な .env.example）などがあれば教えてください。README を拡張して用意します。