# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（開発初期版）
バージョン: 0.1.0

このプロジェクトは、J-Quants API から市場データ（株価日足、財務、マーケットカレンダー等）を取得し、DuckDB に保存・整備して戦略層や発注層に渡すための基盤モジュール群を提供します。品質チェック、ETL パイプライン、監査ログ用スキーマなどを含みます。

---

## 主な機能

- 環境変数 / 設定読み込み（.env 自動ロード、Settings クラス）
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）と固定間隔スロットリングを実装
  - 再試行（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 冪等性を考慮した保存ロジック（ON CONFLICT DO UPDATE）

---

## 必要な環境変数 (.env)

プロジェクトは以下の環境変数を参照します。少なくとも必須項目を .env に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack チャネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL      — kabuAPI のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（monitoring 用）パス（既定: data/monitoring.db）
- KABUSYS_ENV            — 環境: development / paper_trading / live（既定: development）
- LOG_LEVEL              — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）

テスト用:
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 で無効化）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_ref_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python バージョン
   - Python 3.10+ を推奨（PEP 604 の型記法（|）を使用）

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須: duckdb
   - 例:
     - pip install duckdb
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

4. 環境変数の設定
   - リポジトリルートに .env を作成するか、必要な環境変数を OS に設定します。
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡易ガイド）

以下は主な操作例です。Python スクリプトや REPL から利用できます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルベース DB を初期化（必要に応じて親ディレクトリを作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 既存 DB 接続を取得
```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

3) 日次 ETL の実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

4) J-Quants の直接呼び出し例（ID トークン取得、データ取得）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

5) 監査ログ（監査スキーマの初期化）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の DuckDB 接続へ監査テーブルを追加
```

注意事項:
- run_daily_etl は内部で品質チェック（data.quality.run_all_checks）を呼びます。チェック結果は ETLResult.quality_issues に格納されます。
- J-Quants API はレート制限（120 req/min）を守るためモジュール内でスロットリングしています。
- get_id_token はリフレッシュトークンから ID トークンを取得します。401 を検知すると自動リフレッシュして再試行します。

---

## 主要 API 概要

- kabusys.config.settings
  - Settings クラスを通じて環境変数にアクセスします（jquants_refresh_token、kabu_api_password、duckdb_path 等）。
  - 設定値のバリデーション（例: KABUSYS_ENV の有効値チェック）を行います。

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)  — DuckDB の raw_prices へ冪等保存
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
  - スキーマは Raw / Processed / Feature / Execution 層を提供

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult クラスで実行結果と品質問題・エラーを確認可能

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - QualityIssue データクラスにより詳細を受け取れる

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

プロジェクトの主要ファイル／ディレクトリ（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py               — J-Quants API クライアント（取得・保存）
      - schema.py                       — DuckDB スキーマ定義・初期化
      - pipeline.py                     — ETL パイプライン
      - audit.py                        — 監査ログスキーマ
      - quality.py                      — データ品質チェック
    - strategy/
      - __init__.py                      — 戦略関連パッケージ入口（未実装の余地）
    - execution/
      - __init__.py                      — 実行（発注）関連（未実装の余地）
    - monitoring/
      - __init__.py                      — 監視系（未実装の余地）

ファイルごとの責務はソースコード冒頭の docstring に詳細が記載されています。

---

## 運用上の注意点 / 設計上のポイント

- API レート制限: jquants_client 内で固定間隔（60/120 秒）でスロットリングしています。
- リトライ: 408/429/5xx 等のエラーで指数バックオフによる再試行、401 ではトークンを自動更新して再試行します。
- 冪等性: DuckDB への保存処理は ON CONFLICT DO UPDATE により同一主キーでの上書きを行い冪等性を確保しています。
- Look-ahead 防止: 取得時点の fetched_at を UTC で記録します。取得時刻のトレーサビリティを保つことで将来データ混入リスクを低減します。
- 品質チェックは Fail-Fast ではなく全件収集型: 問題を全て収集して戻り値で通知します。呼び出し側が停止基準を決めてください。

---

## 開発 / 貢献

- テストや CI、パッケージング（pyproject.toml など）はこのスニペットには含まれていません。実運用や外部公開する場合は以下を整備してください:
  - requirements.txt / pyproject.toml
  - ユニットテスト（特に ETL / 品質チェック / 保存処理）
  - ロギング・監視の統合
  - セキュリティ（秘密情報の管理・ローテーション）
- バグ報告／改善提案は Issue を通じてお願いします（リポジトリがある場合）。

---

README は以上です。必要であれば以下を追加できます:
- 実際の .env.example ファイルテンプレート
- 詳細な ETL ワークフロー図、SQL クエリの説明
- 実行スケジュール（cron / Airflow / prefect など）例
- 実際の依存関係一覧（requirements）やセットアップスクリプト

追加で欲しい項目があれば教えてください。