# KabuSys

日本株向けの自動売買システム（ライブラリ部分）。データ収集〜前処理〜特徴量生成〜発注管理までの基盤機能を提供します。

現時点の実装では、環境変数管理と DuckDB スキーマ定義／初期化を中心に提供しています。戦略（strategy）、発注（execution）、モニタリング（monitoring）用のモジュール用意済み（骨組み）です。

---

## 機能一覧

- 環境変数 / 設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（OS 環境変数が優先、`.env.local` が上書き）
  - 設定取得用の `Settings` クラス（必須値は未設定時に例外を送出）
  - 自動読み込み無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution の4層に対応したテーブル群を DDL として定義
  - インデックス作成、外部キー依存を考慮した作成順での初期化（冪等）
  - `init_schema(db_path)` による DB 初期化、`get_connection(db_path)` による接続取得
- パッケージ構成（将来的に）
  - `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`

---

## 必要条件

- Python 3.10+
- duckdb（DuckDB Python パッケージ）
- （運用時）kabuステーション API、J-Quants、Slack などの外部サービス用の認証情報

pip 例:
```
pip install duckdb
```

（プロジェクト配布方法によっては `pip install -e .` などでインストールします）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb
   # またはプロジェクトに requirements があればそれを使用
   ```
4. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成して環境変数を設定
   - 自動読み込みはパッケージ import 時に実行されます
   - テストなどで自動読み込みを無効にする場合は、プロセス起動前に環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 環境変数（.env 例）

以下は主要な環境変数例です（必要に応じて追加／変更してください）。`.env.example` を参考に作成してください。

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi   # オプション（デフォルトは上記）

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベース
DUCKDB_PATH=data/kabusys.duckdb      # デフォルト
SQLITE_PATH=data/monitoring.db       # （モニタリング用）

# システム
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

- 必須の値（未設定時は `Settings` が例外を出します）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

---

## 使い方

以下は基本的な利用例です。

- バージョン確認 / モジュール参照
```python
import kabusys
print(kabusys.__version__)  # 例: "0.1.0"
```

- 設定（Settings）を参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # デフォルト: data/kabusys.duckdb
conn = init_schema(db_path)     # テーブルとインデックスを作成して接続を返す
# conn を使ってクエリを実行可能
conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- インメモリ DB を使った初期化（テスト等）
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
# テスト用にインメモリ DB を利用可能
```

- 既存 DB への接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みの制御
  - デフォルトでパッケージ import 時に、プロジェクトルート（.git または pyproject.toml がある場所）から `.env` → `.env.local` を読み込みます。
  - OS 環境変数は上書きされません（`.env.local` は OS 環境変数以外を上書き可能）。
  - 自動読み込みを無効にするには、インポート前に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル／モジュール（src 配下）:

- src/kabusys/
  - __init__.py            # パッケージ定義（__version__, __all__）
  - config.py              # 環境変数・設定管理と Settings クラス
  - data/
    - __init__.py
    - schema.py            # DuckDB スキーマ定義と init_schema / get_connection
  - strategy/
    - __init__.py          # 戦略関連モジュール（将来の実装）
  - execution/
    - __init__.py          # 発注・約定管理（将来の実装）
  - monitoring/
    - __init__.py          # モニタリング（将来の実装）

主要ファイルの役割:
- config.py: .env のパース（クォートやコメントの考慮）と自動読み込み、Settings による安全な設定取得を実現。
- data/schema.py: Raw / Processed / Feature / Execution 層のテーブル DDL を定義。`init_schema()` で DB を作成・初期化。

---

## 開発・貢献

- バグ報告や機能追加は Issue を立ててください。
- ローカルでの開発は仮想環境を使い、依存パッケージをインストールしてから行ってください。
- 自動 .env 読み込みはテストで影響するので、テスト実行前に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定しておくことを推奨します。

---

## ライセンス / 注意事項

- 本プロジェクトは投資助言を目的とするものではなく、実際の運用（特に本番環境での自動売買）は自己責任で行ってください。
- 実運用時は API キーやパスワードの取り扱い（権限、ログ出力、ストレージ）に十分注意してください。

---

必要であれば README に CI、テスト、より詳細な .env.example、DB クエリ例、テーブル説明（DataSchema.md の要約）などを追記できます。ご希望があれば教えてください。