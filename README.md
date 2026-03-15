# KabuSys

日本株向けの自動売買システム用ライブラリ（骨組み）。  
本リポジトリでは、環境変数管理、DuckDB ベースのスキーマ定義、設定アクセスなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの内部ライブラリ群です。  
主に以下を提供します。

- 環境変数 / 設定の管理（.env 自動ロード、必須項目の検証）
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
- 将来的な戦略（strategy）、実行（execution）、監視（monitoring）モジュールのためのパッケージ構成

現状はコアの設定・スキーマ初期化周りが実装されています（バージョン: 0.1.0）。

---

## 主な機能一覧

- 環境変数読み込み
  - プロジェクトルート（.git または pyproject.toml）を自動検出して .env, .env.local を読み込む
  - OS 環境変数が優先され、.env.local は .env より優先して上書き（ただし OS 環境変数は保護）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - 値のパースはシェル風のクォート/コメントを考慮

- 設定アクセス API
  - settings オブジェクト経由で以下の設定にアクセス可能
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（省略時デフォルトあり）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH, SQLITE_PATH（データベースパス）
    - KABUSYS_ENV（development / paper_trading / live のいずれか）
    - LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL のいずれか）

- DuckDB スキーマ管理
  - init_schema(db_path) で DuckDB ファイルを作成し、全テーブル・インデックスを作成（冪等）
  - get_connection(db_path) で既存 DB へ接続
  - スキーマは Raw / Processed / Feature / Execution の四層に分かれる（prices, features, orders, trades, positions など多数のテーブル定義）

---

## 要件

- Python 3.10 以上（PEP 604 の union 型表記 `Path | None` を使用）
- 依存パッケージ（最低限）
  - duckdb

pip でのインストール例（仮にローカルで開発する場合）:
```
python -m pip install duckdb
# またはパッケージ化されている場合は:
# python -m pip install -e .
```

requirements.txt がある場合はそちらを使ってください（本リポジトリには含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン / 取得する
2. Python 3.10+ 環境を作成（venv 等）
3. 依存パッケージをインストール
   ```
   python -m pip install duckdb
   ```
4. 環境変数の準備
   - プロジェクトルートに `.env` を作成（必要なキーは後述）
   - 任意で `.env.local` を作成してローカル上書き可能
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマ初期化（次節の使い方参照）

---

## 使い方

以下は基本的な操作例です。

- settings の利用（環境変数から値を取得）
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path オブジェクト
```

- DuckDB スキーマの初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# ファイルパスは settings.duckdb_path を利用
conn = schema.init_schema(settings.duckdb_path)
# :memory: を使うとインメモリ DB を使用できます
# conn = schema.init_schema(":memory:")
```

- 既存 DB へ接続
```python
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みの振る舞い
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml を検索）を起点に `.env`→`.env.local` を読み込みます。
  - OS 環境変数は保護され、`.env` / `.env.local` の上書き対象になりません（ただし .env.local は .env を上書きします）。
  - テストや特殊用途で自動ロードを無効化したいときは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## スキーマ概要（簡易）

データは以下の 4 層で管理されます。

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

各テーブルは CREATE TABLE IF NOT EXISTS で作成され、インデックスも作成されます。init_schema は冪等です。

---

## ディレクトリ構成

下記は主要ファイルと想定ディレクトリ構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化
    - strategy/
      - __init__.py            # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py            # 発注実行関連（拡張ポイント）
    - monitoring/
      - __init__.py            # 監視・モニタリング（拡張ポイント）

README や pyproject.toml、.git はプロジェクトルートに置かれる想定です。config._find_project_root はこれらを探して .env 自動読み込みの基準とします。

---

## 環境変数一覧（参照用）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

---

## 開発メモ / 注意点

- Python のバージョンは 3.10 以上を推奨します（型表記に union 型 `|` を使用）。
- init_schema は DB の親ディレクトリが存在しない場合、自動でディレクトリを作成します。
- .env のパースは簡易シェル風（クォート、エスケープ、インラインコメントの一部を考慮）ですが、複雑なシェル構文まではサポートしません。
- まだ戦略実装（strategy）、実際の発注実装（execution）、監視（monitoring）は骨組みのみです。実際の取引を行う場合は各 API 実装、リスク管理、テストを十分に行ってください。

---

何か追加したい情報（API の例、.env.example のテンプレート、セットアップスクリプト等）があれば教えてください。README をそれに合わせて拡張します。