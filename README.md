# KabuSys

バージョン: 0.1.0

日本株向けの自動売買基盤ライブラリ。J-Quants / kabuステーション 等の外部 API からデータを取得して DuckDB に永続化し、戦略・実行・監視の各レイヤーで利用できるように設計されています。データ取得はレート制限・リトライ・トークンリフレッシュ等を備え、監査ログ（トレーサビリティ）を重視したスキーマを提供します。

主な設計方針:
- API レート制限（J-Quants: 120 req/min）を守るための RateLimiter を実装
- リトライ（指数バックオフ）、401（トークン期限切れ）自動リフレッシュ対応
- Look-ahead バイアス防止のため取得時刻（UTC）を記録
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で安全に上書き可能
- 発注〜約定までの監査ログを別モジュールで管理

---

## 機能一覧

- J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - リトライ、レート制御、トークン自動リフレッシュ対応
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - インデックス定義、初期化用関数 init_schema
- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査専用スキーマ
  - init_audit_schema / init_audit_db を提供
- 環境変数管理
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定を取得する Settings クラス（settings インスタンス）
- （将来的に）戦略、実行、モニタリング用のパッケージ構成（プレースホルダあり）

---

## 要件

- Python 3.10+
- 依存ライブラリ（最低限）
  - duckdb
- 標準ライブラリ: urllib, json, datetime など

（パッケージ化時は setup/pyproject の依存宣言に従ってください）

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb

   （パッケージが pyproject.toml / setup を提供している場合）
   pip install -e .

4. 環境変数を設定
   プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は .env を上書き）。
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_station_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567

   任意 / デフォルトを持つ設定:
   - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db   （デフォルト）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （デフォルト）

   例 .env:
   JQUANTS_REFRESH_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXX
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単なコード例）

Python REPL / スクリプト例を示します。

- 設定（settings）の利用
  from kabusys.config import settings
  print(settings.duckdb_path)   # Path object
  print(settings.is_live)       # True/False

- DuckDB スキーマを初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成してテーブルを作る

- J-Quants データ取得と保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # 例: ある銘柄の過去1ヶ月分を取得して保存
  import datetime
  today = datetime.date.today()
  one_month_ago = today - datetime.timedelta(days=30)

  records = fetch_daily_quotes(code="7203", date_from=one_month_ago, date_to=today)
  saved = save_daily_quotes(conn, records)
  print(f"{saved} レコード保存しました")

- 財務データ / マーケットカレンダーの取得と保存
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  fin = fetch_financial_statements(code="7203")
  saved_fin = save_financial_statements(conn, fin)

  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
  cal = fetch_market_calendar()
  saved_cal = save_market_calendar(conn, cal)

- id_token を直接取得（必要な場面で）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して POST

- 監査ログスキーマ追加
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema の返り値

注意点:
- J-Quants リクエストは内部でレート制御とリトライを行います。
- save_* 関数は冪等（既存行があれば UPDATE）なので再実行可能です。
- すべてのタイムスタンプは UTC で扱われます（監査 DB は TimeZone='UTC' に設定）。

---

## 設定一覧（環境変数）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack Bot トークン（通知等に使用）
- SLACK_CHANNEL_ID: Slack チャネル ID

オプション / デフォルト:
- KABUSYS_ENV: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

バリデーション:
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ ValueError
- LOG_LEVEL は上記リストにない値なら ValueError

---

## 内部設計のポイント（開発者向けメモ）

- jquants_client:
  - _RateLimiter による固定間隔スロットリング（120 req/min、min interval = 60/120 sec）
  - _request は最大 3 回のリトライ（指数バックオフ）。HTTP 408, 429 と 5xx をリトライ対象
  - 401 受信時は一度だけ get_id_token によりトークンを更新して再試行
  - ページネーション対応（pagination_key を利用）
  - fetched_at を UTC ISO8601（Z）で記録
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換）

- schema / audit:
  - Raw / Processed / Feature / Execution の多層スキーマを DuckDB に展開
  - テーブル作成は冪等（CREATE TABLE IF NOT EXISTS）
  - 監査ログのテーブルは削除しない前提で FOREIGN KEY ON DELETE RESTRICT を想定
  - 監査 DB は UTC タイムゾーンで保存する（init_audit_schema で SET TimeZone='UTC'）

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py                 # パッケージ初期化（__version__ 等）
    - config.py                   # 環境変数・設定管理（settings）
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
      - schema.py                 # DuckDB スキーマ定義・初期化（init_schema 等）
      - audit.py                  # 監査ログスキーマ（init_audit_schema 等）
      - audit.py
    - strategy/
      - __init__.py               # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py               # 実行/ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py               # 監視・モニタリング（拡張ポイント）

---

## 例: よくあるワークフロー

1. 環境を用意し .env を配置
2. DuckDB スキーマを初期化: init_schema(settings.duckdb_path)
3. データを定期的に取得して保存（cron / Airflow 等でスケジューリング）
   - fetch_daily_quotes → save_daily_quotes
   - fetch_financial_statements → save_financial_statements
   - fetch_market_calendar → save_market_calendar
4. Feature 層を生成して戦略を実行（strategy モジュールに実装）
5. シグナルを発行し、order_requests を作成 → broker へ送信 → executions を保存
6. 監査ログは audit スキーマで一貫して記録

---

## 今後の拡張案

- kabuステーション実行エージェント（注文送信・コールバック処理）
- 戦略モジュールのテンプレートとバックテストツール
- Slack/監視アラート統合の拡充
- CI 用の DB 初期化スクリプト、ユニットテストの整備

---

この README はコードベースの現状（src/kabusys 以下）に基づいて作成しています。追加の利用シナリオや API 連携は今後の実装で拡張してください。