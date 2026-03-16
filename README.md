# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。  
データ取得（J-Quants）、データベーススキーマ（DuckDB）、ETLパイプライン、データ品質チェック、監査ログなど、戦略開発・運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けの基盤ライブラリです。本コードベースは以下を主に提供します。

- J-Quants API クライアント（株価・財務・カレンダー取得）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（日次差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレースを保持する監査テーブル）
- 環境変数・設定読み込み（.env/.env.local の自動読み込み、保護）

設計上の特徴:
- API レート制御（120 req/min）
- 再試行（指数バックオフ、401 の場合のトークン自動リフレッシュ）
- ETL は冪等（DuckDB への挿入は ON CONFLICT DO UPDATE）
- 品質チェックは全件収集型（致命的問題だけで即停止しない）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API 経由で日足（OHLCV）、財務諸表、JPX カレンダーを取得
  - レートリミット、リトライ、トークン自動更新、ページネーション対応
  - DuckDB へ冪等に保存する save_* 関数

- data/schema.py
  - DuckDB に作成するテーブル定義（Raw / Processed / Feature / Execution）
  - init_schema(), get_connection()

- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー -> 株価 -> 財務 -> 品質チェック の流れ
  - 差分更新、バックフィル、品質チェック統合

- data/quality.py
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue を返却し、呼び出し側が対応を決定可能

- data/audit.py
  - 監査用テーブル（signal_events, order_requests, executions）
  - init_audit_schema(), init_audit_db()

- config.py
  - .env / .env.local の自動読み込み（プロジェクトルート：.git または pyproject.toml に基づく）
  - 必須設定の取得（settings オブジェクト経由）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - サポート環境: development / paper_trading / live

---

## 前提・依存

- Python 3.10+
  - （型ヒントに | を使用しているため 3.10 以上を想定）
- 依存パッケージ（少なくとも以下が必要）
  - duckdb

必要であればプロジェクトのパッケージ化/requirements を追加してください（本コードは標準ライブラリの urllib を使用しており、外部 HTTP クライアントを用いていません）。

---

## セットアップ手順（ローカル・開発用）

1. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存パッケージをインストール
   ```
   pip install duckdb
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. （任意）パッケージを開発編集モードでインストール
   プロジェクトルートに `pyproject.toml` / `setup.cfg` 等がある場合:
   ```
   pip install -e .
   ```

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます（`.env.local` は .env を上書き）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=<your_refresh_token>  -- 必須（J-Quants 認証）
   - KABU_API_PASSWORD=<password>               -- 必須（kabuステーション API）
   - SLACK_BOT_TOKEN=<token>                    -- 必須（通知用）
   - SLACK_CHANNEL_ID=<channel_id>              -- 必須（通知先）
   - KABUSYS_ENV=development|paper_trading|live -- 省略時 development
   - LOG_LEVEL=INFO|DEBUG|...                   -- 省略時 INFO
   - DUCKDB_PATH=data/kabusys.duckdb            -- 省略時
   - SQLITE_PATH=data/monitoring.db             -- 省略時

   .env のサンプル（例）:
   ```
   JQUANTS_REFRESH_TOKEN="xxxx"
   KABU_API_PASSWORD="yyyy"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C12345678"
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## データベース初期化

DuckDB スキーマを作成するには `init_schema()` を使用します。

Python スクリプト例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH の値（またはデフォルト）
conn = init_schema(settings.duckdb_path)
# 以後 conn を使って ETL / チェック / クエリを実行する
```

監査ログ専用に初期化する場合:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

`:memory:` を渡すとインメモリ DB が使えます（テスト用）。

---

## 使い方（ETL の実行）

日次 ETL を実行する簡単な例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ本日（内部で営業日に調整）
print(result.to_dict())
```

run_daily_etl の主な引数:
- conn: DuckDB 接続
- target_date: ETL 対象日（省略時は今日）
- id_token: J-Quants の id_token（省略すると内部で refresh_token から取得）
- run_quality_checks: 品質チェックを行うか（デフォルト True）
- spike_threshold: スパイク検出閾値（デフォルト 0.5 = 50%）
- backfill_days: 差分再取得のバックフィル日数（デフォルト 3）
- calendar_lookahead_days: 市場カレンダー先読み日数（デフォルト 90）

