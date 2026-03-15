# KabuSys

日本株向け自動売買システムのライブラリ基盤。  
データ収集・整形（DuckDBスキーマ）、環境設定読み込み、取引実行・戦略・監視のためのモジュール群の骨組みを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システム向けの共通基盤ライブラリです。主な役割は次のとおりです。

- 環境変数／.env の安全な読み込みとアプリ設定（settings）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義・初期化
- 発注／戦略／監視のためのサブパッケージ（実装は各モジュールで行う想定）

このリポジトリはフレームワーク部分（スキーマ、設定ロード、名前空間）を提供します。

---

## 主な機能

- 環境変数・.env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env`、`.env.local` を読み込む
  - OS 環境変数を保護しつつ `.env.local` で上書き可能
  - 特殊ケースで自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env のパースはシェル風（export、クォート、行内コメント）に対応
- Settings オブジェクト（環境変数からプロパティ取得）
  - J-Quants、kabuステーション、Slack、DBパス、環境（development/paper_trading/live）などを参照
  - 必須変数が未設定の場合は ValueError を発生
- DuckDB スキーマ管理
  - raw / processed / feature / execution 層のテーブル DDL を定義
  - init_schema(db_path) でテーブルとインデックスを作成（冪等）
  - get_connection(db_path) で既存 DB に接続
- パッケージ構成（拡張用のサブパッケージ）
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

---

## セットアップ

必要条件
- Python 3.10 以上（型ヒントの union 演算子 `|` を使用）
- duckdb（DuckDB Python バインディング）

推奨手順（仮にリポジトリがローカルにある場合）:

1. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   - 最低限: duckdb
   ```
   pip install duckdb
   ```
   - パッケージを editable インストール（プロジェクトに setup/pyproject がある場合）
   ```
   pip install -e .
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（後述の例参照）。

注意:
- 自動 `.env` 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時など）。

---

## 環境変数（.env の例）

必須（アプリケーションで使用する場合）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （デフォルト: data/monitoring.db）
- KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
- LOG_LEVEL （DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

.example（.env.example として保存可能）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

1. settings を使って環境変数を取得する
```python
from kabusys.config import settings

# 必須値が未設定だと ValueError が発生する
jquants_token = settings.jquants_refresh_token
print("env:", settings.env)
print("is_live:", settings.is_live)
```

2. DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す
db_path = settings.duckdb_path  # 例: data/kabusys.duckdb
conn = init_schema(db_path)     # テーブルとインデックスを作成し、接続を返す

# 接続を使ってクエリを実行
with conn:
    df = conn.execute("SELECT name FROM sqlite_master").fetchdf()  # DuckDB の情報取得例
```

3. 既存 DB に接続する（初回は init_schema を推奨）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

注意点:
- init_schema はファイルパスの親ディレクトリが存在しない場合、自動で作成します。
- ":memory:" を渡すとインメモリ DB が使用できます（テストなどに便利）。

---

## ディレクトリ構成

リポジトリ内の主なファイル・フォルダ構成（抜粋）

- src/
  - kabusys/
    - __init__.py              - パッケージ初期化（__all__ 指定）
    - config.py                - 環境変数/.env の読み込みと Settings クラス
    - data/
      - __init__.py
      - schema.py              - DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py            - 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py            - 発注・実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py            - 監視/ログ保存モジュール（拡張ポイント）

README に含まれないが重要な点:
- config._find_project_root() により `.env` 自動読み込みはファイルパスを基準に行われ、CWD に依存しません。
- .env のパースはシェル風に柔軟に対応（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント等）。

---

## 追加メモ

- settings は環境変数の妥当性検証（KABUSYS_ENV の制約、LOG_LEVEL の制約）を行います。不正な値を設定すると ValueError が発生します。
- 認証トークン等の機密情報は `.env.local` に置いて、リポジトリに含めないようにしてください。
- このリポジトリは基盤部分を提供するため、実際の取引ロジックや外部 API 呼び出し（kabu API、J-Quants、Slack 通知等）は各サブモジュールで実装してください。

---

必要であれば、README にインストール方法（pyproject/requirements.txt 想定）、CI・テスト手順、.env のより詳しいパース仕様の説明などを追加できます。どの情報を優先して追加しますか？