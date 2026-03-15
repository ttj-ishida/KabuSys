# KabuSys

日本株向けの自動売買システム用ライブラリ（パッケージ: kabusys、version 0.1.0）

このリポジトリは、データ取得・加工、特徴量生成、シグナル生成、発注・約定管理、モニタリングのための基盤を提供します。DuckDB を用いたローカルデータベーススキーマ定義や、環境変数管理（.env の自動読み込み）などのユーティリティを含みます。

---

## 主な機能

- 環境変数 / 設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（OS環境 > .env.local > .env の優先順位）
  - 必須変数チェック（未設定時は ValueError を送出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
- DuckDB ベースのスキーマ定義（冪等性あり）
  - Raw / Processed / Feature / Execution の各レイヤーを定義
  - 主要テーブル例: raw_prices, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance など
  - よく使うクエリに合わせたインデックスを作成
  - init_schema(db_path) で初期化・接続、get_connection() で既存 DB に接続
- パッケージ構造の基礎（data, strategy, execution, monitoring モジュールのための土台）

---

## セットアップ手順

1. Python バージョン
   - このコードは Python 3.10 以降（PEP 604 の型記法 `X | None` を使用しているため）を想定しています。

2. 依存パッケージのインストール（最低限）
   - duckdb が必須です。
     - pip install duckdb
   - 他に Slack 等の連携を使う場合は該当ライブラリを追加でインストールしてください（例: slack_sdk）。

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb
   ```

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置きます（.env.local は .env を上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

   必須とされる環境変数（Settings で参照されます）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   その他の設定（デフォルトあり）:
   - KABUS_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH （デフォルト: data/monitoring.db）
   - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

   注意:
   - export KEY=val 形式にも対応します。
   - シングル/ダブルクォートの中ではバックスラッシュによるエスケープが処理されます。
   - クォートなしの場合、行中の `#` は直前がスペースまたはタブならコメントとみなします。

---

## 使い方（基本例）

- 設定の参照

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

- DuckDB スキーマを初期化して接続を取得

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

init_schema は必要なディレクトリを自動作成し、全テーブルとインデックスを作成します（冪等）。既に初期化済みの DB に接続するだけなら get_connection を使います。

```python
conn = schema.get_connection("data/kabusys.duckdb")
```

- テーブルへクエリ実行（duckdb 接続をそのまま使用）

```python
# pandas や SQL を直接利用可能
res = conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- 自動 .env 読み込みの無効化（テストなどで）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('loaded')"
```

---

## ディレクトリ構成

（リポジトリの主要ファイル / モジュール）

- src/
  - kabusys/
    - __init__.py          # パッケージ初期化（__version__ 等）
    - config.py            # 環境変数・設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - schema.py         # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py        # 戦略モジュールのためのプレースホルダ
    - execution/
      - __init__.py        # 発注・約定関連モジュールのためのプレースホルダ
    - monitoring/
      - __init__.py        # モニタリング関連のプレースホルダ

- （プロジェクトルートに .env / .env.local を置く想定）
- data/（データベースファイル等を置くデフォルトディレクトリ）

---

## 補足（設計上のポイント）

- .env の自動読み込みは、.git または pyproject.toml を起点にプロジェクトルートを探索するため、CWD に依存せずパッケージ配布後も安定して動作します。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- .env 読み込みの優先順位は OS 環境変数 > .env.local > .env です。OS 環境変数は保護され、.env.local/.env により上書きされません（.env.local は override=True のため .env を上書き）。
- DuckDB のスキーマは Raw / Processed / Feature / Execution（およびインデックス）を定義しており、戦略開発・バックテスト・ライブ運用のデータ基盤として想定されています。

---

必要に応じて、実際の戦略実装や発注ロジック、モニタリングの実装ファイルをこの構成の下に追加していってください。README に加え、.env.example や CONTRIBUTING.md、pyproject.toml / requirements.txt を追加すると導入がより容易になります。