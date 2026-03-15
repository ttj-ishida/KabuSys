KabuSys — 日本株自動売買システム
================================

プロジェクト概要
---------------
KabuSys は日本株の自動売買を想定した、モジュール化されたリサーチ／実行基盤です。  
主要コンポーネントとして、環境設定読み込み、データ永続化（DuckDB スキーマ）、戦略・特徴量層、発注管理、モニタリングなどの土台を提供します。  
（このリポジトリは基盤ライブラリ部分を含み、戦略や実行ロジックの実装は各モジュールを拡張して行います。）

主な機能一覧
-------------
- 環境変数・設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（起動ディレクトリに依存しないプロジェクトルート探索）
  - 必須設定の取得とバリデーション（例: JQUANTS_REFRESH_TOKEN 等）
  - 自動読み込みの無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- データレイヤ（DuckDB）
  - Raw / Processed / Feature / Execution の 3+1 層スキーマ定義
  - インデックス定義、外部キー・制約付きのテーブル群
  - スキーマ初期化関数（init_schema）と接続取得（get_connection）
- 戦略（strategy）／発注（execution）／モニタリング（monitoring）用のパッケージ骨組み
  - 各機能を拡張してユーザー戦略や実行ロジックを実装可能

セットアップ手順
----------------

前提
- Python 3.8+ を推奨
- Git（ソースをクローンする場合）
- 必要パッケージ: duckdb 等（下記インストール参照）

1) リポジトリをクローン（またはソースを取得）
   - git clone <repo-url>

2) 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3) 依存パッケージのインストール
   - pip install duckdb
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   - 開発インストール例（プロジェクトルートで）:
     pip install -e .

環境変数（.env）
----------------
プロジェクトは起点となるファイル（.git または pyproject.toml）を基にプロジェクトルートを探索し、以下の優先順位で環境変数を読み込みます:
OS 環境変数 > .env.local > .env

自動読み込みを無効化したい場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（README 用の一覧。実運用では .env.example を参照してください）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

使い方（基本例）
----------------

1) 設定値の取得
- コード中で settings オブジェクトを使って環境設定を参照できます。

例:
from kabusys.config import settings
token = settings.jquants_refresh_token
if settings.is_live:
    # 本番向け処理

2) DuckDB スキーマ初期化
- データベースファイルを自動作成し、必要なテーブル・インデックスを作成します。

例:
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（DuckDBPyConnection）

3) 既存 DB へ接続
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)

4) 自動環境読み込みを無効化してテストしたい場合
- 実行前に環境変数をセット:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # Unix/macOS
  setx KABUSYS_DISABLE_AUTO_ENV_LOAD 1     # Windows（永続設定）

ディレクトリ構成
-----------------
（主要ファイルと役割）

- src/
  - kabusys/
    - __init__.py              : パッケージ定義（バージョン等）
    - config.py                : 環境変数・設定管理（自動 .env 読込・検証）
    - data/
      - __init__.py
      - schema.py              : DuckDB スキーマ定義・初期化関数（init_schema / get_connection）
    - strategy/
      - __init__.py            : 戦略モジュールのエントリポイント（拡張用）
    - execution/
      - __init__.py            : 発注／実行モジュールのエントリポイント（拡張用）
    - monitoring/
      - __init__.py            : 監視関連モジュール（拡張用）

補足・実装上の注意
-----------------
- .env パーサは単純なシェル風の行をパースします（export プレフィックス対応、シングル/ダブルクォート対応、インラインコメント処理など）。
- settings のプロパティは未設定時に ValueError を投げるものがあるため、必須変数は .env または OS 環境で確実に設定しておいてください。
- DuckDB の init_schema は冪等（既存テーブルはそのまま）です。初回起動時に呼ぶことでスキーマを用意できます。

開発・拡張
----------
- strategy、execution、monitoring パッケージは拡張ポイントです。独自の戦略・発注パイプライン・監視ロジックを実装して統合してください。
- テストや CI で自動 .env ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

ライセンスや貢献についてはリポジトリのトップレベルファイル（LICENSE / CONTRIBUTING 等）を参照してください。