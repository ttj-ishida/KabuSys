# KabuSys — 日本株自動売買システム (README)

このドキュメントは、KabuSys コードベースの簡易 README です。プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの一部実装です。データ取得、スキーマ定義、監査ログといった基盤機能を提供し、戦略層・発注層・モニタリング層と連携して自動売買ワークフローを構築するための土台になります。

主要設計方針：
- Look-ahead bias を防ぐために取得時刻（UTC）を記録
- API レート制限・リトライ・トークン自動リフレッシュなど堅牢な API クライアント設計
- DuckDB を用いた冪等なデータ永続化（ON CONFLICT を使用）
- 監査ログによるトレーサビリティ（戦略 → シグナル → 発注 → 約定 の連鎖を UUID で追跡）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 必須環境変数のチェック（Settings オブジェクト）
  - 自動ロード無効化フラグ：KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）/ 財務（四半期） / JPX カレンダーの取得
  - レート制限（120 req/min）を守る内部 RateLimiter
  - 再試行（指数バックオフ、最大 3 回）、401 の場合はトークン自動リフレッシュ
  - ページネーション対応
  - DuckDB へ冪等に保存するユーティリティ（save_* 関数）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層にまたがるテーブル群と索引の作成定義
  - init_schema(db_path) で初期化（":memory:" 対応）
  - get_connection(db_path) で既存 DB に接続

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions のテーブルを定義
  - init_audit_schema(conn) で既存の DuckDB 接続に監査テーブルを追加
  - init_audit_db(db_path) で監査専用 DB を作成して接続を返す
  - すべての TIMESTAMP を UTC に固定

- パッケージ基盤
  - src レイアウトの Python パッケージ（kabusys）
  - strategy, execution, monitoring 用のパッケージプレースホルダ

---

## セットアップ手順

前提
- Python >= 3.10（PEP 604 の union 型表記（|）を使用）
- pip が利用可能

1. レポジトリをクローン
   - （例）git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
   - 例：
     - pip install duckdb
   - （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）
   - 開発時にパッケージとして使うには（プロジェクトルートに pyproject.toml 等がある前提で）:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env（および必要なら .env.local）を配置することで自動読み込みされます。
   - 自動ロードを無効にする場合は環境変数を設定：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

---

## 環境変数（.env の例）

以下は本プロジェクトで参照される主要な環境変数例です（.env.example 相当）。

例 (.env)
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL は省略時 http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベース
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム設定
KABUSYS_ENV=development      # development | paper_trading | live
LOG_LEVEL=INFO
```

必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings クラスが _require() を用いているため未設定だと ValueError が出ます）。

---

## 使い方（簡単なコード例）

以下は主要ユースケースの最小例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2) J-Quants から日足を取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)

records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print(f"{n} 件を保存しました")
```

3) トークン取得（明示的に利用したい場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
```

4) 監査ログの初期化（監査専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点：
- jquants_client は内部でレート制御とリトライを行います。大量リクエスト時でも 120 req/min を超えないように設計されています。
- get_id_token は refresh token を用いて id_token を取得し、jquants_client 内でキャッシュされてページネーション等で再利用されます。401 発生時は自動で 1 回だけリフレッシュして再試行します。

---

## ディレクトリ構成

プロジェクトは src レイアウトで構成されています。主要ファイルと簡単な説明は以下の通りです。

- src/
  - kabusys/
    - __init__.py
      - パッケージのメタ情報（__version__ 等）
    - config.py
      - 環境変数の読み込み・Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境設定等）
    - data/
      - __init__.py
      - jquants_client.py
        - J-Quants API クライアント（fetch/save の実装、レートリミット、リトライ、トークン管理）
      - schema.py
        - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）と初期化関数
      - audit.py
        - 監査ログテーブルの定義と初期化（signal_events, order_requests, executions）
    - strategy/
      - __init__.py
      - （戦略関連モジュールを配置する想定）
    - execution/
      - __init__.py
      - （発注 / ブローカーインタフェース等を配置する想定）
    - monitoring/
      - __init__.py
      - （モニタリング / アラート / Slack 通知等を配置する想定）

---

## 実装上の注意点 / 補足

- Python バージョン: 3.10 以上を推奨（`X | Y` 型表記を使用しているため）
- DuckDB を用いたファイルはデフォルトで data/kabusys.duckdb に保存されます（Settings.duckdb_path で変更可能）
- .env のパースは Bash 風のシンタックス（export 付き、シングル/ダブルクォート、インラインコメント等）に対応していますが、完全なシェル解釈ではありません
- 監査ログの TIMESTAMP は UTC 固定で保存されます（init_audit_schema は SET TimeZone='UTC' を実行）
- 発注 / 約定の監査トレーサビリティは UUID 連鎖（signal_id → order_request_id → broker_order_id）で設計されています
- 本リポジトリは基盤（データ収集・格納・監査）に重点を置いており、実際の売買ロジック（strategy）やブローカー接続（execution）の具体実装は今後追加されることを想定しています

---

## サポート / 貢献

- Issue や Pull Request を通してバグ報告や機能提案を受け付けてください。
- 実運用する場合は、ログ・例外処理・リトライポリシー、そして本番環境向けの安全ガード（ドローダウン制限・レート制限のモニタリング等）を十分に検討してください。

---

以上。README の追加修正や、具体的な使用例（戦略のテンプレート、kabu API 連携例、CI 設定など）を希望される場合は教えてください。