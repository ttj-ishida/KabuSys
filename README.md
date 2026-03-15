# KabuSys

日本株の自動売買・分析を想定した軽量ライブラリ（パッケージ）です。  
データスキーマ定義、環境設定の読み込み、実行・戦略・監視用のパッケージ構成を提供します。

現在のバージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件 / インストール
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（.env）について
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムの基盤となるモジュール群です。
- データレイヤ（Raw / Processed / Feature / Execution）を想定した DuckDB スキーマを定義・初期化する機能を持ちます。
- 環境変数管理、API トークンなどの設定取得を行う Settings クラスを提供します。
- 将来的に strategy、execution、monitoring の実装を展開するためのパッケージ構成を備えています。

主な機能
- 環境変数自動読み込み（.env / .env.local）と Settings API（kabusys.config.settings）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基準に行います。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
- DuckDB 用スキーマの定義と初期化（kabusys.data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成、ファイルパスの親ディレクトリ自動作成などの利便性
- DB 接続取得ヘルパー（kabusys.data.schema.get_connection）
- パッケージメタ情報（kabusys.__version__）

必要条件 / インストール
- Python 3.10 以上（型記法に | を使用しているため）
- 依存パッケージ（最小）
  - duckdb

サンプルインストール手順（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb
# 開発中のソースを editable install する場合（プロジェクトルートに pyproject.toml / setup がある想定）
# pip install -e .
```

セットアップ手順
1. リポジトリをクローン / 取得する
2. Python 仮想環境を作成し、依存（duckdb 等）をインストールする
3. プロジェクトルートに .env（必要な環境変数）を作成する
   - 自動読み込み機能により、パッケージインポート時に .env と .env.local を読み込みます（ただし OS 環境変数が優先）
4. 初回は DuckDB スキーマを初期化する

使い方（簡単な例）
- 環境設定（Settings）の使用例:
```python
from kabusys.config import settings

# 必須環境変数が未設定の場合は ValueError が発生します
token = settings.jquants_refresh_token
api_base = settings.kabu_api_base_url
db_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path を使って初期化（ファイル DB）:
conn = init_schema(settings.duckdb_path)

# メモリ上 DB を使う場合:
# conn = init_schema(":memory:")
```

- 既存 DB へ接続（スキーマ初期化は行われません）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

環境変数（.env）について
- 自動読み込み
  - パッケージ import 時にプロジェクトルートを探索し、.env → .env.local の順で読み込みます（.env.local は上書き）。
  - OS 環境変数が優先され、既存の OS 環境変数は上書きされません（.env.local の override は可能ですが protected によって保護されます）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD に 1 を設定してください。

- 主要な環境変数（.env に設定する推奨キー）
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL : kabuステーション API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
  - DUCKDB_PATH : DuckDB ファイルパス（任意、デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 sqlite ファイルパス（任意、デフォルト: data/monitoring.db）
  - KABUSYS_ENV : 環境識別（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

- .env の例 (.env.example)
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意事項（設定の挙動）
- Settings は必須値が未設定だと ValueError を投げます（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
- KABUSYS_ENV と LOG_LEVEL は許容値チェックがあります。間違った値を入れると ValueError になります。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py              : パッケージ初期化、__version__
    - config.py                : 環境変数読み込み・Settings 定義（自動 .env ロード含む）
    - data/
      - __init__.py
      - schema.py              : DuckDB スキーマ定義 / init_schema / get_connection
    - strategy/
      - __init__.py            : 戦略モジュール（将来的な実装場所）
    - execution/
      - __init__.py            : 実行（発注・注文管理）モジュール（将来的な実装場所）
    - monitoring/
      - __init__.py            : 監視 / ロギング用モジュール（将来的な実装場所）

開発にあたって
- DuckDB のスキーマは冪等（存在確認して作成）なので、init_schema() は安心して何度でも呼べます。
- .env のパーサはシングル/ダブルクォート、export プレフィックス、行内コメントの扱いなどを考慮しています。
- プロジェクトルート判定は .git または pyproject.toml を基準にしているため、ローカルで開発するときは該当ファイルを配置しておくと自動ロードが機能します。

ライセンス・貢献
- 現状 README にライセンス情報は含まれていません。実際の公開時は LICENSE を追加してください。
- 貢献（PR / Issue）は歓迎します。設計方針としては「データ層とロジック層を分離し、テスト可能で再現性の高い処理」を目指してください。

---

お問い合わせ・補足があれば、どの部分を詳しく知りたいか教えてください。README の追加項目（例: API 仕様、DB スキーマの ER 図、実例スクリプトなど）も作成できます。