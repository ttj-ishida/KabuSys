# KabuSys

日本株自動売買システムのコアライブラリ（KabuSys）。  
このリポジトリはデータ取得（J-Quants）、データ基盤（DuckDB スキーマ・ETL・品質チェック）、監査ログ（発注→約定のトレーサビリティ）などの基盤機能を提供します。戦略（strategy）／発注（execution）／監視（monitoring）は拡張ポイントとして用意されています。

---

## プロジェクト概要

- J-Quants API から株価・財務・取引カレンダー等を取得し、DuckDB に保存する ETL 基盤を提供します。
- レート制限（120 req/min）や再試行・トークン自動リフレッシュ等を組み込み、運用に耐える堅牢性を目指しています。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行い、監査ログ（signal → order_request → execution）を保持します。
- 戦略／発注はモジュールとして分離されており、独自実装を容易に差し替えられます。

主な実装言語: Python 3.10+（型ヒントで | を使用）

---

## 主な機能一覧

- 環境変数管理
  - プロジェクトルートの .env / .env.local を自動読み込み（.git または pyproject.toml を基準）
  - 必須値チェック（Settings クラス）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- J-Quants クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダー取得
  - レートリミッタ（120 req/min）
  - リトライ（指数バックオフ、最大3回）・401時のリフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - fetched_at による取得時刻（UTC）記録（Look-ahead Bias 対策）

- DuckDB スキーマ定義（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、init_schema による冪等的初期化

- ETL パイプライン（data/pipeline.py）
  - 差分更新（最終取得日時からの差分取得 + backfill）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック実行（quality モジュール）
  - run_daily_etl による一括実行

- 品質チェック（data/quality.py）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日）検出
  - QualityIssue オブジェクトで問題を集約

- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions の監査テーブルを定義
  - order_request_id による冪等性、UTC タイムゾーン設定
  - init_audit_schema / init_audit_db を提供

---

## セットアップ手順

1. Python バージョン確認  
   Python 3.10 以上を推奨（typing の `|` 演算子を使用）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要ライブラリのインストール（最低限）
   - pip install duckdb

   ※ その他の依存（requests 等）は実装で追加される可能性があります。プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。

4. 環境変数の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限設定すべき環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネルID
   - (オプション) KABUSYS_ENV = development | paper_trading | live
   - (オプション) LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
   - (オプション) DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - (オプション) SQLITE_PATH (デフォルト: data/monitoring.db)

   .env の書き方はシェルの environment ファイル形式（KEY=VALUE）。`.env.local` は `.env` を上書きできます。

---

## 使い方（基本例）

以下は最小限の使い方例です。Python スクリプトや CI / cron / Airflow 等から呼び出して運用します。

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema
from kabusys.config import settings

# デフォルトパスまたは設定されたパスに DB を作成してテーブルを初期化
conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（run_daily_etl）

```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続（初回は init_schema を推奨）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 監査ログの初期化（監査用テーブルを追加）

```python
from kabusys.data import schema, audit
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
audit.init_audit_schema(conn)
```

4) J-Quants の個別 API 呼び出し（デバッグやバックフィル用途）

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)
# トークンは settings.jquants_refresh_token を内部で使うため通常指定不要
records = jq.fetch_daily_quotes(date_from=date(2022,1,1), date_to=date(2022,1,31))
jq.save_daily_quotes(conn, records)
```

注意点:
- run_daily_etl は内部で calendar → prices → financials → quality チェックの順に実行します。各ステップは個別に例外処理され、1ステップ失敗でも他ステップは継続します（結果に errors が蓄積されます）。
- ID トークンは自動キャッシュ/自動リフレッシュされます。get_id_token() を直接呼ぶ場合は allow_refresh を考慮してください（無限再帰防止のため内部呼出しでは制御があります）。

---

## よく使う設定・挙動

- レート制限: 120 req/min を固定間隔で保証（内部 _RateLimiter）
- リトライ: 408/429/5xx を対象に指数バックオフ（最大 3 回）。429 の場合は Retry-After ヘッダを優先。
- 401 Unauthorized: トークン期限切れと判断して自動で 1 回リフレッシュして再試行。
- DuckDB 保存: ON CONFLICT DO UPDATE による冪等性を担保（raw テーブル保存関数群）。
- 品質チェック: error / warning で分類。ETL の結果オブジェクト（ETLResult）に quality_issues が含まれます。

---

## ディレクトリ構成

（リポジトリの src を起点とした主要ファイル/モジュール）

- src/kabusys/
  - __init__.py (パッケージエクスポート)
  - config.py
    - Settings: 環境変数の取得と検証
    - 自動 .env ロード（.git または pyproject.toml を基準）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_* / save_*）
      - レート制限・再試行・トークン管理
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
      - ETLResult データクラス
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）初期化
    - quality.py
      - データ品質チェック（missing, spike, duplicates, date_consistency）
  - strategy/
    - __init__.py (戦略モジュールの拡張ポイント)
  - execution/
    - __init__.py (発注ロジックの拡張ポイント)
  - monitoring/
    - __init__.py (監視・アラートの拡張ポイント)

---

## 開発メモ / 注意事項

- Python 3.10+ を想定しています（型 annotation で | を多用）。
- .env パーサはクォート・エスケープ・コメントにある程度対応していますが、複雑な書式は避けてください。
- DuckDB のファイル保存先は Settings.duckdb_path（デフォルト: data/kabusys.duckdb）。初回実行時に親ディレクトリを自動作成します。
- 監査ログは削除しない設計（ON DELETE RESTRICT）。監査データは永続化される前提です。
- strategy / execution / monitoring は各自で実装を追加してください。コアはデータ基盤と監査です。

---

もし README に追加したい内容（例: CI / デプロイ手順、具体的な戦略実装テンプレート、Dockerfile 例、テストの実行方法など）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を補足します。