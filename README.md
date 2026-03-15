# KabuSys

バージョン: 0.1.0

日本株向け自動売買システムの基盤ライブラリ。データ管理（Raw/Processed/Feature/Execution レイヤー）、環境設定、スキーマ初期化などの共通機能を提供します。戦略（strategy）、注文実行（execution）、モニタリング（monitoring）用のモジュール群を内包する設計です。

---

## 主な特徴

- 環境変数／.env ファイルからの設定読み込み（自動読み込み機能付き）
- DuckDB を使った多層データスキーマ（Raw / Processed / Feature / Execution）
- スキーマ初期化用 API（冪等）
- J-Quants / kabu ステーション / Slack などの外部サービス向け設定を想定した設定項目
- strategy / execution / monitoring のためのパッケージ構成（骨組み）

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈で `A | B` を使用しているため）
- duckdb Python パッケージ
  - インストール例: pip install duckdb

その他、実運用では kabu API クライアントや Slack クライアント等が必要になります（本リポジトリには含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo-url>

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 最低限: duckdb
     - pip install duckdb
   - 実運用で必要な外部クライアントは各自導入してください（例: Slack クライアント）

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を作成するか、OS 環境変数で設定します。
   - 自動ロードの順序:
     - OS 環境変数 > .env.local (上書き) > .env (未設定のみ)
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データベーススキーマ初期化（下記「使い方」を参照）

---

## 環境変数（主なもの）

以下は本コードベースで参照される主な環境変数です。必須項目はコード内で参照時に未設定だと例外が発生します。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- KABUSYS_ENV (省略時: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (省略時: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

.env のパース仕様（簡単な補足）
- 空行や `#` で始まる行は無視
- `export KEY=val` 形式を許容
- 値はシングル／ダブルクォートで囲めます。エスケープ (バックスラッシュ) に対応
- クォートなしの値は `#` の直前が空白かタブの場合、その `#` 以降をコメントとして扱います

例（.env）:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単なコード例）

Python コードから設定やスキーマ初期化を呼び出す例を示します。

- 設定取得:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema

# ファイルベース DB を作成（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")

# またはインメモリ DB
conn = init_schema(":memory:")
```

- 既存 DB への接続（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

init_schema は全テーブル（raw/processed/feature/execution）とインデックスを冪等に作成します。

---

## API（概要）

- kabusys.config
  - settings: Settings インスタンス。プロパティ経由で各種設定を取得する（例: jquants_refresh_token, kabu_api_password, duckdb_path, env, log_level, is_live 等）
  - 自動でプロジェクトルートの .env / .env.local を読み込む（無効化可）

- kabusys.data.schema
  - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
    - DuckDB ファイルを初期化し、全テーブル／インデックスを作成する（冪等）
  - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
    - 既存 DB への接続を返す（初期化は行わない）

その他:
- パッケージとして strategy, execution, monitoring の各モジュールが用意されていますが、このリポジトリ上の該当 __init__ では具体実装は含まれていません（拡張ポイント）。

---

## ディレクトリ構成

プロジェクトの主要ファイル配置（抜粋）:

```
src/
  kabusys/
    __init__.py            # パッケージ定義（version 等）
    config.py              # 環境変数・設定管理（自動 .env ロード、Settings）
    data/
      __init__.py
      schema.py            # DuckDB スキーマ定義・初期化
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

生成されるデータベース/ログ等（デフォルト）
- data/kabusys.duckdb  (DUCKDB_PATH のデフォルト)
- data/monitoring.db    (SQLITE_PATH のデフォルト)

---

## 開発上の注意点 / ヒント

- init_schema() は親ディレクトリが存在しない場合、自動で作成します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト等で自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV により挙動分岐させたい場合は settings.is_live / is_paper / is_dev を利用してください。
- スキーマは外部キーやインデックスを含みます。既存のデータと整合しない変更を加える際は注意してください。

---

必要であれば、README に依存パッケージの一覧（requirements.txt）や実行例（Strategy のテンプレート、Slack 通知のサンプル）を追加できます。追加を希望する場合は利用したい外部サービスや詳細要件を教えてください。