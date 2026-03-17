# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS などから市場データ／ニュースを収集し、DuckDB に格納・品質チェックし、戦略・実行レイヤーへ供給することを主目的としています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の用途を想定した Python パッケージです。

- J-Quants API からの株価（日足）・財務データ・マーケットカレンダー取得
- RSS フィードからのニュース収集と記事 → 銘柄紐付け
- DuckDB を用いた3層（Raw / Processed / Feature）データベーススキーマの初期化・管理
- ETL（差分取得・保存・品質チェック）パイプライン
- マーケットカレンダー管理、夜間更新ジョブ
- 監査ログ（シグナル → 発注 → 約定までの追跡）用スキーマ

設計上のポイント:
- API レート制限・リトライ・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB への冪等保存（ON CONFLICT …）による安全なデータ更新
- SSRF 対策、XML パース時の安全対策（defusedxml）、受信サイズ制限等の堅牢性
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 機能一覧

- 環境変数 / .env 自動読み込み（プロジェクトルート検出、上書き制御あり）
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン取得 get_id_token（リフレッシュ対応）
  - 保存関数 save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB）
- RSS ニュース収集
  - fetch_rss（SSRF対策・gzip/サイズ制限・XML安全パース）
  - save_raw_news / save_news_symbols（冪等・トランザクション）
  - 銘柄コード抽出 extract_stock_codes
  - run_news_collection（複数ソースの統合ジョブ）
- DuckDB スキーマ管理
  - init_schema / get_connection（Raw / Processed / Feature / Execution のテーブルとインデックスを作成）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（まとめて実行、品質チェックを含む）
- マーケットカレンダー管理
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間更新ジョブ）
- 品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue 型による検出結果の集約
- 監査ログスキーマ
  - init_audit_schema / init_audit_db（signal_events, order_requests, executions 等）

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションに union | を使用しているため）
- システムに DuckDB のホイールがインストール可能であること

1. リポジトリをクローン（またはパッケージのルートへ移動）

2. 依存パッケージをインストール（例）
   - pip を使う場合:
     ```
     pip install duckdb defusedxml
     ```
   - 開発インストール（プロジェクトルートに pyproject.toml がある想定）:
     ```
     pip install -e .
     ```

   必要に応じて他の依存を追加してください（requests ではなく urllib を利用する設計ですが、環境により追加が必要な場合があります）。

3. 環境変数の設定
   - 必須（Settings で必須チェックされるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.git または pyproject.toml によりプロジェクトルートを検出）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データベース初期化
   - DuckDB を初期化してテーブルを作成します（例は後述の「使い方」参照）。

---

## 使い方（サンプル）

以下は基本的な Python からの利用例です。実行前に必要な環境変数を設定してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ディレクトリが自動作成されます
  ```

- 日次 ETL の実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を渡せます
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- マーケットカレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集（既知の銘柄コードセットがある場合の紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # sources を指定しないと DEFAULT_RSS_SOURCES が使われます
  known_codes = {"7203", "6758", "9432"}  # 例: 実際は DB から取得する
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 監査ログスキーマの初期化（監査用テーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # 既存の conn に追記します
  ```

- 直接 API を叩く（テストや詳細取得）
  ```python
  from kabusys.data import jquants_client as jq
  # id_token を直接取得（settings の JQUANTS_REFRESH_TOKEN を使用）
  id_token = jq.get_id_token()
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

ログレベルの設定は環境変数 LOG_LEVEL を使って制御します（例: export LOG_LEVEL=DEBUG）。

---

## よくあるトラブルシュート

- ValueError: 環境変数が設定されていない
  - settings が必須変数（JQUANTS_REFRESH_TOKEN など）を要求します。.env を用意するか環境変数をエクスポートしてください。

- .env が読み込まれない
  - パッケージは .git または pyproject.toml を基準にプロジェクトルートを検出して自動読み込みします。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
  - テストなどで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB への接続エラー / ファイル作成権限
  - init_schema() は親ディレクトリを自動作成しますが、ファイルシステムの権限がないと失敗します。パスと権限を確認してください。

- RSS 取得でサイズ超過や XML パース失敗
  - news_collector は MAX_RESPONSE_BYTES（デフォルト 10 MB）や defusedxml のパース例外で失敗時は空リストを返します。ログを確認して原因を特定してください。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要なファイル・モジュール構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント + DuckDB 保存
      - news_collector.py          — RSS 収集・前処理・DB保存
      - schema.py                  — DuckDB スキーマ定義 / init_schema
      - pipeline.py                — ETL パイプライン（差分更新・run_daily_etl）
      - calendar_management.py     — カレンダー管理 / 夜間更新ジョブ
      - audit.py                   — 監査ログスキーマ（signal/order/execution）
      - quality.py                 — データ品質チェック
    - strategy/
      - __init__.py
      (戦略関連モジュール置き場：未実装の雛形)
    - execution/
      - __init__.py
      (実行ブロック用モジュール置き場：未実装の雛形)
    - monitoring/
      - __init__.py
      (モニタリング関連：未実装の雛形)

---

## 開発メモ / 注意点

- settings では KABUSYS_ENV に対して "development", "paper_trading", "live" のみを許容します。 production 相当の振る舞い（実際の発注等）は is_live フラグ等で分岐させてください。
- J-Quants API はレート制限（120 req/min）を想定しており、モジュール内部で固定間隔スロットリングとリトライロジックを実装しています。
- DuckDB への書き込みは冪等操作（ON CONFLICT DO UPDATE / DO NOTHING）を多用しており、ETL の再実行に耐える設計です。
- ニュース収集では SSRF や XML Bomb に配慮していますが、公開環境でのネットワーク構成に応じて追加のプロキシ制御やタイムアウト設定を行ってください。

---

必要であれば README にサンプル .env.example、CI 実行方法、より詳しい API ドキュメント例（関数引数・戻り値の詳細）、あるいは戦略/実行インターフェース規約を追加できます。どの情報を追記しましょうか？