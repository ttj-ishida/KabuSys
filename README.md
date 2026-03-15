# KabuSys

日本株自動売買システムのコアライブラリ（軽量ベース実装）

このリポジトリはデータ取得、DBスキーマ、監査ログの仕組みを中心にした日本株自動売買システムの基盤モジュール群を提供します。戦略（strategy）、発注（execution）、監視（monitoring）などの上位レイヤーは拡張して利用できます。

## 主な特長（機能一覧）

- 環境変数・設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 必須キーの取得とバリデーション
  - 実行環境（development / paper_trading / live）とログレベル管理

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務（BS/PL）、JPXマーケットカレンダーの取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - 再試行（指数バックオフ、最大3回）、401発生時のトークン自動リフレッシュ
  - Look-ahead bias 対策のため取得時刻（UTC）を記録

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution の4層スキーマを定義
  - 冪等なテーブル作成（CREATE IF NOT EXISTS）および主要インデックス設定
  - init_schema()/get_connection() による DB 初期化・接続

- 監査（Audit）テーブル
  - シグナル → 発注要求 → 約定のトレーサビリティを UUID 連鎖で保持
  - 冪等キー（order_request_id）やステータス遷移をサポート
  - init_audit_schema()/init_audit_db() による初期化

## 必要条件

- Python 3.10+
- 依存パッケージ（最低限）
  - duckdb

（ネットワークアクセスが必要：J-Quants API、kabuステーション、Slack 等）

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール

   git clone して開発環境に配置するか、パッケージとしてインストールしてください。

2. Python 仮想環境を作成し、依存パッケージをインストール

   pip 等で duckdb をインストールしてください。

   pip install duckdb

3. 環境変数を設定

   プロジェクトルートに `.env`（および開発専用に `.env.local`）を作成します。自動読み込みはデフォルトで有効です（プロジェクトルートは .git または pyproject.toml を基準に探索）。

   例（.env）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   注意:
   - 自動 env ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - .env のパースはシェルライクなクォートやコメントをサポートします（詳細は実装参照）。

4. DB スキーマ初期化

   Python から DuckDB を初期化します（以下の使い方参照）。

## 基本的な使い方

- 設定の参照

  from kabusys.config import settings

  settings.jquants_refresh_token
  settings.duckdb_path
  settings.is_live  # KABUSYS_ENV == "live" の判定

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # ":memory:" を渡せばインメモリ DB

- J-Quants からデータ取得 → DuckDB に保存（例: 日次株価）

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  records = fetch_daily_quotes(code="7203")  # 銘柄コード（例: トヨタ）
  count = save_daily_quotes(conn, records)
  print(f"{count} 件を保存しました")

- 財務データ / マーケットカレンダー取得例

  from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar

  fin = fetch_financial_statements(code="7203", date_from=date(2022,1,1), date_to=date(2023,12,31))
  save_financial_statements(conn, fin)

  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)

- ID トークン取得（手動）

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings に設定された refresh token を使って取得

- 監査ログ（Audit）スキーマ初期化

  from kabusys.data.audit import init_audit_db, init_audit_schema
  # 既存の conn に監査テーブルを追加する場合:
  init_audit_schema(conn)
  # 監査専用 DB を別途作る場合:
  audit_conn = init_audit_db("data/audit.duckdb")

## 設計上の注意点 / 挙動

- .env 自動読み込み
  - パッケージインポート時にプロジェクトルートから `.env` と `.env.local` を順に読み込みます。
  - OS 環境変数は優先され、`.env.local` は `.env` を上書きします（ただし OS 環境にあるキーは保護される）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読み込みは無効化できます（テスト用途など）。

- J-Quants クライアントの堅牢性
  - レート制限（120 req/min）を内蔵（固定間隔）。
  - 408/429/5xx は指数バックオフで再試行。最大3回。
  - 401 はリフレッシュして1回だけリトライ（無限ループ防止）。
  - ページネーション対応（pagination_key）。
  - 取得データの保存は冪等（ON CONFLICT DO UPDATE）を採用。

- 監査ログ
  - すべてのタイムスタンプは UTC で保存する設計（init_audit_schema は TimeZone を UTC に設定）。
  - order_request_id を冪等キーとして二重発注を防止する設計になっています。

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
  - SLACK_BOT_TOKEN — Slack Bot Token
  - SLACK_CHANNEL_ID — 通知先チャネル ID

- 任意 / デフォルトあり
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — execution 環境 (development|paper_trading|live)（デフォルト: development）
  - LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意。値は非空で無効化）

## ディレクトリ構成

src/
- kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - schema.py                — DuckDB スキーマ定義と初期化（init_schema 等）
    - audit.py                 — 監査ログスキーマ（signal / order_request / executions）
    - audit.py                 — 監査用 DB 初期化ユーティリティ
    - (その他: raw/processed/feature 関連のテーブル定義)
  - strategy/
    - __init__.py              — 戦略層のエントリポイント（拡張用）
  - execution/
    - __init__.py              — 発注・約定関連（拡張用）
  - monitoring/
    - __init__.py              — 監視 / モニタリング（拡張用）

その他:
- .env.example（存在する場合） — 設定サンプル（リポジトリにあれば参照）

## 開発・拡張のガイドライン（簡易）

- strategy や execution 層はこの基盤に対してプラグイン的に実装してください。
- DuckDB のスキーマは初期化後に互換性を壊さない形で変更すること。後方互換性のない変更はマイグレーション戦略を検討してください。
- 外部 API 呼び出しは jquants_client の再利用を推奨。リトライ・レート制限ロジックは共通化されています。

---

この README はソース内のドキュメント（config.py / jquants_client.py / schema.py / audit.py）を基に作成しています。さらに具体的な利用例や CI/CD、デプロイ手順が必要であれば、その用途（例：paper_trading の流れ、kabuステーション連携の設定、Slack 通知の実装）を教えてください。必要に応じて追記します。