# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・保存（DuckDB）・ETLパイプライン・品質チェック・監査ログ基盤を提供し、戦略層・発注層・監視層と組み合わせて運用するための基盤モジュール群です。

主な目的:
- J-Quants API からの市場データ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義と永続化（冪等保存）
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- 発注〜約定までの監査ログスキーマ（トレーサビリティ保証）
- 環境変数ベースの設定管理（.env の自動読み込み機構）

---

## 機能一覧

- 設定 / 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git / pyproject.toml）
  - 必須環境変数の取得メソッド
  - 実行環境 (development / paper_trading / live) とログレベル検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得
  - API レート制御（120 req/min 固定スロットリング）
  - リトライ（指数バックオフ、最大3回）、401 受信時は自動トークンリフレッシュ
  - ページネーション対応、取得時刻（UTC fetched_at）の記録
  - DuckDB への冪等な保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含む包括的なスキーマ定義
  - テーブル作成・インデックス作成用 API（init_schema, get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL エントリポイント run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック の順で実行
  - 差分更新、backfill、カレンダー先読み
  - 各ジョブは独立してエラーハンドリング（途中失敗でも他ステップ継続）
  - ETL 結果を集約した ETLResult を返す

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合を検出
  - QualityIssue オブジェクトで問題の詳細（サンプル行含む）を返す
  - run_all_checks で一括実行

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを UUID 連鎖で記録
  - order_request_id による冪等性、各種ステータス、UTC タイムスタンプ

- プレースホルダパッケージ
  - strategy/, execution/, monitoring/（将来的な戦略実装や発注、監視ロジックを想定）

---

## 必要条件

- Python 3.10 以上（コードはパイプライン型ヒントや union operator `|` を使用）
- duckdb
- 標準ライブラリの urllib 等を使用（外部 HTTP クライアントは不要）
- （任意）Slack 通知等を利用する場合は slack sdk など

推奨インストール（仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# Slack 連携やその他ツールが必要なら追加インストール
```

（プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot Token（通知に使用）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（テスト用途）

.env 例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

自動ロードについて:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読み込みます。
- テストなどで自動読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（例: duckdb）
3. プロジェクトルートに .env を作成し、必要な環境変数を設定
4. DuckDB スキーマ初期化を実行

例（Python スクリプトから初期化）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照する
conn = init_schema(settings.duckdb_path)
# 追加で監査ログを有効にする場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（主要な API と実行例）

- DuckDB スキーマ初期化
  - init_schema(db_path) → DuckDB 接続を返す（":memory:" も可能）

- 日次 ETL 実行（カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別ジョブの実行例
  - run_prices_etl / run_financials_etl / run_calendar_etl は差分取得を行い、(fetched, saved) を返します。

- J-Quants クライアントを直接使う（テストや診断用）
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を自動使用（または get_id_token に明示的に渡す）
daily = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# DuckDB に保存する場合は save_daily_quotes(conn, daily)
```

- 品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

ログ・通知:
- settings.log_level を使ってロギングレベルを制御できます。Slack 連携などは別モジュールで実装してください（slack トークンは settings から取得可能）。

注意点:
- J-Quants のレート制限（120 req/min）を守るため、クライアントは内部で固定間隔スロットリングを行います。
- HTTP リトライ、トークン自動リフレッシュ、ページネーション対応済み。
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）で重複を吸収します。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの一覧（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（settings インスタンス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - schema.py
      - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
      - init_schema, get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログ用スキーマ（signal_events, order_requests, executions）
  - strategy/
    - __init__.py
    - （戦略実装用プレースホルダ）
  - execution/
    - __init__.py
    - （ブローカ接続 / 発注ロジック用プレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・アラート用プレースホルダ）

補足:
- DataSchema.md / DataPlatform.md といった設計ドキュメントを前提とした実装方針がコメントとしてソースに含まれています（プロジェクト設計資料に準拠）。

---

## 運用上の注意

- 本ライブラリ自体は取引ロジック（実際の売買判断）やブローカへの直接発注処理を含みません。実運用で発注を行う場合は execution 層の実装と徹底したテスト・安全対策（レート制御、冪等性、異常時のフェイルセーフ）を行ってください。
- データ品質チェックは警告・エラーを返しますが、ETL は可能な限り前後のステップを続行します。呼び出し側は ETLResult の has_errors / has_quality_errors を参照して適切なアクションを決めてください。
- 監査ログは削除しない運用を想定しています（ON DELETE RESTRICT）。監査データ保持方針とストレージ容量に注意してください。
- 全てのタイムスタンプは UTC で扱う設計です（監査テーブル初期化時に SET TimeZone='UTC' を実行）。

---

もし README に含めたい追加情報（例: CI/CD 手順、requirements.txt の具体的な中身、.env.example の配布、サンプルデータやユニットテスト実行法）があれば教えてください。必要に応じて追記・整形します。