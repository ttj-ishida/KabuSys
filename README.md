# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けの基盤ライブラリです。データ取得・永続化（DuckDB）、監査ログ（監査用スキーマ）、設定管理、J-Quants API クライアントなど、売買戦略の実装と実行基盤に必要な共通機能を提供します。

---

## 概要

- J-Quants API から株価・財務・マーケットカレンダー等を取得し、DuckDB に永続化します。
- データレイヤー（Raw / Processed / Feature / Execution）を想定したスキーマを提供します。
- 監査（Audit）用のテーブル群を別途初期化でき、シグナル → 発注 → 約定に至るトレーサビリティを保証します。
- 環境変数ベースの設定管理を備え、.env/.env.local の自動読み込み（プロジェクトルート検出）に対応します。
- API 呼び出しはレート制限・リトライ・トークン自動リフレッシュ等を組み込んだ堅牢な実装です。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - 必須環境変数の取得（未設定時は例外）
  - 環境 (development / paper_trading / live) とログレベルの検証

- データ取得（J-Quants クライアント）
  - 日足（OHLCV）取得（fetch_daily_quotes）
  - 財務データ（四半期 BS/PL）取得（fetch_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar）
  - レート制限（120 req/min）・指数バックオフリトライ・401 時トークン自動リフレッシュ
  - 取得タイムスタンプ（fetched_at）を UTC で記録（Look-ahead Bias 防止）

- 永続化（DuckDB）
  - raw / processed / feature / execution 層のテーブル DDL 定義
  - init_schema(db_path) による初期化（冪等）
  - インデックス定義・外部キーを考慮した作成順
  - save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB への冪等保存ロジック（ON CONFLICT DO UPDATE）

- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査用テーブル群
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化
  - 発注の冪等キー（order_request_id）や broker_execution_id を考慮した設計

---

## 動作要件

- Python 3.10 以上（型ヒントに | を使用）
- 依存ライブラリ（例）
  - duckdb
  - （標準ライブラリのみで動作する箇所も多いですが、実運用では追加パッケージが必要になる場合があります）

requirements.txt がリポジトリに無い場合は、最低限次をインストールしてください:

pip install duckdb

（J-Quants の認証・HTTP に関する追加の依存は標準ライブラリで実装されています）

---

## セットアップ手順

1. リポジトリをクローンする

   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境を作成して有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 必要なパッケージをインストール

   pip install duckdb

   （プロジェクトで requirements.txt があればそれを使用してください）
   pip install -r requirements.txt

4. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml を基準）に `.env` または `.env.local` を配置すると自動でロードされます。
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャネル ID

   省略時のデフォルト値（任意）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - KABU_API_BASE_URL: http://localhost:18080/kabusapi
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - LOG_LEVEL: INFO

   注意: Settings クラスは未設定の必須環境変数について ValueError を送出します。

---

## 使い方（サンプル）

以下は基本的な利用例です。実際のアプリケーションではログ設定や例外ハンドリングを適切に行ってください。

- DuckDB スキーマ初期化

  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成してスキーマを初期化

  # インメモリ DB を使う場合
  conn = init_schema(":memory:")

- J-Quants から日足を取得して保存

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # 銘柄コードや期間を指定して取得
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

  # DuckDB に保存（冪等）
  saved = save_daily_quotes(conn, records)
  print(f"{saved} 件を保存しました")

- 財務データ / マーケットカレンダーの取得と保存

  records = fetch_financial_statements(code="7203")
  save_financial_statements(conn, records)

  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)

- 監査スキーマの初期化（既存の DuckDB 接続に追加）

  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)  # conn は init_schema() で得た接続等

- 監査専用 DB を別ファイルとして初期化

  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- 設定値を参照

  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.is_live, settings.log_level)

---

## 実装上のポイント / 注意事項

- J-Quants クライアントはレート制限（120 req/min）を守るため固定間隔のスロットリングを行います。
- HTTP エラー時は指数バックオフで最大 3 回リトライ（408, 429, >=500 を対象）。429 の場合は Retry-After ヘッダを優先します。
- 401 が返った場合はトークンを自動リフレッシュして 1 回だけ再試行します（無限再帰は防止）。
- 取得データには fetched_at（UTC）を付与して、データを「いつ知り得たか」を追跡できるようにしています。
- DuckDB への保存関数は ON CONFLICT DO UPDATE により冪等性を保っています。
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テスト等で自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB の初期化（init_schema）は必ず一度実行してテーブルを作成してください。get_connection() は既存 DB への接続のみを行い、スキーマ作成は行いません。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py            (パッケージ初期化、バージョン: 0.1.0)
    - config.py              (環境変数・設定管理、自動 .env 読み込み)
    - data/
      - __init__.py
      - jquants_client.py    (J-Quants API クライアント、取得・保存ロジック)
      - schema.py            (DuckDB スキーマ定義・初期化)
      - audit.py             (監査ログスキーマ定義・初期化)
      - audit_db (関連関数）
      - ...
    - strategy/
      - __init__.py
      - ...                  (戦略層用モジュール置き場)
    - execution/
      - __init__.py
      - ...                  (発注・執行関連モジュール置き場)
    - monitoring/
      - __init__.py
      - ...                  (監視/メトリクス用)

---

## よくあるトラブルシューティング

- ValueError: 環境変数 'X' が設定されていません。
  - 必須の環境変数が不足しています。`.env` を作成するか環境変数を設定してください。

- J-Quants API の認証失敗（401 が出る）
  - JQUANTS_REFRESH_TOKEN が無効、または期限切れの可能性があります。トークンを確認してください。

- duckdb がインストールされていない
  - pip install duckdb を実行してください。

- 自動 .env 読み込みが動かない
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索します。テスト環境や配布後にこの仕組みが不要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README を拡張します。使い方の具体的なユースケース（戦略実装例、発注フロー例、Slack 通知の利用例等）が必要であれば教えてください。