# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ） — データ取得、スキーマ管理、監査ログ基盤を備えた基盤モジュール群です。

バージョン: 0.1.0

概要:
- J-Quants API から株価・財務・マーケットカレンダー等を取得するクライアントを備えています。
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution 層）を定義・初期化できます。
- 発注〜約定の監査ログ用スキーマ（tracing / audit）を提供します。
- 環境変数による設定管理機能（.env 自動ロード含む）を持ちます。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- ディレクトリ構成
- 環境変数一覧と説明
- 補足（設計上の注意）

プロジェクト概要
- 目的: 日本株の自動売買システム実装のための基盤ライブラリ。データ取得・永続化・監査（トレーサビリティ）にフォーカスしています。
- 設計上の要点:
  - API 呼び出しのレート制限（J-Quants: 120 req/min）を守る RateLimiter 実装
  - リトライ（指数バックオフ、最大 3 回）と 401 受信時のトークン自動リフレッシュ対応
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を使用
  - 監査ログは UUID 連鎖でシグナル→発注→約定のトレーサビリティを保証

主な機能一覧
- 環境設定管理
  - .env / .env.local を自動ロード（プロジェクトルートを .git または pyproject.toml で探索）
  - settings オブジェクト経由で各種設定を取得
- データ取得（J-Quants クライアント）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - レート制御・再試行ロジックを内蔵
- DuckDB スキーマ管理
  - init_schema(db_path) で全テーブル／インデックスを作成
  - get_connection(db_path) で既存 DB に接続
  - テーブル群: raw_prices / raw_financials / market_calendar / features / signals / orders / trades / positions / ... 等
- 監査ログ（Audit）
  - init_audit_schema(conn) / init_audit_db(db_path) により監査用テーブルを追加
  - テーブル例: signal_events, order_requests, executions
- データ保存ユーティリティ
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB に対し冪等保存）

セットアップ手順
前提
- Python 3.10 以上（| 型等の構文を使用）
- pip が利用可能

1) リポジトリをチェックアウトする
   git clone <repo>

2) 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3) 必要パッケージをインストール
   pip install duckdb

   （本リポジトリに追加の依存があれば requirements.txt を用意して従ってください。上記コードは標準ライブラリ + duckdb を使用します。）

4) 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動的にロードされます（環境により OS 環境変数が優先されます）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（簡単な例）
- 設定取得
```py
from kabusys.config import settings

# 必須環境変数が未設定だと ValueError が発生します
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)  # デフォルト: http://localhost:18080/kabusapi
```

- DuckDB スキーマ初期化（永続 DB）
```py
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- J-Quants から日足を取得して保存する例
```py
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# トークンは settings 経由で内部取得されるので省略可
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 監査ログスキーマの初期化（既存接続に追加）
```py
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

- 監査用に独立した DB を作る場合
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

重要な実装挙動（運用時の注意）
- J-Quants API 呼び出しは内部で 120 req/min に相当する最小間隔を保証します（_RateLimiter）。
- リトライは最大 3 回（408/429/5xx 等）で、429 の場合は Retry-After を優先して待機します。
- 401 が返された場合、自動的に get_id_token() を呼んでトークンを1回だけ更新し再試行します。
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等になります。
- 監査ログは UTC タイムゾーンで TIMESTAMP を保存（init_audit_schema は SET TimeZone='UTC' を実行します）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                (パッケージ定義, __version__ 等)
  - config.py                  (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント + 保存ユーティリティ)
    - schema.py                (DuckDB スキーマ定義と init_schema/get_connection)
    - audit.py                 (監査ログスキーマ定義と初期化)
    - audit.py
  - strategy/
    - __init__.py              (戦略モジュール用プレースホルダ)
  - execution/
    - __init__.py              (発注・実行モジュール用プレースホルダ)
  - monitoring/
    - __init__.py              (監視・メトリクス用プレースホルダ)

環境変数（必須・任意）
- 必須（Settings から _require される項目）
  - JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン（get_id_token で使用）
  - KABU_API_PASSWORD      : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN        : Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID

- 任意 / デフォルト値あり
  - KABU_API_BASE_URL      : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            : 監視用 sqlite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV            : 動作モード（development, paper_trading, live）デフォルト: development
  - LOG_LEVEL              : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）デフォルト: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化

.env 自動ロードの挙動
- 自動ロードの優先順位: OS 環境変数 > .env.local > .env
- プロジェクトルートは __file__ 位置から親ディレクトリを上って .git または pyproject.toml を探して決定
- プロジェクトルートが特定できない場合、自動ロードはスキップされます
- .env ファイルの簡易パーサーは export 形式やクォート、行末コメントなどに対応

補足（設計上の注意）
- 本ライブラリは「データ取得・格納・監査」を担う基盤モジュールであり、実際の戦略ロジック・注文発行（ブローカー連携）や Slack 通知の実装は呼び出し側で実装する想定です（ただし環境変数等の準備はあります）。
- DuckDB の初期化は冪等なので運用ではデプロイ時・初回起動時に init_schema() を呼ぶだけで OK です。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されています。データ保全に注意してください。

ライセンス、貢献方法などはリポジトリのトップレベルに別途記載してください。

お問い合わせや改善提案は README の Issue / PR で行ってください。