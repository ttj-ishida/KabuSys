# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ集です。  
データ収集（J-Quants）、DuckDB スキーマ定義、監査ログ用テーブル等を提供し、戦略・発注・監視部分の基盤を支援します。

バージョン: 0.1.0

## プロジェクト概要
KabuSys は日本株自動売買システムの基盤モジュール群です。本リポジトリでは主に以下を提供します。

- J-Quants API クライアント（株価・財務・マーケットカレンダーの取得）
- DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数/設定管理（.env 自動ロードを含む）
- （将来的に）strategy / execution / monitoring 用のパッケージ骨格

設計上のポイント:
- API レート制限（120 req/min）を自動で守る RateLimiter を実装
- 失敗時は指数バックオフ付きリトライ（401 は自動トークンリフレッシュを試行）
- データ取得時の fetched_at を UTC で記録し、Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を基本とする

## 機能一覧
- 環境変数/設定取得（kabusys.config.settings）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（優先度: OS 環境 > .env.local > .env）
  - 必須変数の未設定時は例外を投げるヘルパー
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（refresh token から id token を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - API 呼び出しの共通処理（レートリミット・リトライ・401 リフレッシュ等）
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で全テーブルとインデックスを作成（冪等）
  - get_connection(db_path) で既存 DB に接続
- 監査ログスキーマ（kabusys.data.audit）
  - init_audit_schema(conn) / init_audit_db(db_path) による監査用テーブル作成
  - signal_events / order_requests / executions を定義、監査向けインデックスを作成

（strategy / execution / monitoring の各パッケージは骨格用の __init__.py を含みます）

## 必要条件（推奨）
- Python 3.10+
- duckdb
- （標準ライブラリのみで HTTP は urllib を使用、追加依存は最小限）

インストール例（仮にローカルで開発する場合）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージインストール:
  - pip install duckdb

（将来的に requirements.txt / pyproject.toml があればそちらを使用してください）

## セットアップ手順

1. レポジトリをクローンし、仮想環境を用意する
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（デフォルトで自動ロード有効）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用等）。

必須の環境変数（少なくとも動かす用途に応じて設定してください）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN        : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       : 通知先 Slack チャンネル ID（必須）

任意（デフォルト値あり）:
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env の例:
（.env.example があればそれを参照してください）
例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

環境変数の自動読み込みルール:
- 自動ロードされるファイル: プロジェクトのルート（.git または pyproject.toml を起点）にある `.env` と `.env.local`
- 読み込み優先度: OS 環境変数 > .env.local > .env
- .env のパースは一般的な shell 形式に対応（`export KEY=val`、クォート、コメントなど）

## 使い方（簡単な例）

1) DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

2) J-Quants から株価日足を取得して保存
```python
from kabusys.data import jquants_client
from kabusys.config import settings
from kabusys.data import schema

# DB 初期化済みの接続を取得
conn = schema.get_connection(settings.duckdb_path)

# データ取得（必要なら date_from/date_to を指定）
records = jquants_client.fetch_daily_quotes(code="7203")  # 銘柄コード例

# DuckDB の raw_prices テーブルへ保存（冪等）
n = jquants_client.save_daily_quotes(conn, records)
print(f"{n} 件保存しました")
```

3) 財務データやマーケットカレンダーも同様に fetch_* → save_* を利用できます:
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

4) id_token の手動取得（低レベル使用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

5) 監査ログテーブルの初期化（別 DB に分けることも可能）
```python
from kabusys.data import audit
from kabusys.config import settings

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
# あるいは既存 conn に対して:
# audit.init_audit_schema(conn)
```

注意:
- fetch_* 系関数は内部でレート制限とリトライを行います。大量取得を行う場合は 120 req/min の制約を守る設計です。
- save_* 関数は PK の重複時に更新する（冪等）ため、繰り返し実行可能です。

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント、保存ロジック
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログスキーマ定義・初期化
      - audit.py
      - (その他ユーティリティ)
    - strategy/
      - __init__.py            # 戦略関連（骨格）
    - execution/
      - __init__.py            # 発注/ブローカー連携（骨格）
    - monitoring/
      - __init__.py            # 監視/メトリクス（骨格）

主要なモジュール説明:
- kabusys.config: .env 自動読み込み、Settings クラスを提供（settings オブジェクトから各種設定を取得）
- kabusys.data.jquants_client: J-Quants API の取り扱い（取得・保存・認証・レート制御）
- kabusys.data.schema: DuckDB テーブル群の DDL（Raw / Processed / Feature / Execution）
- kabusys.data.audit: 監査ログ用テーブル（signal_events / order_requests / executions）

## 運用上の注意
- Live 環境で実行する場合は、KABUSYS_ENV を `live` に設定しているかを確認してください。is_live フラグ等が設定により切り替わります。
- 機密情報（トークン・パスワード）は `.env.local` などローカルで管理し、リポジトリにコミットしないでください。
- DuckDB ファイルはバックアップ・スナップショット運用を検討してください（監査ログは削除しない前提です）。

---

必要であれば、README にサンプル .env.example、さらに詳細な API 使用例・スキーマ設計ドキュメント（DataSchema.md / DataPlatform.md に基づく設計書）を追加できます。どの部分を詳しく書き足すか指定してください。