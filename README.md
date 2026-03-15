# KabuSys

日本株向け自動売買システムのコアライブラリ（初期バージョン: 0.1.0）

KabuSys は市場データの収集/保存、特徴量生成、シグナル管理、発注・約定記録、モニタリングを目的とした内部ライブラリ群を提供します。DuckDB を用いたオンディスク（またはインメモリ）データベーススキーマと、環境変数による設定管理を備えています。

---

## 主な機能

- 環境変数ベースの設定管理（.env 自動読み込み対応）
  - J-Quants / kabuステーション / Slack / DB パス等の設定を提供
- DuckDB ベースのスキーマ定義と初期化
  - Raw / Processed / Feature / Execution の多層スキーマ
  - インデックス定義、外部キー考慮の作成順序
- モジュール分割（拡張しやすい構造）
  - data, strategy, execution, monitoring（骨組み）
- .env ファイルの柔軟なパース
  - export プレフィックス、クォート/エスケープ、コメント取り扱い等に対応

---

## 要件

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
- （任意）kabu API や J-Quants、Slack 用クライアントライブラリ（本レポジトリはそれらのクライアントは含みません）

インストール例:
```
pip install duckdb
```

プロジェクト全体の依存は別途 requirements.txt や pyproject.toml で管理してください。

---

## セットアップ手順

1. このリポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb
   ```
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（後述）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意の環境変数:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

5. 自動 .env 読み込みを無効化したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```
   テストなどで CWD に依存しない挙動を求める場合に有効です。

---

## .env 自動読み込みの挙動

- 自動読み込みはパッケージがインポートされた際に行われます（config モジュール内）。
- 読み込みの基準はパッケージファイル位置から親ディレクトリを辿り、`.git` または `pyproject.toml` を見つけたディレクトリをプロジェクトルートとみなします。見つからない場合は自動読み込みをスキップします。
- 読み込み順序と優先度:
  1. OS 環境変数（既存の環境変数）
  2. .env（override=False — 未設定のみ設定）
  3. .env.local（override=True — ただし OS の既存環境変数は保護）
- .env のパースは:
  - `export KEY=val` 形式に対応
  - シングル/ダブルクォート、バックスラッシュエスケープ対応
  - クォートなしの行では `#` の前がスペース/タブであればコメント扱い

---

## 使い方（クイックスタート）

1. 設定値を取得する（settings）
```python
from kabusys.config import settings

# 必須値が未設定の場合は ValueError が発生します
token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url  # デフォルト: http://localhost:18080/kabusapi
```

2. DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema, get_connection
from pathlib import Path

db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # テーブルとインデックスを作成して接続を返す

# インメモリ DB を使う場合
mem_conn = init_schema(":memory:")
```

3. 既存 DB に接続する（スキーマ初期化しない）
```python
conn = get_connection("data/kabusys.duckdb")
```

4. 自動 .env 読み込みを無効にしてから settings を使う（テスト等）
```python
import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"

from kabusys.config import settings
# 以降、手動で環境変数を設定してから settings を参照する
```

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要ファイル・モジュール構成（このリポジトリ内のサンプル）:

- src/
  - kabusys/
    - __init__.py            — パッケージメタ情報（__version__, __all__）
    - config.py              — 環境変数・設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - schema.py           — DuckDB スキーマ定義と初期化関数 (init_schema, get_connection)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（将来的に strategy、execution、monitoring 以下に実装を追加していく想定です。）

---

## DuckDB スキーマ概要

init_schema() により以下のような層でテーブルが作成されます（主なもの）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

各テーブルは基本的な型制約や主キー、外部キーを備え、クエリ性能向上のためインデックスも作成されます。

---

## 設定オプション（まとめ）

- 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 環境変数（任意）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（monitoring 用）（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化

---

## 注意点 / 補足

- settings プロパティは必須項目が未設定だと ValueError を投げます。まず環境変数（または .env）を整備してください。
- init_schema() は冪等です（既存テーブルがあればスキップ）。初回に一度実行してください。
- strategy / execution / monitoring モジュールは拡張点です。実際の売買ロジックや API ラッパーはこれらの下に実装して統合してください。

---

必要であれば README に環境変数の .env.example テンプレートや、DuckDB スキーマの詳細ドキュメント（テーブル一覧とフィールド説明）を追記します。どの情報をさらに詳しく書くか指示してください。