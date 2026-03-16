# KabuSys

日本株向けの自動売買システム用ライブラリ（ミニマル実装）
このリポジトリは、J-Quants API を利用した市場データ取得、DuckDB によるデータレイクのスキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログのためのスキーマなどを提供します。

主な設計方針は「冪等性」「トレーサビリティ」「API レート制御」「品質担保」で、運用・検証（paper trading）から本番（live）まで想定しています。

---

## 機能一覧

- 環境変数 / .env の自動読み込み（プロジェクトルートを探索）
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
- 設定管理（`kabusys.config.settings`）
  - 必須トークンの取得（例: `JQUANTS_REFRESH_TOKEN` 等）
  - 環境（development / paper_trading / live）やログレベルの検証
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応の固定間隔レートリミッタ
  - リトライ（指数バックオフ、401 時の自動トークンリフレッシュ）
  - 取得時刻（fetched_at）の記録（Look-ahead bias 対策）
  - DuckDB へ冪等に保存する `save_*` 関数
- DuckDB スキーマ定義・初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブルと索引を定義
  - `init_schema()` による初期化（:memory: もサポート）
- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル（デフォルト 3 日）、品質チェックの統合
  - `run_daily_etl()` から ETL を一括実行し結果（ETLResult）を返す
- データ品質チェック（`kabusys.data.quality`）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - 問題は `QualityIssue` リストとして返却（error / warning）
- 監査ログ（`kabusys.data.audit`）
  - シグナル → 発注要求 → 約定までトレース可能な監査テーブル群
  - `init_audit_schema()` / `init_audit_db()` により初期化可能

---

## 前提条件

- Python 3.9+
- 必要な主要依存:
  - duckdb
- ネットワーク接続（J-Quants API へのアクセス）
- J-Quants のリフレッシュトークン等の環境変数

（実際の運用では他に HTTP クライアントや Slack ライブラリ等を追加する可能性があります）

---

## セットアップ手順

1. リポジトリをクローン / ワークスペースに配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb
   - その他プロジェクト固有の依存があれば追記してください
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くことが可能）
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

### 推奨 .env（例）

.env.example のような形式を参考にしてください。最低限必要な変数は下記です。

- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

任意 / デフォルト:
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

注意: Settings の必須値が不足していると起動時に ValueError を投げます。

---

## 使い方

以下は代表的な利用例です。適宜 Python スクリプトや CLI ジョブに組み込んでください。

- 設定取得

```python
from kabusys.config import settings

# 必須トークン等を参照
token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
```

- DuckDB スキーマ初期化

```python
from kabusys.data import schema

# デフォルト: data/kabusys.duckdb
conn = schema.init_schema(settings.duckdb_path)
```

- 監査ログ用スキーマ追加

```python
from kabusys.data import audit

# 既存の conn に監査テーブルを追加
audit.init_audit_schema(conn)

# または専用 DB を作る
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants API から日次株価を取得して保存（直接利用例）

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} records")
```

- 日次 ETL の実行（推奨: パイプライン関数を使う）

```python
from kabusys.data import pipeline
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 品質チェックのみ実行

```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date(2023, 1, 31))
for i in issues:
    print(i)
```

エラー処理:
- ETL 実行中は各ステップが独立して例外を捕捉するため、あるステップが失敗しても他は継続します。
- `ETLResult.errors` と `ETLResult.quality_issues` を必ず確認し、運用側でアクションを決定してください。

---

## 環境変数一覧（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルトあり:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効化

---

## 注意点 / 実装のポイント

- J-Quants クライアントは次を実装しています:
  - レート制御: 120 req/min を固定間隔で厳守
  - リトライ: ネットワークエラーや 408/429/5xx を指数バックオフで再試行（最大 3 回）
  - 401 が返った場合は一度だけリフレッシュトークンを用いて id_token を再取得して再試行
  - ページネーション対応（pagination_key を利用）
  - 取得時刻（fetched_at）を UTC ISO8601 で付与
- DuckDB への保存関数は ON CONFLICT DO UPDATE により冪等性を担保
- 品質チェックは Fail-Fast ではなく全件収集。重大度に応じて呼び出し元が判断

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント + DuckDB 保存関数
    - schema.py          -- DuckDB スキーマ定義・初期化
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）
    - quality.py         -- データ品質チェック
    - audit.py           -- 監査ログ（シグナル→発注→約定のトレーサビリティ）
    - pipeline.py
    - audit.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状の実装で提供されている主要モジュールの一覧です。strategy / execution / monitoring は今後の拡張ポイントとして空のパッケージが用意されています。）

---

## よくあるトラブルと対処

- ValueError: 環境変数が足りない
  - 必須変数（JQUANTS_REFRESH_TOKEN 等）を .env または OS 環境に設定してください。
- ネットワークや API の 429/5xx による失敗
  - jquants_client はリトライとバックオフを行いますが、短時間に大量リクエストを送るとレート制限に達します。時間を空けて再実行してください。
- .env が読み込まれない
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基準に .env を探します。必要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、手動で環境変数を設定してください。

---

## 今後の拡張ポイント（参考）

- strategy / execution モジュールに具体的な売買ロジックと発注ドライバを実装
- Slack 通知や監視ダッシュボードの統合（monitoring）
- テスト用のモッククライアント、CI ワークフロー
- メタデータやメトリクスの永続化（Prometheus / Grafana 統合）

---

この README はコードベースの現状に基づく概要ドキュメントです。実際にプロダクションで運用する際は、API レート・認証情報の保護、運用用のログ・監視、障害時のリトライ・ロールバック戦略を十分に設計してください。