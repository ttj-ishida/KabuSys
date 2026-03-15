# KabuSys

日本株自動売買プラットフォーム向けのライブラリ群（プロトタイプ／ライブラリ層）。
データ取得・スキーマ管理・監査ログなど、アルゴリズムトレード基盤の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群を提供します。

- J-Quants API からの市場データ取得（株価日足、四半期財務、マーケットカレンダー）
- DuckDB によるスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル → 発注 → 約定フローのトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動読み込み、必須設定のチェック）

設計上のポイント：
- API レート制御（120 req/min）およびリトライ（指数バックオフ、401 時の自動トークンリフレッシュ）
- 取得時刻（fetched_at）や UTC タイムゾーンを使った時系列の正確なトレーサビリティ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を防止

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化可能

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes: 株価日足（ページネーション対応）
  - fetch_financial_statements: 四半期財務データ（ページネーション対応）
  - fetch_market_calendar: JPX マーケットカレンダー
  - get_id_token: リフレッシュトークンから id_token を取得（自動キャッシュ・自動リフレッシュ）

- データ永続化（kabusys.data.schema）
  - init_schema: DuckDB の全テーブル（Raw/Processed/Feature/Execution）を作成
  - get_connection: 既存 DB へ接続
  - テーブル定義は冪等でインデックスも作成

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化関数
  - 監査向けインデックスを作成、タイムゾーンは UTC に固定

- パッケージ構成の拡張ポイント
  - strategy, execution, monitoring 用のパッケージプレースホルダ

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | アノテーションを使用）
- duckdb パッケージ

例（仮の開発環境）:
1. リポジトリをクローン
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb

（プロジェクト化している場合は pip install -e . などで開発インストール）

環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意／デフォルト有り:
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
  - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 に設定すると .env の自動読み込みを無効化

簡易 .env.example:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

自動読み込みの挙動:
- パッケージのファイル位置から親ディレクトリを上へ辿り、.git または pyproject.toml が見つかった場所をプロジェクトルートと判断して .env / .env.local を読み込みます。
- 既存 OS 環境変数は上書きされません（ただし .env.local は override=True で上書き可）。
- テストなどで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

以下は DuckDB を初期化し、J-Quants からデータを取得して保存する最小例です。

1) スキーマの初期化と接続取得
Python:
from kabusys import data
from kabusys.config import settings

# デフォルトの DUCKDB パスを利用してスキーマ初期化
conn = data.schema.init_schema(settings.duckdb_path)

2) 株価日足の取得と保存
from kabusys.data import jquants_client as jq

records = jq.fetch_daily_quotes(code="7203")  # 銘柄コード（例: トヨタ）
n = jq.save_daily_quotes(conn, records)
print(f"saved {n} rows")

3) 財務データ / マーケットカレンダー
fins = jq.fetch_financial_statements(code="7203")
jq.save_financial_statements(conn, fins)

cal = jq.fetch_market_calendar()
jq.save_market_calendar(conn, cal)

4) 監査ログの初期化（監査テーブルを別 DB に用意する場合）
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/audit.duckdb")
# 既存 conn に追加するなら:
# audit.init_audit_schema(conn)

補足（注意点）
- fetch_* 系はページネーション対応、内部で id_token のキャッシュと自動リフレッシュを行います。
- API 呼び出しは内部でレート制御（120 req/min）とリトライ（408/429/5xx 等）を行います。
- DuckDB への保存関数は ON CONFLICT DO UPDATE を利用しており、冪等に動作します。
- 監査ログのタイムスタンプは UTC で保存されます（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

パッケージの主なファイル・構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント（取得 + 保存）
    - schema.py                   -- DuckDB スキーマ定義と init_schema / get_connection
    - audit.py                    -- 監査ログスキーマ（signal_events / order_requests / executions）
    - audit.py
    - その他（raw/processed/feature/execution テーブル DDL 定義含む）
  - strategy/
    - __init__.py                 -- 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py                 -- 発注・ブローカー統合（拡張ポイント）
  - monitoring/
    - __init__.py                 -- 監視・アラート（拡張ポイント）

README に載っている以上のモジュールは、戦略実装・取引実行・監視ロジックを組み込むための基盤（ライブラリ）です。

---

## 開発上の留意点

- Python バージョンは 3.10+ を想定しています（型注釈で | を使用）。
- ネットワーク／API 呼び出しには 30 秒のタイムアウトを設定していますが、実運用ではリトライ戦略や監視を強化してください。
- DuckDB を永続ストレージとして使用していますが、バックアップ・移行ポリシーの検討が必要です。
- 監査ログは削除しない設計を前提としているため、ディスク容量や保守ポリシーに注意してください。

---

問題や拡張のための提案が必要であれば、どの機能（例: 注文送信の冪等化、ブローカー連携、戦略インターフェイス）を優先したいか教えてください。README のサンプルコードや .env 例の補足も作成できます。