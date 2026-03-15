# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（プロトタイプ）

このリポジトリは、J-Quants や kabuステーション等からデータを取得し、DuckDB に格納して戦略や発注ロジックに利用するための基盤的なモジュール群を提供します。監査ログやスキーマ定義、API クライアント、環境設定周りのユーティリティを含みます。

## 特徴（要点）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - ページネーション対応、取得日時（fetched_at）を UTC で記録
  - RateLimiter によるレート制御（120 req/min）
  - リトライ（指数バックオフ、最大 3 回）と 401 の自動トークンリフレッシュ
  - DuckDB への冪等な保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義
  - インデックス定義、外部キー依存を考慮した初期化関数（init_schema）
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と専用初期化関数（init_audit_schema / init_audit_db）

- 環境設定（.env 読み込み）
  - パッケージ起点でプロジェクトルートを検索し `.env` / `.env.local` を自動で読み込む（環境変数優先）
  - 必須設定はプロパティ経由で取得（未設定時はエラー）
  - テスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能

- 監査・トレーサビリティ
  - シグナルから発注・約定にいたる UUID ベースのトレーサビリティ設計
  - 発注要求は冪等キー（order_request_id）を保持し、二重発注防止を想定

## 必要条件

- Python 3.10 以上（PEP 604 の型ヒント（A | B）等を使用）
- duckdb（Python パッケージ）
- ネットワークアクセス（J-Quants など外部 API）

（実運用では kabuステーション API 用クライアントや Slack 通知等の追加依存が想定されます）

## セットアップ手順（開発環境）

1. リポジトリをクローン

   git clone <このリポジトリの URL>
   cd <repo>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell / cmd)

3. 必要パッケージをインストール

   pip install --upgrade pip
   pip install duckdb

   ※ パッケージを setuptools 等でローカルインストールする場合:
   pip install -e .

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を作成します。自動的に読み込まれます（ただし既存の OS 環境変数が優先）。

   必須の環境変数（このコードベースで参照されるもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN : Slack ボットトークン
   - SLACK_CHANNEL_ID : Slack 送信先チャンネル ID

   任意/デフォルトあり:
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : 開発環境。development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化（任意）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

## 使い方（概要とサンプルコード）

以下は主要 API の使い方サンプルです。対話環境やスクリプトから呼び出してデータ収集/保存やスキーマ初期化が行えます。

- 設定取得

  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)  # Path オブジェクト

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)
  # conn は duckdb.DuckDBPyConnection。以降の保存関数に渡す。

- J-Quants から日足取得→保存

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # 必要に応じて明示的にトークンを取得して渡すことも可能
  # from kabusys.data.jquants_client import get_id_token
  # token = get_id_token()

  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  inserted = save_daily_quotes(conn, records)
  print(f"保存件数: {inserted}")

- 財務データ・カレンダーの取得と保存

  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

  fin = fetch_financial_statements(code="7203")
  save_financial_statements(conn, fin)

  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)

- 監査ログスキーマ初期化

  from kabusys.data.audit import init_audit_schema, init_audit_db
  # 既存の conn に監査テーブルを追加する
  init_audit_schema(conn)
  # 監査専用 DB を作る場合
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- その他
  - jquants_client は内部でレート制御・リトライ・トークンキャッシュを行います。fetch_* 系はページネーションに対応しています。
  - save_* 系は DB 側で ON CONFLICT DO UPDATE を用いることで冪等にデータを格納します。
  - 型変換ユーティリティ（_to_float/_to_int）により不正な文字列は安全に None に変換します。

## 環境変数の自動読み込み挙動

- パッケージ初期化時（kabusys.config をインポートする際）に、パッケージファイルの位置を起点として親ディレクトリからプロジェクトルートを探索し、`.git` または `pyproject.toml` を見つけたらそのディレクトリをプロジェクトルートとみなして `.env` を読み込みます。
- 読み込み順は OS 環境変数（既存） > .env.local（上書き） > .env（未設定キーを設定）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

## 実装上の注目点（設計メモ）

- J-Quants クライアントは 120 req/min の厳格な制御を想定（固定間隔スロットリング）。429 や 5xx に対して指数バックオフでリトライします。401 は自動リフレッシュを試み 1 回だけ再送します。
- データ保存時は取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を評価できるようにしています。
- スキーマは Raw → Processed → Feature → Execution の層を分離し、インデックスで典型的なクエリパターンを高速化します。
- 監査テーブル群は削除せず永続化する前提（ON DELETE RESTRICT）で、発注要求には冪等キー（order_request_id）を持たせて二重発注を防ぐ設計です。

## ディレクトリ構成

以下は主要ファイル/ディレクトリの構成です（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（fetch/save, get_id_token）
      - schema.py              # DuckDB スキーマ定義と init_schema/get_connection
      - audit.py               # 監査ログ（signal_events / order_requests / executions）
      - audit.py               # 監査用スキーマ初期化ユーティリティ
    - strategy/
      - __init__.py            # 戦略層のエントリ（実装はここに追加）
    - execution/
      - __init__.py            # 発注実行層のエントリ（実装はここに追加）
    - monitoring/
      - __init__.py            # 監視・メトリクス（実装はここに追加）

（実際のリポジトリでは他にテストやドキュメント、CI 設定等が存在するかもしれません）

## 今後の拡張案（参考）

- kabuステーション／証券会社向けブローカーアダプタの実装（注文送信・取消・約定コールバック）
- Slack／Prometheus などの監視・通知連携の追加
- 戦略・ポートフォリオ管理ロジック、バックテスト用モジュール
- セキュリティ: 認証トークンのシークレット管理（Vault 等）との統合

---

何か README に追加したい情報（例: 実行スクリプト、CI の流れ、環境のより詳細な例）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。