個別ジョブを呼ぶこともできます:
- run_calendar_etl(conn, target_date, ...)
- run_prices_etl(conn, target_date, ...)
- run_financials_etl(conn, target_date, ...)

ETL実行時の例外は各ステップごとに捕捉され、結果オブジェクト（ETLResult）の `errors` に追加されます。品質チェックで検出された問題は `quality_issues` に格納されます。

---

## 品質チェック（quality モジュール）

主なチェック:
- check_missing_data: 必須カラム（open/high/low/close）欠損検出（error）
- check_spike: 前日比スパイク検出（warning、デフォルト閾値 50%）
- check_duplicates: 主キー重複検出（error）
- check_date_consistency: 未来日付 / 非営業日データの検出（error/warning）

すべて実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=some_date)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

設計方針としては「全件収集型」で、致命的な問題があってもすぐに ETL を停止しないため、呼び出し側で `has_quality_errors` を確認して適切に対処してください。

---

## 監査ログ（audit）

監査テーブルはシグナルから約定までのトレースを保持します（UUID ベースの連鎖）。初期化関数:

- init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加
- init_audit_db(db_path): 監査専用 DB を初期化して接続を返す

監査テーブルは TIMESTAMP を UTC で保存するように設定されます。

---

## ログ・設定挙動

- .env と .env.local はプロジェクトルート（.git または pyproject.toml がある場所）から自動的に読み込まれます。
  - 読み込み順: OS 環境 > .env.local > .env
  - OS 環境変数は保護され、.env による上書きを防ぎます（ただし .env.local は上書き可能）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト用途）。
- settings オブジェクトは必須の値が欠けると ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## ディレクトリ構成

以下は主要ファイル/ディレクトリと役割の一覧です（src/kabusys 配下）:

- __init__.py
  - パッケージ初期化。__version__ を定義。

- config.py
  - 環境変数の読み込み・設定オブジェクト（settings）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック、リトライ、レート制御）
  - schema.py
    - DuckDB スキーマ定義、init_schema(), get_connection()
  - pipeline.py
    - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality.py
    - データ品質チェック（各チェック関数・run_all_checks）
  - audit.py
    - 監査ログテーブルの定義・初期化（init_audit_schema, init_audit_db）
  - pipeline / jquants_client の補助ロジック（ETL 用ユーティリティ）

- strategy/
  - __init__.py
  - （戦略実装用のプレースホルダ。戦略ロジックはここに実装）

- execution/
  - __init__.py
  - （発注 / ブローカー連携のロジックを配置）

- monitoring/
  - __init__.py
  - （監視・アラート周りのロジック）

---

## 運用ヒント

- 定期実行: run_daily_etl を cron / scheduled job で毎日実行して最新データを維持します。
- バックフィル: ETL はデフォルトで直近 backfill_days（デフォルト 3 日）を再取得して API の後出し修正に耐性があります。
- テスト: `:memory:` の DuckDB を使えば単体テストが容易です（init_schema(":memory:")）。
- ログレベルは環境変数 LOG_LEVEL で調整できます（DEBUG/INFO/...）。
- 本番運用時は KABUSYS_ENV を `live` に設定し、paper_trading などで安全に検証してください。

---

## 例: 簡易 ETL 実行スクリプト

保存例: scripts/run_daily_etl.py
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

def main():
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn)
    print(result.to_dict())

if __name__ == "__main__":
    main()
```

実行:
```
python scripts/run_daily_etl.py
```

※ 実行前に環境変数（JQUANTS_REFRESH_TOKEN 等）を設定してください。

---

もし README に追加したい内容（CI 設定例、より詳しい運用手順、サンプルデータのロード方法、Slack 通知や kabu ステーション連携の実装例など）があれば教えてください。必要に応じてサンプル .env.example を作成します。