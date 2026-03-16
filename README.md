# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株の自動売買に必要なデータ取得、ETL、データ品質チェック、監査ログ（トレーサビリティ）基盤を提供するライブラリ群です。本リポジトリは主に次の機能を含みます:

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェックモジュール（欠損・重複・スパイク・日付不整合）
- 発注／約定に関する監査ログスキーマ（トレーサビリティ）

---

## 主な機能一覧

- data.jquants_client
  - 株価日足（OHLCV）、財務データ（四半期）、マーケットカレンダーの取得
  - レートリミット（120 req/min）管理、指数バックオフリトライ、401 の自動リフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）

- data.schema
  - Raw / Processed / Feature / Execution 層の DuckDB DDL 定義
  - スキーマ初期化（init_schema）と接続取得（get_connection）

- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 価格 → 財務 → 品質チェックの順で実行
  - 差分取得・バックフィル・営業日調整・品質チェック集約（ETLResult にサマリ保存）

- data.quality
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合のチェック
  - 各チェックは QualityIssue オブジェクトのリストを返す（エラー／警告の分離）

- data.audit
  - シグナル → 発注要求 → 約定 の監査テーブル群を提供
  - order_request_id を冪等キーとした設計、すべての TIMESTAMP は UTC を想定

- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 設定アクセサ（Settings）で必須値の取得と検証

---

## 動作環境・前提

- Python 3.10 以上（型ヒントで | 演算子などを利用）
- duckdb（DuckDB Python モジュール）
- ネットワーク通信可能（J-Quants API へアクセスするため）
- 必要な外部サービスの認証情報（J-Quants / kabuステーション / Slack 等）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージのインストール（例）
   - pip install duckdb

   （将来的に requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数の設定
   - プロジェクトルートの `.env` または OS 環境変数で以下を設定してください。

例: .env（サンプル）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token_

# kabuステーション API
KABU_API_PASSWORD=あなたの_kabu_api_password_
# KABU_API_BASE_URL は任意（デフォルト: http://localhost:18080/kabusapi）

# Slack（通知に使用する場合）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development       # development | paper_trading | live
LOG_LEVEL=INFO
```

注意:
- パッケージロード時に自動で .env を読み込む仕組みがあります（プロジェクトルートに .git または pyproject.toml がある場合）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## 使い方（基本例）

以下は Python スクリプト／REPL から主要機能を利用する例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはメモリDB
# conn = schema.init_schema(":memory:")
```

2) J-Quants トークン取得（明示的に取得する場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

3) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は schema.init_schema の戻り値
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) 監査ログの初期化
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
# 既存 conn に監査テーブルを追加する
init_audit_schema(conn)

# 監査専用DBを作る場合
# audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

5) 直接 API でデータを取得して保存する
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 主要 API 要点（設計・挙動）

- jquants_client
  - レート制限を守るため内部でスロットリングを実施（120 req/min）
  - ネットワークエラーや 429/408/5xx に対して指数バックオフ（最大 3 回）
  - 401 を受けた場合はリフレッシュトークンで自動的に ID トークンを更新し 1 回リトライ
  - データ取得時に fetched_at（UTC）を記録し、Look-ahead Bias の追跡を支援

- schema
  - Raw / Processed / Feature / Execution / Audit のテーブルを定義
  - init_schema は冪等（既存テーブルはスキップ）
  - init_audit_schema は UTC を前提にタイムゾーンを設定

- pipeline
  - 差分取得のデフォルト単位は営業日で、最終取得日から backfill_days（デフォルト 3 日）を遡って再取得
  - ETL の各ステップは独立してエラー処理され、1ステップの失敗で他ステップが止まらない設計（結果は ETLResult に記録）
  - run_daily_etl は品質チェックをオプションで実行可能

- quality
  - 各チェックはエラー一覧（QualityIssue）を返す。呼び出し側が重大度に応じて中断や通知を行う

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — デフォルト DB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（値を設定すると無効）

必須変数が不足している場合、config.Settings の該当プロパティアクセスで ValueError が発生します。

---

## ディレクトリ構成

リポジトリ（src/kabusys 配下）の主要ファイルと役割:

- src/kabusys/
  - __init__.py — パッケージの基本情報（__version__）
  - config.py — 環境変数・設定管理（.env の自動読み込み、Settings クラス）

- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 / 保存 / 認証 / レート制御 / リトライ）
  - schema.py — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
  - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック）
  - audit.py — 監査ログ（signal / order_request / executions テーブル）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）

- src/kabusys/strategy/
  - __init__.py — 戦略モジュールのプレースホルダ（戦略ロジックはここに実装）

- src/kabusys/execution/
  - __init__.py — 発注・ブローカ連携のプレースホルダ

- src/kabusys/monitoring/
  - __init__.py — 監視・メトリクス関連のプレースホルダ

---

## 運用上の注意点

- KABUSYS_ENV に応じて本番（live）・ペーパー（paper_trading）・開発（development）挙動を分岐させる設計が可能です。実際の発注処理を行うモジュール（execution 等）では settings.is_live/is_paper を参照して安全対策を実装してください。
- DuckDB ファイルはデフォルトで data/ 以下に配置されます。バックアップや永続化の運用を検討してください。
- J-Quants の API レート制限とリトライロジックが組み込まれていますが、運用側でも過負荷を避けるスケジューリングを推奨します。
- 監査ログは削除しない前提の設計です（ON DELETE RESTRICT 等）。容量管理・アーカイブ方針を定めてください。

---

## 開発・拡張

- 戦略ロジックは `kabusys.strategy` 配下に実装してください（シグナル生成 → data.audit に保存 → execution 層へ渡す流れ）。
- execution 層には実際のブローカー API 呼び出しや冪等制御を実装してください（order_request_id を冪等キーとして利用）。
- 品質チェックや ETL のパラメータ（spike_threshold / backfill_days 等）は pipeline.run_daily_etl の引数から調整できます。

---

不明点や README の追加希望（例: 実行スクリプト、CI 設定、具体的な戦略テンプレートなど）があれば教えてください。必要に応じて README を拡張します。