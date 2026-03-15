# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群（ライブラリ）。  
データ取得・スキーマ管理・監査ログ・環境設定など、バックエンドの共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダーなど）取得
- 取得データの DuckDB への永続化（冪等性を考慮）
- データベース（DuckDB）のスキーマ定義と初期化
- 監査ログ（シグナル → 発注 → 約定のトレース）の定義・初期化
- 環境変数の読み込み・管理（.env / .env.local、自動ロード）
- 発注/戦略/モニタリング等のサブパッケージ（拡張用の土台）

設計上の特徴：
- API レート制御（120 req/min）とリトライ（指数バックオフ・トークン自動リフレッシュ）を備えた J-Quants クライアント
- DuckDB のテーブルは ON CONFLICT DO UPDATE を使って冪等に保存
- 監査ログは削除しない方針、すべて UTC タイムスタンプで保存

---

## 機能一覧

- 環境設定読み込み
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）
  - 必須環境変数チェックとラッパー（`kabusys.config.settings`）
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レートリミット、リトライ、401 でのトークン自動リフレッシュを実装
  - DuckDB への保存ユーティリティ（冪等）
- DuckDB スキーマ管理（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化関数 `init_schema()` と接続取得 `get_connection()`
- 監査ログ（`kabusys.data.audit`）
  - signal_events, order_requests, executions テーブルを初期化する関数
  - 監査用インデックスを作成
- パッケージ構成は戦略、実行、モニタリング等を拡張するためのモジュールを用意

---

## 前提 / 要件

- Python 3.10 以上（型ヒントに `X | None` を使用しているため）
- 必要な外部パッケージ（最低限）:
  - duckdb
- 標準ライブラリ: urllib 等

インストール例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発用途: パッケージとしてインストール
pip install -e .
```

---

## 環境変数（主なもの）

以下は本ライブラリ内で参照される主な環境変数です。`.env` または `.env.local` に設定してください。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。`kabusys.data.jquants_client.get_id_token()` で使用します。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注系を実装する際に使用）
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットするとプロジェクトルートの `.env` 自動読み込みを無効化できます（テスト時等に便利）。

簡単な .env.example:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabu-station
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# Environment
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: パッケージはプロジェクトルート（`.git` or `pyproject.toml` のあるディレクトリ）から `.env` を自動検出します。

---

## セットアップ手順

1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール:
   ```bash
   pip install duckdb
   # 開発時は editable install
   pip install -e .
   ```

4. `.env` を作成:
   - `.env.example` を参考に必須環境変数を設定してください。
   - `.env.local` を作れば `.env` の上書き（優先）として読み込まれます。

5. DuckDB スキーマ初期化（例: スクリプトで一度実行）:
   - 下記「使い方」を参照して、`init_schema()` を呼ぶとデータベースとテーブルが作成されます。

---

## 使い方（簡単なコード例）

- 環境設定の参照:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 存在しなければ ValueError
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env)                    # development | paper_trading | live
```

- DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければディレクトリも作成される
# in-memory の場合
# conn = init_schema(":memory:")
```

- J-Quants から株価日足を取得して保存する例:
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

records = fetch_daily_quotes(
    code="7203",  # トヨタ等の銘柄コード。省略で全銘柄取得（注意: データ量）
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)
saved = save_daily_quotes(conn, records)
print(f"saved {saved} records")
```

- 財務データやカレンダーも同様に取得・保存可能:
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fins = fetch_financial_statements(code="7203")
save_financial_statements(conn, fins)

calendar = fetch_market_calendar()
save_market_calendar(conn, calendar)
```

- get_id_token を直接呼ぶ（必要な場合）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
```

- 監査ログの初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # signal_events, order_requests, executions を追加で作成
```

注意点:
- J-Quants API へのリクエストはレート制限（120 req/min）を守るため遅延が入ります。
- fetch_* 関数はページネーションに対応しており、内部で ID トークンのキャッシュと自動リフレッシュを行います。
- save_* 関数は重複挿入に対して ON CONFLICT DO UPDATE を行うため冪等です。

---

## ディレクトリ構成

主要ファイル・モジュールの構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数/設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存ロジック）
    - schema.py                    -- DuckDB のスキーマ定義・初期化
    - audit.py                     -- 監査ログ（signal_events, order_requests, executions）
    - (その他: audit 初期化ユーティリティ等)
  - strategy/
    - __init__.py                  -- 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                  -- 発注/ブローカー連携の拡張ポイント
  - monitoring/
    - __init__.py                  -- モニタリング関連（拡張ポイント）

その他:
- .env / .env.local                -- 環境変数（プロジェクトルートに配置）
- データベースファイル等は `DUCKDB_PATH` の設定に従って保存されます（デフォルト: data/kabusys.duckdb）。

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリはデータ取得や監査テーブルの初期化を行いますが、実際の発注やブローカー連携は別途実装が必要です（execution モジュールを拡張して利用）。
- 本番（live）モードでは特に環境変数・ログレベル・監査の運用を厳格にしてください（settings.is_live で分岐可）。
- `.env.local` はローカル用の秘匿設定置き場として使い、`.env` を通常設定のテンプレートとして管理するとよいです。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- DuckDB はローカルファイルを使用します。運用では定期バックアップやファイルアクセス制御を検討してください。

---

必要であれば、README に含めるセットアップのさらに詳しい手順（CI/CD、テスト、logging 設定例、.env のより詳しい説明、発注ワークフロー例など）を追加できます。どの情報を補足しましょうか？