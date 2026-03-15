# KabuSys

日本株自動売買システムのための軽量ライブラリ。データ収集・スキーマ定義・環境設定管理・実行/戦略/監視モジュールの基盤を提供します。

バージョン: 0.1.0

概要
- DuckDB を用いたローカルデータベーススキーマ（Raw / Processed / Feature / Execution の4層）を提供します。
- 環境変数管理（.env の自動読み込み、必須変数チェック）を備え、kabuステーション API / J-Quants / Slack など外部連携用の設定を想定しています。
- strategy, execution, monitoring 等のサブパッケージのための骨組み（API エントリポイント）を含みます。

主な機能
- 環境設定管理
  - .env / .env.local ファイルを自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数の取得ヘルパー（未設定時は ValueError を送出）
  - 実行環境（development / paper_trading / live）およびログレベルの検証
  - 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution のテーブルをDDLで定義
  - init_schema(db_path) でテーブルとインデックスを冪等に作成
  - get_connection(db_path) で既存 DB に接続
- パッケージ構成
  - data（スキーマ・DB関連）
  - strategy（戦略ロジックを配置するためのプレースホルダ）
  - execution（注文・約定処理のプレースホルダ）
  - monitoring（監視用のプレースホルダ）

要件
- Python 3.10 以上（型アノテーションで | 型が使われています）
- duckdb Python パッケージ

セットアップ手順

1. リポジトリをクローン（ローカルで開発する場合）
   - git clone ...（省略）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （パッケージ配布用に setup/pyproject があれば）pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

.env で設定すべき主なキー（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb  # 任意（デフォルト）
- SQLITE_PATH=data/monitoring.db   # 任意（デフォルト）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

例: .env.example
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

挙動（自動 .env 読み込みの詳細）
- プロジェクトルート判定はパッケージ内ファイル位置から親ディレクトリを遡って .git または pyproject.toml を探します。見つからなければ自動読み込みをスキップします（テスト等で安全）。
- 読み込み順序: OS 環境変数 > .env.local > .env
  - 最初に os.environ のキー集合を保護キーとして取得し、.env を override=False で読み込む（未設定キーのみ設定）。
  - 次に .env.local を override=True で読み込むが、保護キー（既存 OS 環境変数）については上書きを行いません。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込み処理自体をスキップします。
- .env のパースはシングル/ダブルクォートやエスケープ、コメントの取り扱いに対応しています。

使い方（簡単なコード例）

- 設定値を参照する
```
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

- DuckDB スキーマ初期化（最初の一度）
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成し、テーブルを作る
```

- 既存 DB に接続（スキーマ初期化は行わない）
```
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# conn.execute("SELECT COUNT(*) FROM prices_daily").fetchall()
```

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py  — パッケージ初期化（__version__, __all__）
  - config.py    — 環境変数・設定管理（Settings クラス）
  - data/
    - __init__.py
    - schema.py  — DuckDB スキーマ定義と init_schema / get_connection
  - strategy/
    - __init__.py  — 戦略モジュール（プレースホルダ）
  - execution/
    - __init__.py  — 実行（注文・約定）モジュール（プレースホルダ）
  - monitoring/
    - __init__.py  — 監視モジュール（プレースホルダ）

開発メモ / 注意点
- init_schema は冪等（既存テーブルがあればスキップ）なので、初回起動時に安心して呼べます。
- Settings は必要な環境変数が無い場合に ValueError を送出します。デプロイ前に .env を整備してください。
- DuckDB のパスの親ディレクトリは自動的に作成されます（:memory: はそのままインメモリ DB として動作）。
- packages の戦略・実行・監視は現時点では骨組みのため、具体的な売買ロジックや注文送信の実装を追加してください。

貢献 / ライセンス
- この README はコードベースの概要をまとめたものです。実運用する場合はテスト・エラーハンドリング・認証情報の安全な管理（シークレット管理）を必ず行ってください。