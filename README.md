# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）です。  
データ収集（J-Quants）、ETL、データ品質チェック、DuckDB スキーマ、監査ログ管理、発注／実行のための骨組みを提供します。

主に内部で使うライブラリ群を含み、戦略実装やブローカー連携部分を組み合わせて自動売買システムを構築できます。

---

## 主な特徴（機能一覧）

- 環境変数／設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定は `Settings` クラスで取得（未設定時エラー）
  - 実行環境フラグ（development / paper_trading / live）・ログレベル指定
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）の厳守（固定間隔スロットリング）
  - 自動リトライ（指数バックオフ、最大 3 回、408/429/5xx に対応）
  - 401 受信時はトークン自動リフレッシュして1回リトライ
  - 取得時刻（UTC）を記録し Look-ahead バイアスに配慮
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution のレイヤーでテーブル定義
  - インデックス、外部キー、型チェックを含むDDL
  - `init_schema()` / `get_connection()` を提供
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日から差分のみ取得）
  - バックフィル（後出し修正吸収）とカレンダー先読み
  - 品質チェック（kabusys.data.quality）との連携
  - 日次 ETL エントリ `run_daily_etl()` と個別ジョブ（prices/financials/calendar）
  - 結果は `ETLResult` として詳細を返す
- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠損）、重複（主キー重複）、スパイク（前日比閾値超過）、日付不整合（未来日付・非営業日データ）
  - 問題を `QualityIssue` リストとして返却（error / warning を区別）
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注 → 約定のトレーサビリティを確保するテーブル群
  - 冪等キー（order_request_id / broker_execution_id）やステータス管理
  - `init_audit_schema()` / `init_audit_db()` を提供

---

## 前提（Prerequisites）

- Python 3.10 以上（| 型ヒントなどにより 3.10+ が必要）
- duckdb（DuckDB Python パッケージ）
- ネットワーク経由で J-Quants 等外部 API にアクセス可能であること

必要なら他のランタイム依存を追加してください（例: Slack 通知などのための追加パッケージ）。

---

## セットアップ手順

1. Python と依存パッケージのインストール
   - 仮想環境内で作業することを推奨します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
     - pip install --upgrade pip
     - pip install duckdb

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

2. 必要な環境変数を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 最低限設定すべき変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb) — DuckDB ファイルパス
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db) — 監視用 SQLite（別用途）
     - KABUSYS_ENV (任意, default: development) — development / paper_trading / live
     - LOG_LEVEL (任意, default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

3. データベーススキーマの初期化
   - DuckDB を用いてスキーマを初期化します（ファイル DB または :memory:）。
   - 例スクリプト:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

4. 監査ログテーブルの初期化（必要な場合）
   - schema で作成した conn を渡して追加作成:
     - from kabusys.data import audit
     - audit.init_audit_schema(conn)
   - 監査ログ専用 DB を作る場合:
     - audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単なコード例）

- 設定取得（Settings）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
  - if settings.is_live: ...

- スキーマ初期化と ETL 実行（日次 ETL）
  - 例: daily_etl.py
    - from datetime import date
      from kabusys.data import schema, pipeline
      conn = schema.init_schema("data/kabusys.duckdb")
      result = pipeline.run_daily_etl(conn, target_date=date.today())
      print(result.to_dict())

- 個別ジョブ実行（株価差分 ETL）
  - from kabusys.data import schema, pipeline
    conn = schema.init_schema("data/kabusys.duckdb")
    fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

- J-Quants から直接データ取得して DuckDB に保存
  - from kabusys.data import jquants_client as jq
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = jq.save_daily_quotes(conn, records)

- 監査ログ初期化
  - from kabusys.data import audit
    conn = schema.init_schema("data/kabusys.duckdb")
    audit.init_audit_schema(conn)

- 品質チェックを個別に実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date.today())
    for i in issues: print(i)

注意点:
- ETL は各ステップを個別にエラーハンドリングします（1ステップの失敗で全体停止しません）。結果として ETLResult にエラー・品質問題が集約されます。
- J-Quants API の ID トークンはモジュール内でキャッシュされ、401受信時には自動リフレッシュされます。テスト時は id_token を明示的に注入して制御可能です。

---

## 環境変数自動読込みの挙動

- プロジェクトルートは `src/kabusys/config.py` 内で `.git` または `pyproject.toml` を探索して決定します。見つからない場合は自動読み込みをスキップします。
- 読み込み順序:
  - OS 環境変数（優先）
  - .env.local（存在すれば上書き）
  - .env
- 自動読み込みを無効にする:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する

.env のパースは一般的な shell 形式（export あり、シングル／ダブルクォート対応、インラインコメントの扱い等）に配慮しています。

---

## 主要 API の概要

- kabusys.config
  - settings: Settings インスタンス
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.kabu_api_base_url
    - settings.slack_bot_token, settings.slack_channel_id
    - settings.duckdb_path, settings.sqlite_path
    - settings.env, settings.log_level, settings.is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)  # DuckDB に idempotent 保存
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection（テーブルとインデックスを作成）
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

以下は現状の主要ファイル／モジュール構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py

各モジュールの役割:
- config.py: 環境変数／設定の読み込みと検証
- data/jquants_client.py: J-Quants API クライアントと DuckDB への保存ユーティリティ
- data/schema.py: DuckDB の DDL 定義と初期化関数
- data/pipeline.py: ETL パイプライン（差分取得・保存・品質チェック）
- data/quality.py: データ品質検査
- data/audit.py: シグナル→発注→約定の監査ログテーブル定義と初期化

---

## 運用上の注意

- J-Quants のレート制限（120 req/min）を遵守するため、jquants_client 内で待機ロジックがあります。外部から連続リクエストを送る場合は注意してください。
- DB 初期化は冪等（既存テーブルはスキップ）ですが、DDL 変更時は既存データと整合性に注意してください。
- 監査ログは削除しない想定（ON DELETE RESTRICT 等）。バックアップ・アーカイブ運用を検討してください。
- 本ライブラリはコア基盤を提供します。実際の発注処理（証券会社 API 経由）やリスク管理、戦略アルゴリズムは別途実装が必要です。

---

## サンプル（短い実行例）

簡易 ETL 実行:
```
from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（ファイルがなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（本日を対象）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

監査ログ初期化（別 DB にする例）:
```
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

README はここまでです。必要であれば以下の内容を追加で作成します:
- .env.example の完全テンプレート
- CI / GitHub Actions 用の DB 初期化スクリプト例
- より詳細な API 使用例（各引数のサンプル値）
- Logging の設定例（logging.basicConfig 等）

どれを追加しますか？