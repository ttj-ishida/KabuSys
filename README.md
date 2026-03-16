# KabuSys — 日本株自動売買システム

軽量なデータ基盤とETL、監査ログ、J‑Quants API クライアントなどを備えた日本株の自動売買システムの骨組みです。本リポジトリは以下を提供します。

- J‑Quants API からの時系列・財務・カレンダー取得クライアント（リトライ・レート制御・トークン自動更新対応）
- DuckDB を用いたスキーマ定義・初期化
- 差分ETLパイプライン（市場カレンダー、株価日足、財務データ）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（戦略→シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env / 環境変数の自動読み込み）

バージョン: 0.1.0

---

## 主な機能

- J‑Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（デフォルト 120 req/min）を守る固定間隔スロットリング
  - 408/429/5xx に対する指数バックオフ再試行、401 時のリフレッシュ→再試行を1回自動実行
  - 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を防止
  - DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の 4 層スキーマ
  - 監査ログ用のテーブル群（signal_events、order_requests、executions）
  - 必要なインデックスも定義

- ETL パイプライン
  - 差分更新（最終取得日から差分を算出、backfill により数日前から再取得）
  - カレンダーは先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を集約して返す

- 品質チェック
  - 各チェックは QualityIssue のリストを返し、呼び出し側が重大度（error/warning）に基づいて判断可能

- 設定管理
  - プロジェクトルートにある `.env` / `.env.local` を自動ロード（OS 環境優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば自動ロードを無効化可能

---

## 必要条件 / 依存関係

- Python 3.10 以上（typing の新構文および型注釈を使用）
- duckdb
- （実運用では）J‑Quants アクセス権、kabu API、Slack トークンなど

※ 実際のパッケージ依存は pyproject.toml / requirements.txt に従ってください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（リポジトリURL）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  または Windows の場合 .venv\Scripts\activate

3. 依存関係をインストール
   - pip install -r requirements.txt
   - またはパッケージ化されていれば: pip install -e .

4. .env を準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動で読み込まれます。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
   - 任意 / デフォルトがある変数
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|... （デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化
     - KABUSYS の DB パス:
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)

   - .env のパーシングはシェル風のコメント・クォート・export 形式に対応しています。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから初期化します（例は次節参照）。

---

## 使い方（例）

以下は最小限の使用例です。実際はログ設定や例外ハンドリング、スケジューラ（cron/airflow）からの呼び出しなどを組み合わせてください。

1) DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

db_path = settings.duckdb_path  # .env の DUCKDB_PATH を利用
conn = init_schema(db_path)
```

2) 監査ログテーブルの追加入力（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

3) J‑Quants のトークン取得（明示的に）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使って POST 実行
```

4) 日次 ETL を実行（単日）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

5) ETL の個別呼び出し（価格のみ等）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

6) 品質チェックを単独で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

ノート:
- run_daily_etl は内部で market_calendar → prices → financials → quality の順で実行します。各ステップは独立してエラーハンドリングされ、問題があっても他のステップは継続実行されます。
- J‑Quants クライアントは ID トークンをモジュール内キャッシュしており、ページネーションや自動リフレッシュを考慮しています。
- save_* 関数は ON CONFLICT DO UPDATE により冪等にデータを保存します。

---

## 環境変数（一覧）

最低限設定が必要なキー：
- JQUANTS_REFRESH_TOKEN — J‑Quants の refresh token（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル（必須）

任意（デフォルト値あり）：
- KABUSYS_ENV — 開発環境：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

---

## ディレクトリ構成

プロジェクトは src 配下にパッケージとして配置されています。主要ファイルを抜粋すると次のようになります。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定読み込みロジック
    - data/
      - __init__.py
      - jquants_client.py      — J‑Quants API クライアント（取得・保存・リトライ・レート制御）
      - schema.py              — DuckDB スキーマ定義と初期化
      - pipeline.py            — ETL パイプライン（差分更新、品質チェック）
      - audit.py               — 監査ログ（シグナル→発注→約定のトレーサビリティ）
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py            — （戦略モジュール用プレースホルダ）
    - execution/
      - __init__.py            — （発注実行モジュール用プレースホルダ）
    - monitoring/
      - __init__.py            — （モニタリングモジュール用プレースホルダ）

上記以外に設定ファイル、ドキュメント（DataPlatform.md、DataSchema.md 等）がある想定です。

---

## 設計上の注意点 / 補足

- 型注釈・ドキュメンテーション文字列は各関数に豊富にあります。実装の詳細は該当モジュールの docstring を参照してください。
- J‑Quants API はレート制限（120 req/min）や 401 によるトークンリフレッシュなどの挙動に対応済みです。429 の場合 Retry‑After ヘッダを尊重します。
- ETL は差分更新とバックフィルにより API の後出し修正を吸収する設計になっています（デフォルト backfill 3 日）。
- データ品質チェックは Fail‑Fast にならず、すべての問題を収集して呼び出し元に返します。致命的問題の判断は呼び出し元コンポーネントに委ねられます。
- 監査ログは削除しない前提で設計されており、order_request_id が冪等キーとして機能します。

---

## 最後に

このリポジトリは自動売買システムのコアとなるデータ基盤と基礎ライブラリを提供します。実運用にはさらに以下を検討してください。

- 実際のブローカー連携（kabuステーション等）とエラーハンドリング／再送ロジック
- 永続的なログ収集・可観測性（Prometheus / Grafana 等）
- CI/CD・テスト（ユニット・統合テスト）、および自動デプロイ
- データバックアップとリストア戦略

ご質問や追加したいドキュメント項目があれば教えてください。README を用途に合わせて拡張します。