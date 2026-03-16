# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム用ライブラリです。データ取得・保存、スキーマ管理、データ品質チェック、監査ログなど、取引アルゴリズム実行に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次の目的で設計されたモジュール群です。

- J-Quants API などから市場データ（株価日足、財務データ、マーケットカレンダー等）を取得するクライアント
- 取得データを DuckDB に冪等に保存するスキーマと初期化機能
- データ品質チェック（欠損・スパイク・重複・日付不整合）機能
- 発注〜約定までを追跡する監査ログ用スキーマ
- 環境変数ベースの設定管理（.env の自動読み込みを含む）

設計上の注意点：
- J-Quants API 呼び出しはレート制限（120 req/min）に従い、リトライやトークン自動リフレッシュを考慮
- すべてのタイムスタンプは UTC を前提に扱う
- DuckDB への保存は ON CONFLICT DO UPDATE を用いて冪等性を確保

---

## 機能一覧

主な機能:

- 環境設定管理（自動 .env 読み込み、必須環境変数チェック）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応、レートリミット・リトライ・トークン管理）
  - 財務データ（四半期 BS/PL）取得
  - マーケットカレンダー取得
  - トークン取得（refresh token → id token）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal_events / order_requests / executions）のスキーマと初期化
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合）
- ロギングレベルと実行環境（development / paper_trading / live）を環境変数で制御

---

## 要件

- Python 3.10+
- 必須 Python パッケージ（例）:
  - duckdb
- ネットワークアクセス（J-Quants API など）および各種認証情報

（必要に応じて pyproject.toml / requirements.txt をプロジェクトに追加してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb
   # 他の依存があればここに追加
   ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を置くことで自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
- KABU_API_PASSWORD : kabuステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意／デフォルト:
- KABUSYS_ENV : 実行環境（development / paper_trading / live）、デフォルト `development`
- LOG_LEVEL : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）、デフォルト `INFO`
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化するフラグ（`1` 等）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: `http://localhost:18080/kabusapi`）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH : SQLite（監視用）ファイルパス（デフォルト: `data/monitoring.db`）

.env の読み込みルール（優先順位）
- OS 環境変数 > .env.local > .env
- パーシングはシェル形式に近い仕様（export 対応、クォート・エスケープ・コメント処理あり）

---

## 使い方

いくつかの基本的な利用例を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # ファイル作成・テーブル作成
  # 既存 DB に接続するだけなら:
  # conn = get_connection("data/kabusys.duckdb")
  ```

- J-Quants のトークン取得（明示的に）
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を参照して取得
  ```

- 日次株価を取得して DuckDB に保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # 例: 2023-01-01 から 2023-12-31 までのデータを取得して保存
  from datetime import date
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved_count = save_daily_quotes(conn, records)
  print(f"保存件数: {saved_count}")
  ```

- 財務データ / マーケットカレンダーの取得と保存
  ```python
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  records = fetch_financial_statements(code="7203")  # 銘柄コード例
  save_financial_statements(conn, records)

  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- 監査ログスキーマ初期化（既存の DuckDB 接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema で得た DuckDB 接続が想定
  ```

- 監査専用 DB を新規作成する場合
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)  # target_date を指定するとその日のみチェック
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
      for row in issue.rows:
          print(row)
  ```

注意点:
- J-Quants クライアントはモジュール内で ID トークンをキャッシュします。401 受信時は自動でリフレッシュして一度だけリトライします。
- レート制限（120 req/min）を内部で尊重するため、高頻度の連続実行は意図した待ち時間が発生します。

---

## ディレクトリ構成

主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py             # 環境変数・設定管理（.env 自動読み込み等）
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント（取得・保存ロジック）
    - schema.py          # DuckDB スキーマ定義・初期化
    - audit.py           # 監査ログスキーマ（signal/order/execution）
    - quality.py         # データ品質チェック
  - strategy/
    - __init__.py         # 戦略関連モジュール（将来的な実装領域）
  - execution/
    - __init__.py         # 発注・ブローカー連携（将来的な実装領域）
  - monitoring/
    - __init__.py         # 監視・メトリクス周り（将来的な実装領域）

---

## 補足 / 注意事項

- 型ヒントや構文（| を使う Union）は Python 3.10 以降を想定しています。
- `.env` のパースはシェル互換の細かなケース（クォート・エスケープ・コメント）に対応していますが、特殊ケースは注意してください。
- DuckDB のテーブル定義や制約（CHECK, PRIMARY KEY, FOREIGN KEY）は、運用設計や外部システムとの連携を想定して厳密に定義されています。マイグレーションやスキーマ変更は慎重に行ってください。
- ライセンスやコントリビュート方針はリポジトリに合わせて別途追加してください。

---

何か追加したいセクション（例: CI、テスト例、詳細な API リファレンス）や、日本語表現の調整があれば教えてください。