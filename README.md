# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）、および将来的な戦略・発注モジュールの基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を中心に設計された内部ライブラリです。

- J-Quants API からの市場データ（株価日足・財務情報・マーケットカレンダー）取得
- DuckDB を用いたスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブル（シグナル→発注要求→約定 のトレーサビリティ）
- 環境変数管理（.env の自動ロード、必要なキーの検証）
- レート制御、リトライ、ID トークン自動リフレッシュ等の API クライアント実装

戦略（strategy）や発注（execution）モジュールは拡張ポイントとして用意されています（現状はパッケージ化のための初期ファイルのみ）。

---

## 機能一覧

- 環境設定管理
  - プロジェクトルートの .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数を Settings オブジェクト経由で安全に取得

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務四半期データ、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔 throttling）
  - リトライ（指数バックオフ、最大3回）、401 時のトークン自動リフレッシュ
  - ページネーション対応、取得時刻（fetched_at）の記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - インデックス作成、初期化ユーティリティ（init_schema / get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次ジョブ run_daily_etl（カレンダー→株価→財務→品質チェック）
  - 差分更新の自動計算、バックフィルオプション
  - 品質チェック結果を収集して ETLResult として返却

- 品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欄）検出
  - 前日比スパイク検出（閾値指定可）
  - 主キー重複検出
  - 日付不整合（未来日付、非営業日に相当するデータ）

- 監査ログ（kabusys.data.audit）
  - シグナル／発注要求／約定を監査用テーブルに保存するDDLと初期化関数
  - 発注要求は冪等キー（order_request_id）を想定

---

## 必要条件

- Python 3.10 以上（型注釈に `X | None` を使用しているため）
- duckdb（データ永続化に必須）
- 標準ライブラリ（urllib, json, datetime, logging など）

pip での依存インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

（プロジェクト配布で setup 或いは poetry を用意する場合は `pip install -e .` を想定できます）

---

## 環境変数（主なもの）

KabuSys はいくつかの環境変数を参照します。`.env` や `.env.local` をプロジェクトルートに置くと自動で読み込まれます（CWD ではなくソースファイル位置を基準にプロジェクトルートを探します）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能利用時）
- SLACK_BOT_TOKEN — Slack 通知用（未使用箇所がある場合あり）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用DB）パス（デフォルト: data/monitoring.db）

自動 .env ロードを抑止する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

`.env.example` を参照して必要なキーを用意してください（本リポジトリに example があればそれに合わせてください）。

---

## セットアップ手順（ローカル）

1. リポジトリのクローン
   - git clone ...

2. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb
   - （将来的に requirements.txt / pyproject.toml を追加する想定）

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成してキーを設定
     例（最小）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=yyyyyyyy
     SLACK_BOT_TOKEN=zzzzzzzz
     SLACK_CHANNEL_ID=C01234567
     ```

4. DuckDB の初期化（最初の一度）
   - Python REPL やスクリプトで init_schema を呼ぶ:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)
     conn.close()
     ```

---

## 使い方（基本例）

- 設定の参照:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.env, settings.is_live)
  ```

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # :memory: も可
  ```

- 監査ログテーブルの初期化（既存接続に追加）:
  ```python
  from kabusys.data import audit
  audit.init_audit_schema(conn)
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  conn.close()
  ```

- J-Quants の株価を個別にフェッチして保存:
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  from kabusys.config import settings
  conn = schema.get_connection(settings.duckdb_path)
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 品質チェックを単独で実行:
  ```python
  from kabusys.data import quality, schema
  from kabusys.config import settings
  conn = schema.get_connection(settings.duckdb_path)
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意:
- API にはレート制限とリトライロジックが実装されていますが、運用時はさらにバックオフやスロットリングの考慮が必要です。
- run_daily_etl は内部で例外を捕捉しつつ進め、結果オブジェクトにエラーや品質問題を収集します。運用側でログやアラート処理を実装してください。

---

## ディレクトリ構成

以下は主要ファイルのツリー（パッケージの一部）です:

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境設定読み込み・Settings
    - execution/
      - __init__.py           — 発注 / 約定ロジックの拡張ポイント
    - strategy/
      - __init__.py           — 戦略モジュールの拡張ポイント
    - monitoring/
      - __init__.py           — 監視・メトリクスの拡張ポイント
    - data/
      - __init__.py
      - jquants_client.py     — J-Quants API クライアント（取得 + DuckDB 保存）
      - schema.py             — DuckDB スキーマ定義と初期化
      - pipeline.py           — ETL パイプライン（差分取得・保存・品質チェック）
      - audit.py              — 監査ログ（シグナル→発注→約定のトレーサビリティ）
      - quality.py            — データ品質チェック

---

## 実運用上の注意点

- 環境（KABUSYS_ENV）に `live` を設定すると実際の発注を行うモジュールが有効になる想定です。発注機能を有効にする前に入念なテストを行ってください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップや移行ポリシーを検討してください。
- J-Quants トークンや kabu API の資格情報は厳重に管理し、公開リポジトリに含めないでください。
- README のサンプルでは最低限の使い方を示しています。運用スクリプトや scheduler（cron / Airflow 等）への組込を推奨します。

---

もし README に追加したい内容（CI / テスト手順、具体的な .env.example、デプロイ手順、API レート制御の詳細設定など）があれば教えてください。必要に応じて追記します。