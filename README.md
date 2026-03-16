# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（データ収集・ETL・スキーマ・監査ログ等）

このリポジトリは、J-Quants API や kabuステーション 等から市場データを取得して DuckDB に保存し、戦略や発注ロジックが利用できる形に整備するための基盤モジュール群を提供します。データ品質チェック（欠損・スパイク・重複・日付不整合）や監査ログ（シグナル→発注→約定のトレーサビリティ）を重視した設計になっています。

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - Look-ahead Bias 防止のため fetched_at を UTC で記録
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit（監査） 層のテーブル定義と初期化
  - 実運用を想定した制約・インデックス設計

- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）の実行と集計
  - エラー耐性：個別ステップの失敗に対してパイプライン全体は継続

- データ品質チェック
  - QualityIssue 型で検出結果を返す（severity: error / warning）
  - 全チェックを一括実行可能

- 監査ログ（audit）
  - シグナル→発注要求→約定を UUID で紐づけて完全トレース
  - 発注冪等キー（order_request_id）など運用上の要件を考慮

## 機能一覧（要約）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルートの検知: .git または pyproject.toml）
  - 環境変数取得ラッパ（必須キー検証、KABUSYS_ENV/LOG_LEVEL チェック）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ保存）

- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - ETLResult（処理概要と品質チェック結果を保持）

- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

## 前提（Requirements）

- Python >= 3.10
- 必要なパッケージ（例）
  - duckdb
- ネットワークアクセス（J-Quants API へアクセス可能であること）
- 環境変数（下記参照）に有効な認証情報を用意

（実際のパッケージ依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は 1 を設定

通常はリポジトリルートに `.env` / `.env.local` を置き、上記を設定します。`.env.local` は `.env` を上書きします。プロジェクトルートの検出は __file__ を起点に .git や pyproject.toml を探索します。

## セットアップ手順

1. リポジトリをクローン / コードを配置

2. Python 環境を作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb
   - （その他の依存はプロジェクトの要件ファイルを参照）

4. 環境変数を設定
   - リポジトリルートに `.env` を作成し、必要なキーを設定
   - 例:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードを無効にする場合は環境に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット

5. DuckDB スキーマ初期化（次節参照）

## 初期化・使い方（簡単な例）

以下は Python スクリプトからライブラリを利用する基本例です。

- DuckDB スキーマの初期化

```python
from kabusys.data import schema
from kabusys.config import settings

# ファイル DB を初期化（親ディレクトリが無ければ自動作成）
conn = schema.init_schema(settings.duckdb_path)

# インメモリ DB の場合
# conn = schema.init_schema(":memory:")
```

- 監査ログ（Audit）テーブルの初期化（既存接続へ追加）

```python
from kabusys.data import audit

audit.init_audit_schema(conn)
```

- 日次 ETL の実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）

```python
from kabusys.data import pipeline

result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- J-Quants から直接データ取得・保存を行う例

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# ID トークンの取得（settings.jquants_refresh_token を内部で使用）
id_token = jq.get_id_token()

# 指定期間・銘柄の株価を取得
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=..., date_to=...)

# 保存（conn は init_schema などで得た DuckDB 接続）
saved_count = jq.save_daily_quotes(conn, records)
```

- 品質チェックを個別に実行する例

```python
from kabusys.data import quality

issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

### ETL 実行時の設定オプション
- run_daily_etl の主な引数
  - target_date: ETL の対象日（省略で本日）
  - run_quality_checks: 品質チェックを行うか（デフォルト True）
  - spike_threshold: スパイク検出閾値（デフォルト 0.5 = 50%）
  - backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）
  - calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

## 主要モジュール説明（ファイル/ディレクトリ構成）

プロジェクトの主要ファイルは以下の通りです（抜粋）。詳しくは各モジュールを参照してください。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得 + 保存）
    - schema.py                   — DuckDB スキーマ定義と init_schema
    - pipeline.py                 — ETL パイプライン（差分取得・保存・品質チェック）
    - quality.py                  — データ品質チェック
    - audit.py                    — 監査ログ（signal/order_request/executions）初期化
  - strategy/
    - __init__.py                 — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                 — 発注・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                 — 監視/メトリクス（拡張ポイント）

（上記は現状の実装ファイル構成であり、将来的に戦略・発注・監視の具象実装を追加する想定です）

## 注意点 / 運用上のポイント

- 環境変数は `.env` / OS 環境変数から読み込まれます。OS 環境変数が優先され、`.env.local` は `.env` の上書きとして扱われます。
- J-Quants API のレート制限（120 req/min）を厳守するため内部でスロットリングを行っていますが、上位の処理でも大量リクエストを控える設計にしてください。
- DuckDB のスキーマは冪等に作成されます（CREATE TABLE IF NOT EXISTS 等）。ただし、スキーマ変更時はマイグレーションを検討してください。
- run_daily_etl は個別ステップの例外を捕捉して処理を続行します。戻り値の ETLResult の errors / quality_issues をチェックして運用判断を行ってください。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。ログの永続化ポリシーに注意してください。

## 例: 最小ワークフロー（まとめ）

1. .env を用意して必要なキーを設定
2. Python でスキーマを初期化
3. 日次 ETL を実行してデータを収集・保存
4. 品質チェック結果を監視、問題に応じてアラートや再取り込みを実施

## 開発・拡張ポイント

- strategy/ モジュールに戦略ロジックを実装し、signal を生成して signal_queue へ入れるフローを作成してください。
- execution/ モジュールに証券会社 API との接続ロジック（発注・約定取得）を実装し、audit / execution テーブルとの連携を実現してください。
- monitoring/ モジュールで Prometheus や Slack への通知、ジョブ監視を追加すると運用が容易になります。

---

README に不足している点や、特定機能（例: 発注連携、Slack 通知、定期実行のサンプルスクリプト等）のサンプルを追加したい場合は、どの部分を詳述するか教えてください。必要に応じてサンプルコードや運用手順を追記します。