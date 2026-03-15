README
=====

プロジェクト概要
-------------
KabuSys は日本株向けの自動売買システム向けの Python パッケージの骨組みです。  
モジュールはデータ取得、売買戦略、注文実行、モニタリングのサブパッケージに分かれており、環境変数ベースの設定管理機能を備えています。

バージョン: 0.1.0

主な特徴
-------
- 環境変数 / .env ファイルによる設定読み込み（自動ロード機能）
- .env の柔軟なパース（export プレフィックス、クォート、エスケープ、コメント処理）
- プロジェクトルート自動検出（.git または pyproject.toml を基準）
- J-Quants / kabuステーション / Slack / DB パス等の共通設定を提供
- 開発・ペーパー取引・本番（live）を切り替える環境設定

機能一覧
--------
- 設定管理モジュール (src/kabusys/config.py)
  - OS 環境変数と .env/.env.local から設定を読み込み
  - 必須設定の検査（未設定時は ValueError を投げる）
  - env（development/paper_trading/live）とログレベルの検証
  - DB パス（DuckDB/SQLite）の Path オブジェクト変換
- パッケージ構成（拡張可能）
  - data, strategy, execution, monitoring のサブパッケージを想定

セットアップ手順
--------------
前提
- Python 3.10 以上（型ヒントで | 演算子を使用しているため）

手順（開発向け）
1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

3. パッケージをインストール（開発モード）:
   pip install -e .

4. 環境変数を設定:
   - プロジェクトルートに .env ファイルを作成するか、OS 環境変数で設定します。
   - 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方
-----
設定の読み取り（例）:
- Python コード中で設定を参照するには settings を使います。

例:
from kabusys.config import settings

# 必須トークン取得（未設定時は ValueError）
refresh_token = settings.jquants_refresh_token

# kabu API のパスワード
kabu_pw = settings.kabu_api_password

# DB パス（Path オブジェクト）
duckdb_path = settings.duckdb_path
sqlite_path = settings.sqlite_path

# 実行環境判定
if settings.is_live:
    print("ライブ運用モードです")

自動 .env 読み込みの挙動
- 読み込み順序（優先度高 → 低）:
  1. OS 環境変数
  2. .env.local（存在する場合、.env を上書きする。ただし OS 環境変数は保持）
  3. .env
- .env のパース対応:
  - export KEY=val 形式に対応
  - シングル/ダブルクォートされた値、エスケープシーケンス対応
  - クォートなしの値は、'#' の直前がスペース/タブの場合にコメントと認識
- 自動ロードのトリガー:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点として .env/.env.local を読み込みます
  - テスト等で自動ロードを無効にしたい場合:
    KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env（例）
- プロジェクトルートに配置する .env の例:
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
# KABU_API_BASE_URL を省略するとデフォルト http://localhost:18080/kabusapi が使われます
SLACK_BOT_TOKEN="xoxb-...."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"
KABUSYS_ENV=development
LOG_LEVEL=INFO

- .env.example を参照して必要な値を用意してください（リポジトリに .env.example がある想定）。

環境変数一覧（主要）
- 必須（未設定時に ValueError）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - KABUSYS_ENV: デフォルト "development"（有効値: "development", "paper_trading", "live"）
  - LOG_LEVEL: デフォルト "INFO"（有効値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動読み込みを無効化

注意事項
--------
- settings のプロパティ（例: jquants_refresh_token）は環境変数が未設定だと ValueError を送出します。実行前に必ず必要な環境変数を設定してください。
- .env の自動読み込みはパッケージ初回インポート時に行われます。テストで独自に環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

パッケージ構成（ディレクトリ構成）
-------------------------------
以下はソースの主要ファイル・ディレクトリです:

src/
  kabusys/
    __init__.py                # パッケージ初期化（__version__ = "0.1.0"、__all__）
    config.py                  # 環境変数・設定管理モジュール
    data/
      __init__.py              # データ関連サブパッケージ
    strategy/
      __init__.py              # 売買戦略サブパッケージ
    execution/
      __init__.py              # 注文実行サブパッケージ
    monitoring/
      __init__.py              # モニタリングサブパッケージ

貢献・拡張
---------
- サブパッケージ（data / strategy / execution / monitoring）に機能を実装して拡張してください。
- 設定キーが増えた場合は config.Settings にプロパティを追加し、.env.example を更新してください。

ライセンス
--------
- 本リポジトリにライセンスファイルがあればそちらを参照してください（未記載の場合はプロジェクト方針に従って追加してください）。

お問い合わせ
----------
問題や質問があれば Issue を立てるか、リポジトリのメンテナに連絡してください。