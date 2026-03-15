# KabuSys

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。データ管理（DuckDB スキーマ）、環境設定読み込み、戦略／発注／モニタリング用のモジュールを備え、ローカルでのペーパートレードやライブ運用に対応できる設計になっています。

バージョン: 0.1.0

## 主な特徴
- 環境変数／`.env` ファイルの自動読み込み（プロジェクトルート検出）
- 型付けされたアプリケーション設定（必須・任意の環境変数プロパティを提供）
- DuckDB を利用した階層化されたデータスキーマと初期化関数
  - Raw / Processed / Feature / Execution 層を想定したテーブル定義
- モジュール分割（data, strategy, execution, monitoring）による拡張容易性
- .env の堅牢なパース（クォート、コメント、export 形式などに対応）
- 自動ロードの無効化オプション（テスト用）

## 機能一覧
- 環境設定
  - 自動的に .env / .env.local をプロジェクトルートから読み込み（OS 環境変数が優先）
  - 必須項目未設定時は ValueError を発生させるプロパティ（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境（development / paper_trading / live）やログレベルの検証
- データ
  - DuckDB 用のスキーマ定義（テーブル + インデックス）
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path) で既存 DB に接続
- パッケージ構成
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を想定した構造

## 要求環境
- Python 3.10 以上（typing における PEP 604 の union 型などを使用）
- duckdb Python パッケージ（データベース処理に使用）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb
# 開発中のパッケージとして使いたい場合（プロジェクトに setup/pyproject があることを想定）
pip install -e .
```

## セットアップ手順

1. リポジトリをクローンして仮想環境を用意
2. 依存パッケージをインストール（最低限 duckdb）
3. プロジェクトルートに `.env`（および開発用に`.env.local`）を作成
   - 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. DuckDB スキーマを初期化

### 必須の環境変数（主なもの）
以下は Settings クラスが参照する代表的な環境変数です。実際の運用では .env.example を参照して設定してください。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例（.env の一例）:
```
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

## 使い方（さっと使える例）

- Settings を参照する:
```python
from kabusys.config import settings

print(settings.env)  # development / paper_trading / live
print(settings.duckdb_path)  # Path オブジェクト
# 必須値を直接参照すると未設定時に ValueError が発生する
token = settings.jquants_refresh_token
```

- DuckDB スキーマを初期化する:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path に基づいて DB ファイルを作成し、スキーマを初期化
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 既存 DB に接続する:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- テストや一時実行でインメモリ DB を使う:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

## 注意事項 / 実装のポイント
- .env の自動ロード優先順位は次のとおり:
  1. OS 環境変数
  2. .env.local（存在すれば .env より優先して上書き。ただし OS 環境変数は保護）
  3. .env
- .env のパースはクォートやエスケープ、export 形式、コメントに対応しています。
- Settings._require は未設定の場合に ValueError を投げるため、起動時に必須環境変数の漏れが検出されます。
- DuckDB のスキーマは冪等で、既存テーブルがあれば上書きしません。親ディレクトリが存在しない場合は自動作成します。

## ディレクトリ構成
（プロジェクトルートを想定した最小構成）

- src/
  - kabusys/
    - __init__.py                # パッケージのメタ情報（__version__ 等）
    - config.py                  # 環境変数／設定の読み込みと Settings クラス
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py              # 戦略関連コード配置予定
    - execution/
      - __init__.py              # 発注／実行関連コード配置予定
    - monitoring/
      - __init__.py              # 監視／ロギング／メトリクス関連配置予定

この README は現状のコードベース（config.py と data/schema.py を中心に実装済み）に基づいています。strategy / execution / monitoring モジュールは拡張ポイントとして用意されています。実運用に移す際は各種トークン・認証情報の安全な管理、ログ設定、例外処理、実取引時の十分な検証を行ってください。

貢献・質問があればリポジトリ上で Issue / PR をお願いします。