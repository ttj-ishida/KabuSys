# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システムのベースライブラリ。データ管理（DuckDB スキーマ）、環境設定の読み込み、戦略／発注／モニタリング用のパッケージを含む骨組みを提供します。

---

## 概要

KabuSys は、以下の目的を持つ内部ライブラリ／フレームワークです。

- 日本株のマーケットデータ・ファンダメンタル・ニュースなどを保存・管理するための DuckDB スキーマを提供
- 環境変数／.env ファイルからの設定読み込みを安全に行う設定モジュール
- 戦略、発注（execution）、モニタリングのためのパッケージ構成（骨組み）

このリポジトリはコアのスキーマ設計と設定読み込みロジックを実装しており、上に戦略や実行ロジックを組み合わせて自動売買アプリケーションを構築します。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（優先度: OS 環境 > .env.local > .env）
  - export KEY=val、クォート文字列、コメント行等に対応した堅牢なパーサ
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数取得時に未設定なら ValueError を送出する Settings クラス
  - 設定プロパティ例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等

- DuckDB スキーマ管理（kabusys.data.schema）
  - 3〜4 層のテーブル設計（Raw / Processed / Feature / Execution）
  - 価格、財務、ニュース、実行履歴、シグナル、オーダー、トレード、ポジション、ポートフォリオなどのテーブル定義
  - 初期化用関数 init_schema(db_path)（親ディレクトリ自動作成、冪等）
  - 既存 DB への接続取得 get_connection(db_path)

- パッケージ構成の骨組み（kabusys.strategy, kabusys.execution, kabusys.monitoring）
  - 各モジュール向けのプレースホルダ __init__（拡張して戦略や実行ロジック、監視処理を実装）

---

## セットアップ手順

想定環境
- Python 3.10 以上（型ヒントに PEP 604（| 型）を使用）
- OS: Linux / macOS / Windows

1. リポジトリをクローン（既にある場合は不要）:
   ```
   git clone <リポジトリURL>
   cd <プロジェクトルート>
   ```

2. 仮想環境を作成して有効化（推奨）:
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - 最低限 DuckDB が必要です（その他の依存はプロジェクトで追加してください）:
     ```
     pip install duckdb
     ```
   - パッケージとしてインストールする場合（pyproject.toml や setup がある場合）:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成してください（.env.example を参考に）。必須項目は下記参照。
   - 自動読み込み: パッケージインポート時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして無効化できます。

必須環境変数（Settings が参照するもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（任意・デフォルトあり）
- KABU_API_BASE_URL 例: http://localhost:18080/kabusapi （デフォルト）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （デフォルト: data/monitoring.db）
- KABUSYS_ENV （development / paper_trading / live）デフォルト: development
- LOG_LEVEL （DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト: INFO

例 .env（最低限のイメージ）:
```
JQUANTS_REFRESH_TOKEN="your_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="CXXXXXXX"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

- 設定の参照:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("環境:", settings.env)
print("ライブモードか:", settings.is_live)
```

- DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)
# DuckDB 接続を使ってクエリ実行できます
df = conn.execute("SELECT count(*) FROM prices_daily").fetchdf()
print(df)
```

- 既存 DB に接続（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

- .env 自動読み込みを無効化（テスト等で）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('auto env load disabled')"
```

---

## .env パーシングの特徴

- 空行および `#` で始まる行は無視
- `export KEY=val` 形式に対応
- 値にシングル／ダブルクォートがある場合、エスケープ（`\`）に対応して正しく抜き出します。クォートの閉じ以降（インラインコメント等）は無視されます。
- クォートなしの値では、`#` が前にスペースまたはタブがある場合のみコメントとして扱います
- 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
- .env.local は .env の上書き（override）として読み込まれ、OS 環境変数は保護され上書きされません

---

## ディレクトリ構成

プロジェクトの主要ファイル構成（src 以下）:

- src/
  - kabusys/
    - __init__.py                 # パッケージのメタ情報（__version__ 等）
    - config.py                   # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - strategy/
      - __init__.py               # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py               # 発注／実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py               # モニタリング・DB（拡張ポイント）

主要なソースファイルの説明:
- src/kabusys/config.py
  - プロジェクトルート検出（.git または pyproject.toml を基準）
  - .env / .env.local 読み込みロジック
  - Settings クラス（プロパティで環境変数を提供）
- src/kabusys/data/schema.py
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - インデックス定義
  - init_schema()：DB ファイルの親ディレクトリ作成・DDL 実行（冪等）
  - get_connection()：既存 DB への接続取得

---

## その他の注意点 / 開発メモ

- init_schema は既存のテーブルがあればスキップするため安全に何度でも呼べます。
- DuckDB のファイルを指定する際、":memory:" を指定するとインメモリ DB を使用可能です。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかである必要があります。無効な値を設定すると例外を投げます。
- LOG_LEVEL も事前定義されたレベルのみ受け付けます。

---

この README は現状のコードベース（設定読み込みとスキーマ定義）をもとにしたものです。戦略や実行ロジック、外部 API との連携（J-Quants、kabuステーション、Slack など）は別モジュールに実装してください。必要があれば、.env.example のテンプレートや追加の使い方（オーダー発行、シグナルの投入例など）を追記できます。