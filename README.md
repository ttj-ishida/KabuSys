# KabuSys

日本株向けの自動売買システム用ライブラリ。データ取得〜前処理〜特徴量生成〜発注・約定管理までを想定した共通機能とデータスキーマを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買基盤構築を支援する Python パッケージのコア部分です。  
主に以下を提供します。

- 環境変数／設定管理（自動 .env ロード、必須チェック）
- DuckDB を使ったデータスキーマ（Raw / Processed / Feature / Execution 層）
- 戦略・発注・モニタリング用のパッケージ領域（骨格）

パッケージルート: `src/kabusys`

---

## 主な機能

- 環境設定管理（`kabusys.config.settings`）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込み
  - OS 環境変数を保護しつつ .env.local で上書き可能
  - 必須環境変数未設定時のエラー通知
  - 実行環境フラグ（development / paper_trading / live）やログレベル検証
- DuckDB スキーマ定義（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス定義、外部キーやチェック制約を含む DDL を実行する `init_schema()` を提供
  - 既存テーブルがあれば冪等的にスキーマ作成をスキップ
- パッケージ構成の骨格（`strategy`, `execution`, `monitoring`）を用意

---

## セットアップ手順

1. Python (推奨: 3.10+) を用意します。

2. リポジトリをクローンまたは展開し、開発環境へインストールします（例: editable インストール）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

   - 必要なパッケージ（最低限）:
     - duckdb

   必要に応じてプロジェクト固有の requirements.txt / pyproject の依存をインストールしてください。

3. 環境変数を設定します。開発ではプロジェクトルートに `.env`（およびローカル上書き用に `.env.local`）を用意することが推奨されます。自動ロードはデフォルトで有効です（詳細は「環境変数」参照）。

---

## 環境変数

KabuSys は .env ファイルまたは OS の環境変数から設定を読み込みます。自動ロード条件:

- プロジェクトルートは `src/kabusys/config._find_project_root()` により `.git` または `pyproject.toml` の存在で判定します。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: `http://localhost:18080/kabusapi`）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV — 実行環境: `development`, `paper_trading`, `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`（デフォルト: `INFO`）

.env のパース仕様（概要）:

- コメント行（先頭 `#`）は無視
- `export KEY=val` 形式に対応
- 値はシングル／ダブルクォートで囲え、エスケープをサポート
- `.env` は OS 環境変数で設定済のキーを上書きしない（`.env.local` は上書きするが OS 環境変数は常に保護される）

設定値は `from kabusys.config import settings` でアクセスできます。例:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path
if settings.is_live:
    # ライブ環境向け処理
```

必須環境変数が未設定の場合、`settings` の当該プロパティ呼び出しで `ValueError` が発生します。

---

## データベース（DuckDB）初期化

スキーマ初期化 API:

- init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - 指定したパスの DuckDB を作成（親ディレクトリ自動作成）
  - 全テーブル・インデックスを作成（存在する場合はスキップ）
  - ":memory:" を指定するとインメモリ DB を使用

- get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - 既存 DB への接続のみを行う（スキーマ作成は行わない）

使用例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# 初回: スキーマを作成
conn = init_schema(settings.duckdb_path)

# 再接続: スキーマ作成は行わない
conn2 = get_connection(settings.duckdb_path)
```

スキーマは以下のレイヤーで構成されています（主なテーブル）:

- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance

各テーブルには整合性チェック（CHECK 制約）、主キー、外部キー、頻出クエリ向けのインデックスを定義しています。

---

## 使い方（簡単な例）

1. .env を用意
   - 必須変数を設定（例: JQUANTS_REFRESH_TOKEN 等）

2. スキーマを初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path にはデフォルトで data/kabusys.duckdb が入ります
conn = init_schema(settings.duckdb_path)
```

3. データ挿入・クエリ（duckdb 接続を直接利用）

```python
# 例: prices_daily にデータ挿入
conn.execute(
    "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
    ['2024-01-04', '7203', 1000.0, 1050.0, 995.0, 1020.0, 123456]
)
rows = conn.execute("SELECT * FROM prices_daily WHERE code = '7203'").fetchall()
```

4. strategy / execution / monitoring 用のモジュールは骨格のみ（拡張して使用）

---

## ディレクトリ構成

リポジトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py              # パッケージ定義、__version__ = "0.1.0"
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化 API
    - strategy/
      - __init__.py            # 戦略関連のエントリポイント（拡張用）
    - execution/
      - __init__.py            # 発注・注文管理のエントリポイント（拡張用）
    - monitoring/
      - __init__.py            # モニタリング関連（拡張用）

その他:
- .env.example（リポジトリに用意することを推奨）
- pyproject.toml / setup.cfg 等（パッケージ管理）

---

## 開発メモ / 実装上の注意

- 環境の自動読み込みはプロジェクトルート判定に依存するため、実行場所（CWD）に依存しません。ユニットテスト等で自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってください。
- .env と .env.local の読み込み順:
  - OS 環境変数 (highest, protected)
  - .env (未設定キーのみ設定)
  - .env.local (override=True で .env の値を上書き、ただし OS 環境変数は保護)
- DuckDB スキーマは冪等に作成されるため、何度でも init_schema() を呼べます。
- `settings` のプロパティは呼び出し時に検証（必須チェック、列挙値チェック）を行います。

---

必要に応じて、strategy / execution / monitoring の実装サンプルや CI / デプロイ手順を追加してください。