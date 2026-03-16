# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム向けライブラリです。  
J-Quants API や kabuステーション API と連携してデータ取得、DuckDB による永続化、ETL、品質チェック、監査ログを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価（日足）、財務データ、マーケットカレンダーを取得して DuckDB に保存する。
- 差分 ETL（最終取得日からの差分取得、一定日数のバックフィル）を提供する。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行する。
- 発注／約定の監査トレース用スキーマを含む監査ログ管理を行う。
- 将来的に戦略層・実行層・モニタリングと統合するためのパッケージ骨子を提供する。

設計上の特徴:

- API レート制限（120 req/min）遵守のためのレートリミッタ搭載
- リトライ（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 監査ログは UUID 連鎖でトレース可能、TIMESTAMP は UTC で保存

---

## 機能一覧

- 環境設定管理
  - .env を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須環境変数の検査メソッドを提供
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

- データ取得（data.jquants_client）
  - 日足 (OHLCV) / 財務データ（四半期 BS/PL）/ JPX マーケットカレンダーの取得
  - ページネーション対応・トークンキャッシュ・リトライ・レート制御

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - テーブル・インデックスの自動作成（冪等）
  - init_schema / get_connection API

- ETL（data.pipeline）
  - 日次 ETL（カレンダー先読み → 株価差分取得 → 財務差分取得 → 品質チェック）
  - 差分更新ロジック / backfill / lookahead オプション
  - ETL 実行結果を表す ETLResult（品質問題やエラーを集約）

- データ品質チェック（data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比の変動閾値）
  - 主キー重複検出
  - 日付不整合（未来日付、非営業日のデータ）
  - 全チェックをまとめて実行する run_all_checks

- 監査ログ（data.audit）
  - シグナル → 発注要求 → 実行 の監査テーブル（UUID、冪等キー）
  - 発注要求のステータス管理用スキーマおよびインデックス
  - init_audit_schema / init_audit_db

- 将来的な拡張ポイント
  - strategy、execution、monitoring パッケージのプレースホルダ（拡張予定）

---

## セットアップ手順

想定環境: Python 3.10 以上

依存ライブラリ（最小）:

- duckdb
- （標準ライブラリのみで他の依存は現状不要）

例: 仮想環境を作成して依存をインストールする

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発中であればプロジェクトを editable install:
# pip install -e .
```

環境変数: 以下は必須／任意の変数一覧（.env に記述しておくと自動読み込みされます）

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（API 実行時に使用）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知の送信先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

自動読み込みの挙動:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探し、`.env` を読み込みます。
- `.env.local` があれば `.env` の上書きとして読み込みます（OS 環境変数は保護され上書きされません）。
- 自動読み込みを無効にする: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

簡単な .env.example:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（例）

以下は代表的な利用シナリオの例です。Python スクリプトや REPL から実行できます。

1) DuckDB スキーマを初期化する

```python
from kabusys.data.schema import init_schema

# ファイル DB を作る（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) J-Quants API の ID トークンを取得する（内部で settings.jquants_refresh_token を使用）

```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()
print(token)
```

3) 日次 ETL を実行する（市場カレンダー先読み → 株価・財務取得 → 品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date や backfill_days を指定可
print(result.to_dict())
```

4) 監査スキーマを追加で初期化する（既存の conn を使う）

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で取得した DuckDB 接続
init_audit_schema(conn)
```

5) 品質チェックだけを実行する

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

ログレベルや環境切り替えは環境変数 `KABUSYS_ENV`、`LOG_LEVEL` で制御します。

---

## 主要 API 概要

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / sqlite_path
  - settings.env / settings.log_level / settings.is_live など

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ構成（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py  -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py          -- DuckDB スキーマ定義・初期化
      - pipeline.py        -- ETL パイプライン
      - audit.py           -- 監査ログスキーマ
      - quality.py         -- データ品質チェック
    - strategy/
      - __init__.py        -- 戦略関連（拡張ポイント）
    - execution/
      - __init__.py        -- 発注実行関連（拡張ポイント）
    - monitoring/
      - __init__.py        -- モニタリング関連（拡張ポイント）

---

## 運用上の注意・補足

- J-Quants API のレート制限（120 req/min）に合わせた実装が組み込まれていますが、長時間大量リクエストを行う用途では実運用の追加制御が必要になる場合があります。
- ETL は個々のステップで例外を捕捉して続行する設計です（Fail-Fast ではなく、問題を収集して呼び出し元で判断）。ログと ETLResult を確認してください。
- DuckDB のファイルはバックアップやローテーションを適切に行ってください。:memory: もサポートしていますが永続化されません。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）です。削除要件がある場合は別途検討してください。
- timezone は監査ログ初期化で UTC に設定されます。実データの保存時も UTC を意識してください。

---

もし README に含めたい追加情報（例: CI、テスト、実行用の CLI、Docker イメージ、詳しい .env.example、運用チェックリストなど）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追記します。