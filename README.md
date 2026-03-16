# KabuSys — 日本株自動売買システム

軽量なデータ基盤とETL、監査ログを備えた日本株向け自動売買システムのライブラリ群です。J-Quants API / kabuステーション等と連携して、市場データの取得・保存・品質チェック・監査ログ記録までをサポートすることを目的としています。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 主な機能

- 環境変数・設定管理
  - `.env` / `.env.local` からの自動ロード（プロジェクトルート検出）
  - 必須設定の取得・バリデーション（J-Quants トークン、kabuAPI パスワード、Slack トークンなど）
- J-Quants API クライアント（data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）と 401 発生時の自動トークンリフレッシュ
  - ページネーション対応、fetched_at による取得時刻記録（UTC）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義・初期化（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - スキーマ初期化関数 `init_schema`、接続取得 `get_connection`
- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日ベース）、バックフィル、calendar の先読み
  - ETL の個別実行（prices / financials / calendar）および日次一括実行 `run_daily_etl`
  - 品質チェック（data.quality と連携）結果を含む ETLResult を返す
- 監査ログ（data.audit）
  - signal → order_request → execution をUUIDで追跡する監査テーブル群
  - 発注の冪等性（order_request_id）やタイムスタンプ(UTC)ポリシーを実装
- データ品質チェック（data.quality）
  - 欠損（OHLC 欠測）、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日）の検出
  - 各チェックは `QualityIssue` を返し、呼び出し元で重大度に応じた対応が可能

※ strategy / execution / monitoring パッケージはプレースホルダ（将来の戦略実装、発注ロジック、監視機能）用に用意されています。

---

## 必要要件

- Python 3.10+
- duckdb
- 標準ライブラリの urllib, json, logging など

（パッケージは外部ライブラリ duckdb を利用します。その他の依存は現状標準ライブラリ中心です。）

---

## インストール

開発環境で利用する場合（リポジトリ直下で）:

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb

3. 開発インストール（オプション）
   - pip install -e .

---

## 設定（環境変数）

config モジュールはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）から自動的に `.env` / `.env.local` を読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID — Slack チャンネルID

任意:
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## クイックスタート（例）

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査ログテーブル初期化（既存接続へ追加）
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
```

3) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)

print(result.to_dict())  # ETL 結果と品質チェックのサマリ
```

4) J-Quants から日足を直接取得して保存する（テスト用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

---

## API のポイント（実装上の注意）

- jquants_client
  - レート制限: 120req/min を守るため固定間隔スロットリングを行います。
  - リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフ（最大3回）。
  - 401 エラーはトークンを自動的にリフレッシュしてもう一度だけリトライします。
  - 取得データは fetched_at を UTC ISO8601 タイムスタンプで付与して保存し、Look-ahead Bias を防ぎます。
- schema.init_schema は idempotent（既存テーブルがあればそのまま）です。
- pipeline.run_daily_etl は個別ステップ（calendar, prices, financials, quality）を独立して実行し、片方が失敗しても他は継続します。結果として ETLResult を返し、errors・quality_issues を確認できます。

---

## 使い方のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、明示的に設定を注入して挙動を安定させることができます。
- DuckDB のパスに `:memory:` を渡すとインメモリ DB になります（ユニットテストに便利）。
- ETL の差分計算は DB 内の最終取得日を参照するため、初回は過去の開始日（デフォルト 2017-01-01）からロードされます。
- 品質チェックの閾値（スパイク検出など）は pipeline.run_daily_etl の引数で調整可能です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/  (発注ロジック用パッケージ - 現状プレースホルダ)
      - __init__.py
    - strategy/   (戦略用パッケージ - 現状プレースホルダ)
      - __init__.py
    - monitoring/ (監視用パッケージ - プレースホルダ)
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（取得・保存ロジック）
      - schema.py             # DuckDB スキーマ定義・初期化
      - pipeline.py           # ETL パイプライン
      - audit.py              # 監査ログ（signal/order_request/executions）
      - quality.py            # データ品質チェック

---

## 開発・貢献

- テスト: DuckDB のインメモリ (:memory:) を利用してユニットテストを作成してください。
- コードスタイル: type hints とドキュメンテーション文字列を尊重してください。
- Issue / PR では設計意図（冪等性、トレーサビリティ、UTC 時刻保存等）を尊重することを推奨します。

---

## 補足・注意点

- 実運用で発注（execution）を行う場合は、手元の kabuステーション API や証券会社の仕様に合わせた追加の安全チェック（リスク管理、ポジション上限、二重送信対策等）を必ず実装してください。
- Slack 通知や監視連携は基本的な設定を取り扱うため、運用ルールに応じた詳細な実装が必要です。
- 本リポジトリはデータ取得・保存・品質チェック・監査ログに重点を置いています。実際の売買戦略・実注文の送信は strategy / execution 層で実装してください。

---

README に含める追加情報（例: サンプル .env.example、運用フロー図、データスキーマ図）が必要であればお知らせください。