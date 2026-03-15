# KabuSys

日本株向け自動売買システムの基盤ライブラリです。市場データの保存・スキーマ管理、環境設定の取り扱い、戦略・発注・監視のモジュール分割を想定したパッケージ構成を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- 日本株の市場データ・財務データ・ニュース等の取得・保管（DuckDB）
- 特徴量（feature）・AIスコア等の格納スキーマ
- 発注フロー（シグナル → 発注キュー → 注文 → 約定 → ポジション）を管理するテーブル群
- 環境変数による設定管理（.env 自動読み込み機能を含む）

パッケージはモジュール別に分離されており、戦略（strategy）、実行（execution）、データ（data）、監視（monitoring）などで拡張できます。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可）
  - 必須設定の検証（未設定時に例外）
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - テーブル作成（冪等）
  - インデックス作成
  - init_schema() / get_connection() API
- パッケージ化されたモジュール構成（strategy / execution / data / monitoring）の雛形

---

## 必要条件 / 依存

- Python 3.9+
- duckdb（データベースを使用する場合）
- （実行環境により）kabuステーション API クライアント、Slack SDK 等を別途導入

pip で最低限 duckdb を入れておく例:
```
pip install duckdb
```

※ このリポジトリ自体の他の外部依存はこのサンプルコードには明示されていません。実運用では J-Quants API クライアントや Slack 用ライブラリ等を別途追加してください。

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境の作成（推奨）
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. パッケージのインストール（編集可能インストール）
```
pip install -e .
pip install duckdb
```

4. 環境変数の準備
- プロジェクトルートに `.env` と（開発用に）`.env.local` を置くと、自動で読み込まれます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

例 `.env`（最低限必要なキー）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# システム設定（任意）
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DBパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

必須項目（未設定だと Settings プロパティ呼び出し時に ValueError を送出）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

---

## 使い方

以下は基本的な利用例です。

- 環境設定にアクセスする
```python
from kabusys.config import settings

print(settings.kabu_api_base_url)
print(settings.is_dev)  # KABUSYS_ENV による判定
```

- DuckDB スキーマを初期化する（ファイル DB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
# 以降 conn を使ってクエリ実行可
```

- メモリ上 DB を使う場合:
```python
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
```

- 既存 DB へ接続する（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- 自動 .env ロードを無効にしてテスト実行する（環境変数を直接制御する場合）:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -m pytest
```

---

## ディレクトリ構成

現在の主要ファイルと想定構成は以下のとおりです。

- src/
  - kabusys/
    - __init__.py                # パッケージエントリ（__version__ 等）
    - config.py                  # 環境変数・設定管理（.env 自動ロード、Settings クラス）
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化関数 (init_schema, get_connection)
    - strategy/
      - __init__.py              # 戦略関連モジュール（拡張用）
    - execution/
      - __init__.py              # 発注・実行関連モジュール（拡張用）
    - monitoring/
      - __init__.py              # 監視・アラート関連モジュール（拡張用）

主要なファイル説明:
- src/kabusys/config.py
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込み
  - Settings クラスが環境変数をラップして提供
- src/kabusys/data/schema.py
  - DuckDB の DDL（Raw / Processed / Feature / Execution の各テーブル）を定義
  - init_schema(db_path) でディレクトリ作成→DDL 実行→接続を返す
  - get_connection(db_path) は既存 DB へ接続する

---

## 注意事項 / 補足

- .env のパースは基本的な shell 形式（export プレフィックス、クォート、コメント）をサポートしていますが、複雑なケースは注意してください。
- KABUSYS_ENV は 'development', 'paper_trading', 'live' のいずれかである必要があります。
- LOG_LEVEL は 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' のいずれかを指定してください。
- 実際の発注機能を実装する場合は、kabuステーション API の接続・認証・送受信処理や、Slack 通知ロジック等を別途実装してください。

---

必要に応じて README を拡張して、使用例（戦略のテンプレート、監視ダッシュボードの作成手順、CI 設定など）を追加します。ご希望の内容があれば教えてください。