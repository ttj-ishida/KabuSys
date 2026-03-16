# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株向けのデータ基盤 / ETL / 監査ログ基盤を備えた自動売買システムのコアライブラリです。  
主に J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に格納して品質チェックを行う ETL パイプラインを提供します。発注・監査（audit）用のスキーマも含まれ、戦略や実行層と組み合わせて利用できます。

- Python 3.10+
- 主な依存: duckdb（その他標準ライブラリ: urllib, json, logging, datetime 等）

## 機能一覧

- J-Quants API クライアント
  - 日足（OHLCV）のページネーション取得
  - 四半期財務データの取得
  - JPX マーケットカレンダーの取得
  - レート制限（120 req/min）・リトライ（指数バックオフ）・401 の自動トークンリフレッシュに対応
  - 取得時刻（fetched_at）を UTC で記録（look-ahead bias のトレーサビリティ確保）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の 3 層（+監査）テーブル定義
  - 冪等性を考慮した INSERT（ON CONFLICT DO UPDATE）
  - インデックス定義付き
- ETL パイプライン
  - 差分取得（最終取得日を基に未取得分のみ取得）
  - backfill による数日前からの再取得で API の後出し修正を吸収
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果（ETLResult）の構造化出力
- データ品質チェック（quality モジュール）
  - 欠損データ検出
  - スパイク（前日比）検出
  - 主キー重複検出
  - 日付不整合（未来日付・非営業日データ）検出
- 監査ログ（audit モジュール）
  - シグナル生成、発注要求、約定をトレースする監査スキーマ
  - 冪等キー (order_request_id / broker_execution_id) を利用した追跡

## 必要な環境変数（主なもの）

このライブラリは環境変数 / .env ファイルから設定を読み込みます（自動読込あり）。必須のものは以下：

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

その他（任意 / デフォルトあり）:

- KABUSYS_ENV — 実行環境（development | paper_trading | live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` および `.env.local` を自動で読み込みます。
- OS 環境変数より .env を上書きしないよう保護します。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースは export 文やクォート、コメント等に対応します。

## セットアップ手順

1. Python とパッケージを用意
   - Python 3.10 以上を推奨
   - 依存パッケージをインストール（例）:
     pip install duckdb

   （プロジェクトに pyproject/requirements がある場合はそちらを使用してください）

2. ソースを配置 / インストール
   - 開発時:
     pip install -e .
   - あるいは直接ソースを使う（PYTHONPATH に src を含める等）

3. .env を作成（プロジェクトルート）
   例:
   JQUANTS_REFRESH_TOKEN="your_refresh_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV="development"

4. DuckDB スキーマ初期化
   - Python REPL あるいはスクリプトから初期化できます（下記「使い方」を参照）。

## 使い方（簡易ガイド）

以下は主要な操作例です。

1) 必要なモジュールの読み込みとログ設定（簡易例）

```python
import logging
from kabusys.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level))
```

2) DuckDB のスキーマ初期化

```python
from kabusys.data.schema import init_schema
# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
```

- ":memory:" を渡すとインメモリ DB が使えます:
  conn = init_schema(":memory:")

3) 監査ログスキーマを追加する（必要な場合）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

4) 日次 ETL 実行

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行し、ETLResult を返します。
- ETLResult には fetched/saved 数や品質チェック結果（QualityIssue のリスト）、エラーメッセージが含まれます。

5) J-Quants の個別取得例

```python
from kabusys.data import jquants_client as jq

# 特定銘柄の日足取得
records = jq.fetch_daily_quotes(code="7203", date_from=..., date_to=...)

# 取得データを DuckDB に保存
saved = jq.save_daily_quotes(conn, records)
```

6) 品質チェックの単独実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=..., spike_threshold=0.5)
for i in issues:
    print(i)
```

## よく使う API（モジュールと主な関数）

- kabusys.config
  - settings: 環境変数ラッパー（settings.jquants_refresh_token, settings.duckdb_path 等）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.quality
  - run_all_checks(conn, ...)
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

## 設計上のポイント（運用メモ）

- レート制限: J-Quants は 120 req/min を想定。モジュール内で固定間隔スロットリングを実装しています。
- 再試行: ネットワーク障害や 429/408/5xx に対して指数バックオフで最大 3 回リトライ。
- トークンリフレッシュ: 401 を受けた場合はリフレッシュトークンから ID トークンを自動更新して 1 回再試行します。
- 取得トレース: 各 raw レコードは fetched_at（UTC）を付与し、「いつシステムがそのデータを知り得たか」を追跡できます。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を使って冪等化されています。
- 品質チェックは Fail-Fast を採らず、全チェックを実行して問題を収集します。呼び出し側が重大度に応じて停止/通知を行ってください。

## ディレクトリ構成

（リポジトリの src 配下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント + 保存ロジック
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
      - quality.py             # データ品質チェック
      - audit.py               # 監査ログ（signal / order_request / executions）
      - pipeline.py
      - audit.py
    - strategy/
      - __init__.py
      # 戦略関連コード（展開予定）
    - execution/
      - __init__.py
      # 発注/実行関連コード（展開予定）
    - monitoring/
      - __init__.py
      # 監視/可観測性関連（展開予定）

## 例: フルワークフロー（簡単なスクリプト）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化
conn = init_schema(settings.duckdb_path)

# 日次 ETL 実行
result = run_daily_etl(conn)
print(result.to_dict())
```

## トラブルシューティング

- 環境変数未設定:
  - settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）を参照すると ValueError が発生します。`.env.example` を参考に .env を用意してください。
- .env が読み込まれない:
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続 / DDL エラー:
  - init_schema() を通してスキーマを初期化してください。必要に応じて権限や親ディレクトリ存在を確認してください。

---

この README はコードベースの現状（ETL、データ品質、監査部分）に基づいて作成しています。戦略や発注（execution / strategy / monitoring）モジュールはインターフェースの足場が用意されており、運用ニーズに応じて実装・拡張してください。必要であれば README の整備（CLI 例、Docker 化、CI ワークフロー等）を追加で作成できます。