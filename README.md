# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
J-Quants や kabuステーション 等の外部 API からデータを取得し、DuckDB に格納・品質チェックを行い、戦略／発注層へ供給することを目的としています。

バージョン: 0.1.0

---

## プロジェクト概要

- J-Quants API から株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを提供します。
- 取得データは DuckDB に三層（Raw / Processed / Feature）＋実行・監査テーブルとして保存します。
- ETL パイプライン（差分更新、バックフィル、品質チェック）を実装しています。
- 発注・監査用のスキーマを提供し、シグナル→発注→約定のトレースを可能にします。
- 設計上、API レート制限（120 req/min）の順守、リトライ（指数バックオフ）、トークン自動リフレッシュ、冪等な保存を重視しています。

---

## 主な機能一覧

- 環境変数管理（.env の自動読み込み / 保護）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
  - 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - レート制限（120 req/min）と最大 3 回のリトライ、401 時の自動トークンリフレッシュに対応
- DuckDB スキーマ管理
  - init_schema(db_path) によるスキーマ作成（Raw/Processed/Feature/Execution）
  - init_audit_schema(conn) / init_audit_db(db_path) による監査ログ用テーブルの作成
- ETL パイプライン
  - run_daily_etl(conn, target_date=..., ...)
    - 市場カレンダー取得（先読み）
    - 株価差分更新（バックフィル対応）
    - 財務データ差分更新
    - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- 品質チェックモジュール（quality）
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
  - 検出結果は QualityIssue オブジェクトとして集約
- 監査（audit）
  - signal_events / order_requests / executions を含む監査スキーマ
  - 発注の冪等性やトレース性を保証する設計

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | を使用）
- DuckDB を利用（duckdb Python パッケージ）

1. リポジトリをチェックアウト
   git clone ...

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb

   （必要に応じて他の HTTP ライブラリなどを追加してください。標準ライブラリの urllib を使用しているため追加は不要な場合があります）

4. 環境変数の設定
   プロジェクトルートに `.env` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化されます）。

   .env の例:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here

   # kabuステーション
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境設定
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 自動環境読み込みについて
   - デフォルト: OS 環境変数 > .env.local > .env の順で読み込み
   - OS 環境変数は保護され、.env で上書きされません（.env.local は上書き可）
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## 使い方

以下は代表的な利用例です。プロジェクトに CLI は含まれていないため、スクリプトやジョブから直接 API を呼び出して利用します。

1) DuckDB スキーマの初期化
```
from kabusys.data import schema

# ディスク上のファイルに初期化
conn = schema.init_schema("data/kabusys.duckdb")

# インメモリ DB を使う場合
# conn = schema.init_schema(":memory:")
```

2) 監査ログ（発注トレーサビリティ）スキーマを追加
```
from kabusys.data import audit
# 既存の conn に監査テーブルを追加
audit.init_audit_schema(conn)
# または監査専用 DB を作成
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL を実行（株価・財務・カレンダーの取得と品質チェック）
```
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())  # ETL 結果の概要（品質問題やエラーを含む）
```

- run_daily_etl の主なパラメータ:
  - id_token: J-Quants の ID トークンを注入可能（テスト用）
  - run_quality_checks: True/False（デフォルト True）
  - spike_threshold: スパイク検出閾値（デフォルト 0.5 = 50%）
  - backfill_days: 差分更新時のバックフィル日数（デフォルト 3）
  - calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

4) J-Quants API クライアント単独利用例
```
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# ID トークンは自動で settings.jquants_refresh_token から取得される
quotes = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
```

注意点:
- J-Quants API へのリクエストは内部で 120 req/min のレート制御を行います。
- HTTP 408/429/5xx 系は最大 3 回リトライ（指数バックオフ）。429 に Retry-After があれば尊重します。
- 401 は自動でリフレッシュして 1 回リトライします。
- DuckDB への保存は ON CONFLICT DO UPDATE を用いることで冪等性を確保します。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するフラグ（任意）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、Settings クラス（settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制限・リトライ）
    - schema.py
      - DuckDB スキーマ定義と init_schema, get_connection
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - audit.py
      - 監査ログテーブル（signal_events / order_requests / executions）
    - quality.py
      - 品質チェックモジュール（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
    - （戦略ロジック用のモジュールを配置する想定）
  - execution/
    - __init__.py
    - （発注／ブローカー連携の実装を置く想定）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用の実装を置く想定）

---

## 設計上の注意点 / ベストプラクティス

- ETL は差分更新かつ冪等であるため、定期ジョブ（cron / Airflow 等）での実行に向きます。
- run_daily_etl は品質チェックで検出された問題を集めて返します。呼び出し側で重大度に応じた運用（アラート、Slack 通知、一時停止等）を実装してください。
- 発注・監査周りは監査テーブルにより完全なトレーサビリティを目指しています。実運用では外部ブローカーの返却値を order_requests / executions に確実にマッピングしてください。
- API のレート制限やリトライはライブラリ側で対処しますが、大量のページネーション取得等を実行する場合は実行スケジュールを分割してください。

---

## 今後の拡張案（参考）

- 実際の kabuステーションへの発注アダプタおよび WebSocket/Streaming インターフェース実装
- Strategy レイヤーのサンプル実装（paper/live の切替を含む）
- CLI / 管理用ダッシュボードの提供
- テストヘルパー（モック ID トークン、API レスポンスの録再生）

---

必要に応じて README をプロジェクトのポリシーや運用手順に合わせてカスタマイズしてください。追加で「デプロイ手順」「Slack 通知サンプル」「運用チェックリスト」などを盛り込みたい場合は指示をください。