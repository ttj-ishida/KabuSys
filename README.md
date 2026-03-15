# KabuSys

日本株自動売買システム用のライブラリ基盤（プロトタイプ）。  
マーケットデータの保存・加工・特徴量生成から発注・モニタリングまでを想定したモジュール群と、DuckDB スキーマ・環境設定管理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買プラットフォーム構築を支援する Python パッケージです。  
現在の実装では以下を中心に提供します：

- 環境変数と .env ファイルからの設定読み込み（自動ロード）
- DuckDB におけるデータスキーマ定義（Raw / Processed / Feature / Execution レイヤ）
- スキーマ初期化ユーティリティ
- モジュール構成（data / strategy / execution / monitoring の骨組み）

将来的に戦略（strategy）・発注（execution）・監視（monitoring）モジュールを拡張していくことを想定しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数の取得とバリデーション
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
  - 自動ロード無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

- データスキーマ（kabusys.data.schema）
  - Raw、Processed、Feature、Execution 各レイヤーのテーブル定義
  - インデックス定義
  - init_schema(db_path) による冪等なスキーマ初期化
  - get_connection(db_path) による既存 DB への接続

- パッケージ骨組み
  - strategy、execution、monitoring モジュールのプレースホルダ

---

## セットアップ手順

前提:
- Python 3.10 以降（typing の | などを使用）
- pip が利用可能

1. リポジトリをクローン/配置
   (プロジェクトルートには .git または pyproject.toml があることを推奨)

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   最低限 DuckDB が必要です：
   ```
   pip install duckdb
   ```
   将来的に他の依存がある場合、requirements.txt または pyproject.toml を参照してください。

4. パッケージを開発モードでインストール（任意）
   プロジェクトに setup.py / pyproject.toml がある場合:
   ```
   pip install -e .
   ```

5. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（デフォルト）。  
   自動ロードを無効化したい場合は環境変数を設定します:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト値:
- KABUSYS_ENV: "development"（有効値: development, paper_trading, live）
- LOG_LEVEL: "INFO"（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
- DUCKDB_PATH: "data/kabusys.duckdb"
- SQLITE_PATH: "data/monitoring.db"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" にすると自動 .env ロードを無効化

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

注意: 自動ロードはプロジェクトルート（.git または pyproject.toml のある場所）を基準に行われます。

---

## 使い方（簡単な例）

- 設定取得:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 未設定なら例外
print(settings.kabu_api_base_url)
print(settings.is_dev)
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
from pathlib import Path

db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # files の親ディレクトリを自動作成し、全テーブルを作成
# conn は duckdb connection（使用例）
conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- 既存DBへ接続（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env ロードの挙動を制御
  - デフォルト: OS 環境変数 > .env.local > .env の順で読み込む
  - テスト時などに自動ロードを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## ディレクトリ構成

主要ファイル/ディレクトリ（省略可能な空 __init__.py を含む）:

- src/
  - kabusys/
    - __init__.py                # パッケージ定義（__version__ = "0.1.0"）
    - config.py                  # 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化 (init_schema, get_connection)
    - strategy/
      - __init__.py              # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py              # 発注/実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py              # 監視モジュール（拡張ポイント）

プロジェクトルートに .env / .env.local を置くと自動読み込みされます（条件: プロジェクトルートが .git または pyproject.toml で検出されること）。

---

## 開発メモ / 注意点

- Python の型ヒントで |（ユニオン記法）や Path | None を使っているため Python 3.10 以上が必要です。
- init_schema は冪等（既存テーブルがある場合はスキップ）なので安心して何度でも実行できます。
- .env ファイルパーサはシンプルに実装されていますが、クォートやエスケープ、コメントの扱いに配慮しています。特殊ケースはパーサ挙動に従ってください。
- config.Settings は実行時に必須の環境変数が不足していると ValueError を投げます。運用時は必須値を確実に設定してください。

---

必要であれば、README に加えて .env.example、開発セットアップ（tox / pre-commit 等）、テストコードの追加なども作成します。どうしますか？