# KabuSys

日本株向けの自動売買システム（骨組み）。データ収集・スキーマ管理・戦略・発注・監視のための基盤モジュール群を提供します。

バージョン: 0.1.0

## 概要

KabuSys は日本株の自動売買システムの基盤ライブラリです。  
主な責務は次のとおりです。

- 環境変数／設定管理（.env の自動読み込み、必須変数チェック）
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution の多層スキーマ）
- 戦略（strategy）、発注（execution）、監視（monitoring）用のパッケージ構成（骨組みのみ）

このリポジトリはコアのインフラ（設定・データ層・スキーマ）を提供し、具体的な戦略や取引ロジックは各モジュール配下に実装して拡張していく設計です。

## 主な機能一覧

- 環境変数読み込みと管理
  - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込む
  - クォート／エスケープ対応、コメント処理を備えた .env パーサ
  - 必須環境変数の取得時に未設定なら ValueError を投げて早期エラー検出
  - 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- 設定（Settings）：J-Quants、kabu API、Slack、DB パス、環境種別（development / paper_trading / live）、ログレベルなど
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - よく使われるクエリに合わせたインデックス定義
  - init_schema(db_path) でディレクトリ作成→DDL実行の冪等初期化
  - get_connection(db_path) で既存 DB に接続

## セットアップ手順

1. Python 環境（推奨: Python 3.10 以上）を準備します。

2. リポジトリをクローンして開発用環境を作成します（例: virtualenv / venv）。

   ```
   git clone <this-repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存ライブラリをインストールします。最低限 DuckDB が必要です。

   ```
   pip install duckdb
   ```

   ※ 実際の運用では Slack SDK、kabu API クライアント、J-Quants クライアント等が必要になります。各機能を実装する際に追加してください。

4. 環境変数を用意します。プロジェクトルートに `.env`（および必要であれば `.env.local`）を置きます。自動的に読み込まれます（CWD ではなく、パッケージファイル位置から上位の .git / pyproject.toml を探索してルートを決定）。

   自動読み込みを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

## 必須・推奨環境変数（例）

以下はコード内で参照される主な環境変数の例です（.env に設定してください）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

例（.env の抜粋）:

```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=paper_trading
LOG_LEVEL=DEBUG
```

.env のパースはシングル/ダブルクォートやエスケープに対応し、行頭に `export ` があっても受け付けます。クォートなしの場合は `#` をコメント扱いにする際の細かいルールがあります（スペース直前の `#` をコメント開始と見なす等）。

## 使い方（簡単なコード例）

- 設定を取得する:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path
```

- DuckDB スキーマを初期化する:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = init_schema(settings.duckdb_path)

# :memory: も指定可能（インメモリ DB）
# conn = init_schema(":memory:")
```

- 既存 DB に接続する（初回のみ init_schema を呼ぶ想定）:

```python
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

- 自動 .env 読み込みを無効にして手動で環境をセットアップしたい場合:

```python
import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
# その後に必要な環境変数をセット
os.environ["JQUANTS_REFRESH_TOKEN"] = "..."
```

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリは次の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数・設定読み込みロジック
  - data/
    - __init__.py
    - schema.py            -- DuckDB スキーマ定義と init_schema / get_connection
  - strategy/
    - __init__.py          -- 戦略実装用パッケージ（拡張点）
  - execution/
    - __init__.py          -- 発注実装用パッケージ（拡張点）
  - monitoring/
    - __init__.py          -- 監視・モニタリング用パッケージ（拡張点）

README・ドキュメント等はこの他に配置する想定です（DataSchema.md 等の参照がコード内コメントにあります）。

## 開発メモ・注意点

- config の自動 .env 読み込みは、パッケージファイルの位置から上位へ .git または pyproject.toml を探してプロジェクトルートを決定します。CI やテストで挙動を切り替えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- Settings クラスは必須環境変数を要求します。未設定のまま使用すると ValueError が発生して早期に検出できます。
- init_schema は冪等です。既存テーブルがあればそのままスキップします。
- DuckDB のパス指定に ":memory:" を使うとインメモリ DB を利用できます（テスト時に便利）。

---

不明点や追加してほしい情報（例: 実際の戦略実装例、kabu API の接続サンプル、Slack 通知サンプルなど）があれば教えてください。README をそれに合わせて拡張します。