# KabuSys

日本株向けの自動売買システムの基盤ライブラリ（KabuSys）。  
市場データの収集・整形・特徴量作成、発注/約定/ポジション管理のためのスキーマや環境設定ユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下のような自動売買システム構築に必要な基盤を提供します。

- 環境変数/.env の読み込み・管理（自動ロード機構付き）
- DuckDB を利用したデータスキーマ（Raw / Processed / Feature / Execution 層）
- 設定取得用の Settings API（J-Quants / kabuステーション / Slack / DB パス等）

現在の実装は主にライブラリ層（設定管理、DB スキーマ定義）を提供しており、戦略・発注ロジックは別モジュールで実装できます。

---

## 主な機能

- .env ファイルのパース（シングル/ダブルクォート、エスケープ、コメント処理に対応）
- 自動 .env ライフサイクル:
  - 読み込み順: OS 環境変数 > .env.local > .env
  - OS 既存の環境変数は保護される（上書きされない）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能
- Settings クラスで必須/任意設定を型的に取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
- DuckDB 用スキーマ定義と初期化ユーティリティ
  - Raw / Processed / Feature / Execution の各層テーブル
  - インデックス作成（頻出クエリに対する最適化）
  - init_schema() で冪等にテーブルを作成可能
  - :memory: を指定してインメモリ DB を利用可能

---

## 要件

- Python 3.9+
- duckdb Python パッケージ

必要に応じて他の依存を追加してください（戦略・発注を統合する場合は関連ライブラリなど）。

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトを配置）
   ```
   git clone <リポジトリURL>
   cd <プロジェクトルート>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数ファイルの準備
   - プロジェクトルートに `.env`（および必要であれば `.env.local`）を配置します。
   - 例は次節を参照してください。

---

## 環境変数 (.env) の例

必須項目（実運用前に必ず設定してください）:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他（任意/デフォルトあり）:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

.example:
```
# .env の例
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token_here"
KABU_API_PASSWORD="your_kabu_api_password_here"
SLACK_BOT_TOKEN="xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx"
SLACK_CHANNEL_ID="C0123456789"

KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

.env のパースはシングル/ダブルクォート、エスケープ文字、行頭の `#` コメントや行内コメント（一部条件）に対応しています。

---

## 使い方（簡単なコード例）

設定の取得:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("env:", settings.env)
print("is_live:", settings.is_live)
```

DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

既存 DB へ接続（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

インメモリ DB を使う場合:
```python
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
```

自動 .env 読み込みを無効にしてテスト等で明示的に環境を設定したい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# または Windows (PowerShell)
$env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```

---

## ディレクトリ構成

プロジェクトの主要ファイル/ディレクトリ構成（src 配下）:

- src/
  - kabusys/
    - __init__.py                (パッケージ定義、バージョン)
    - config.py                  (環境変数/設定管理)
    - data/
      - __init__.py
      - schema.py                (DuckDB スキーマ定義・初期化)
    - strategy/
      - __init__.py              (戦略関連のエントリポイント)
    - execution/
      - __init__.py              (発注/実行関連のエントリポイント)
    - monitoring/
      - __init__.py              (監視/ログ収集関連)

主要モジュール:
- kabusys.config
  - Settings クラス: settings インスタンスでアクセス
  - 自動 .env 読み込み（プロジェクトルートに .env, .env.local がある場合）
- kabusys.data.schema
  - init_schema(db_path): テーブルとインデックスを作成して接続を返す
  - get_connection(db_path): 既存 DB に接続する

---

## 注意事項 / 実運用へのヒント

- .env.local は .env の上書き用（優先度が高い）です。ただし、既に OS 環境変数に設定されているキーは上書きされません（保護）。
- KABUSYS_ENV によって本番/ペーパー/開発の挙動を切り替えられるように設計されています（ただし、実際の発注処理は別途実装が必要です）。
- DuckDB のファイルパス parent ディレクトリが存在しない場合は自動で作成されます。
- スキーマ定義は冪等（すでにテーブルが存在していればスキップ）なので、複数回 init_schema を呼んでも安全です。
- セキュリティ: API キーやパスワードはリポジトリにコミットしないでください。`.gitignore` に `.env` を追加することを推奨します。

---

必要に応じて、戦略実装・発注実装・監視ダッシュボードなどの上位レイヤーをこの基盤に積み上げてください。追加の機能や使い方のサンプルが必要であれば教えてください。