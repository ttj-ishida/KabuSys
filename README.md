# KabuSys

日本株自動売買システム（ライブラリ）  
このリポジトリは、J‑Quants API から市場データを取得し、DuckDB に格納・品質検査を行い、戦略→発注→監査の基盤を提供するモジュール群です。ETL（データ取得・保存・品質チェック）や監査ログ（トレース可能な発注/約定ログ）を含むデータプラットフォームの基盤実装を目的としています。

主な設計方針・特徴
- J‑Quants API のレート制限（120 req/min）を守る固定間隔スロットリング
- リトライ（指数バックオフ）、401 受信時の自動トークンリフレッシュ
- データ取得の冪等性（DuckDB への INSERT ... ON CONFLICT DO UPDATE）
- 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を防止
- ETL は差分更新（バックフィル可能）かつ品質チェックを実行
- 監査ログは UUID 階層でシグナル→発注→約定を完全トレース可能に設計

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを自動検出）
  - 必須環境変数のチェック
- J‑Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得
  - JPX マーケットカレンダー取得
  - トークン取得（リフレッシュ）機能
  - レート制御・リトライ・エラーハンドリング
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義とスキーマ初期化ユーティリティ
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得（最終取得日ベース）とバックフィル
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（audit）
  - シグナル、発注要求、約定ログのスキーマと初期化関数
  - 発注の冪等性（order_request_id）を前提とした設計

---

## 必要な環境変数

Settings（kabusys.config.Settings）で参照する主要な環境変数:

必須
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — 通知先のチャンネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

制御用
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化

.env 読み込みの挙動:
- プロジェクトルートを .git または pyproject.toml で検出
- 読み込み順: OS 環境変数 > .env.local > .env
- .env のパースは export 形式や quoted 値、コメント等に対応

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境の準備（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージのインストール  
   このコードベースでは主に標準ライブラリを利用していますが、DuckDB が必要です:
   ```
   pip install duckdb
   ```
   （実際の公開パッケージ化／requirements.txt がある場合はそちらを利用してください）

3. 環境変数設定  
   プロジェクトルートに `.env`（と必要なら `.env.local`）を作成して必須変数を設定します。自動読み込みはデフォルトで有効です。

4. DuckDB スキーマ初期化（例）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルがなければ自動作成
   ```
   監査ログを別 DB に分ける場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```
   既存接続に監査テーブルを追加する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)  # conn は init_schema の戻り値
   ```

---

## 使い方（基本例）

- J‑Quants トークンを明示的に取得する:
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）:
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL ジョブ
  - 株価差分 ETL:
    ```python
    from kabusys.data import pipeline
    fetched, saved = pipeline.run_prices_etl(conn, target_date)
    ```
  - 財務差分 ETL:
    ```python
    fetched, saved = pipeline.run_financials_etl(conn, target_date)
    ```
  - カレンダー ETL:
    ```python
    fetched, saved = pipeline.run_calendar_etl(conn, target_date)
    ```

- 品質チェックを手動で実行:
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

- 監査ログ初期化（既存 conn に追加）:
  ```python
  from kabusys.data import audit
  audit.init_audit_schema(conn)
  ```

運用時の注意
- J‑Quants API のレート制限（120 req/min）に従うため、長時間で大量取得する場合は配慮が必要です（実装内で固定間隔スロットリングを行います）。
- ETL のバックフィル設定（backfill_days）により、直近数日の再取得で API の後出し修正を吸収します。
- すべてのタイムスタンプ（fetched_at / created_at 等）は UTC を前提としています。

---

## ディレクトリ構成

リポジトリ内の主要ファイルとサブパッケージ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数と Settings 定義（.env ロード）
  - data/
    - __init__.py
    - jquants_client.py            -- J‑Quants API クライアント（fetch/save）
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - audit.py                     -- 監査ログ（signal/order/execution）スキーマ
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略層用（ボイラープレート）
  - execution/
    - __init__.py                  -- 発注／ブローカー連携層（ボイラープレート）
  - monitoring/
    - __init__.py                  -- 監視系（将来的な実装想定）

（各ファイルには詳細な docstring と実装方針が含まれています）

---

## 実装上の重要ポイント（補足）

- 冪等性: jquants_client の save_* 関数は ON CONFLICT DO UPDATE を用いて重複挿入を避け、再実行しても安全です。
- レート制御: _RateLimiter により最小間隔が保証され、また HTTP 429 の場合は Retry‑After を優先してリトライします。
- トークン管理: get_id_token でリフレッシュトークンから id_token を取得。401 を受けた際は自動で一度だけリフレッシュして再試行します。
- 品質チェック: 重大度（error / warning）を返す設計で、ETL はチェックで error が出ても処理を継続して問題を収集します。呼び出し元で停止判断を行ってください。

---

## ライセンス・貢献

（ここにライセンス情報や貢献方法、連絡先などを追記してください）

---

README はプロジェクトの最初の案内です。ご希望があれば、具体的な運用例（cron / Airflow の DAG 例）、Docker 化、CI/CD のセットアップ例、Slack への通知例などのセクションを追加できます。どのトピックを優先して追加しますか？