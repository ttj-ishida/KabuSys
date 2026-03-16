# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（パッケージ名: `kabusys`）。  
データ取得、データベーススキーマ、ETLパイプライン、監査ログ、データ品質チェック等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を含むライブラリです。

- J-Quants API から株価・財務・市場カレンダーの取得
- DuckDB を用いた 3 層（Raw / Processed / Feature）データスキーマの管理
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント:
- API レート制限（120 req/min）を厳守するレートリミッタ
- リトライ（指数バックオフ）・トークン自動リフレッシュ（401 の場合）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは全件収集型（Fail-Fast ではない）

---

## 主な機能一覧

- 環境設定管理（`.env` の自動読み込み、必須キー検証）
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - rate limiting・retry・pagination・token refresh
  - DuckDB へ保存する save_* 関数
- DuckDB スキーマ管理
  - `init_schema()` で全テーブルとインデックスを作成（冪等）
  - `get_connection()` で接続を取得
- ETL パイプライン
  - `run_daily_etl()`：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分取得、バックフィル、品質チェック（spike 検出など）
  - ETLResult 型で詳細結果を返す
- 品質チェック（quality モジュール）
  - 欠損、スパイク、重複、日付不整合チェック
  - 各チェックは `QualityIssue` リストを返す
- 監査ログ（audit モジュール）
  - signal_events / order_requests / executions テーブル
  - 監査用 DDL とインデックス、初期化ユーティリティ

---

## セットアップ手順

前提：
- Python 3.10 以上（型注釈の `|` 演算子を使用）
- pip が利用可能

最低限の依存:
- duckdb

インストール例（ローカル開発）:
```bash
# 仮想環境を作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# pip 等をアップグレード
pip install --upgrade pip

# 必要パッケージをインストール
pip install duckdb

# （パッケージをプロジェクト直下から開発インストールする場合）
pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）

環境変数（任意・デフォルト）
- KABUSYS_ENV           : 実行環境。`development` (デフォルト) / `paper_trading` / `live`
- LOG_LEVEL             : ログレベル。`INFO` (デフォルト) / `DEBUG` / `WARNING` / ...
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の自動読み込み:
- プロジェクトルートを `.git` または `pyproject.toml` を基準に探索し、`.env` と `.env.local` を読み込みます。
- OS 環境変数を上書きしない設計（`.env.local` は上書き可）。
- 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env`
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

Python から利用する基本例を示します。

1) DuckDB スキーマ初期化:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path はデフォルトで data/kabusys.duckdb
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日に対して実行
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックで致命的な問題が検出されました")
```

3) 監査ログ（audit）を既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
```

4) 直接 J-Quants API を呼ぶ（トークン取得・フェッチ）:
```python
from kabusys.data import jquants_client as jq

# id_token を明示的に取得（内部では refresh token を使用）
id_token = jq.get_id_token()

# 銘柄コード 1301 の日足を取得
records = jq.fetch_daily_quotes(id_token=id_token, code="1301", date_from=None, date_to=None)
# DuckDB に保存するには conn を用いて
jq.save_daily_quotes(conn, records)
```

5) 個別の品質チェックを実行:
```python
from kabusys.data import quality
from datetime import date

issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- run_daily_etl は複数のステップを個別に try/except で扱い、問題があっても可能な限り処理を継続します。結果は ETLResult で確認してください。
- jquants_client は内部でレートリミッタとリトライを実装しています。API 制限に従い 120 req/min を目安に動作します。

---

## ディレクトリ構成

プロジェクト内の主要ファイルとモジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得/保存）
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - audit.py                # 監査ログ用スキーマ初期化
      - quality.py              # データ品質チェック
      - pipeline.py
      - audit.py
      - quality.py
    - strategy/                  # 戦略関連（現状空のパッケージ）
      - __init__.py
    - execution/                 # 発注・ブローカー実装（現状空のパッケージ）
      - __init__.py
    - monitoring/                # 監視関連（現状空のパッケージ）
      - __init__.py

（プロジェクトルートに .env/.env.local/.git などが存在する想定）

---

## 主要 API（要点）

- settings (kabusys.config.Settings)
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ... ) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## トラブルシューティング / 注意事項

- Python バージョンは 3.10 以上を推奨（型アノテーションに `|` を使用）。
- DuckDB ファイルの親ディレクトリが存在しない場合、`init_schema` や `init_audit_db` が自動で作成します。
- 環境変数が設定されていない場合、Settings の必須プロパティは ValueError を投げます（.env.example を参考に設定してください）。
- 自動 .env ロードはプロジェクトルート探索に依存します。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- J-Quants API の 401 応答時には自動でトークンリフレッシュを試みます（1 回のみ）。トークンが無効 / 期限切れの場合は適切なリフレッシュトークンを環境変数に設定してください。

---

この README はコードベースの現状（主要モジュールの実装）に基づいて作成しています。戦略層（strategy）、発注/Execution 層、モニタリング層の実装はプロジェクトの拡張に応じて追加してください。必要であればサンプルワークフローや CI 設定、より詳細な DataPlatform / DataSchema ドキュメントを追加できます。