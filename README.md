KabuSys
======

日本株向けの自動売買システム用ライブラリ（骨組み）。
本リポジトリは環境変数／設定管理を中心に、データ取得・ストラテジ・注文実行・モニタリング用のパッケージ構成を提供します。実際の戦略や実行ロジックは各モジュールに実装して拡張します。

バージョン
----------
0.1.0

主な機能
--------
- 環境変数管理 (.env / .env.local の自動読み込み)
  - プロジェクトルート（.git または pyproject.toml）を基準に .env を探すため、CWD に依存しない。
  - .env と .env.local の読み込み順序をサポート（.env.local が上書き）。
  - export KEY=val、クォート付き文字列、インラインコメント等に対応したパーサ実装。
  - OS 環境変数は保護され、.env による上書きは制御可能。
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
- Settings クラスによる型付きアクセス
  - J-Quants・kabuステーション・Slack・DBパス等の設定をプロパティで提供。
  - 必須環境変数未設定時は ValueError を送出して明確に失敗。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
- パッケージ構造の雛形
  - data / strategy / execution / monitoring の各サブパッケージを用意。

セットアップ
-----------
1. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 本パッケージをインストール（編集可能インストール）
   - pip install -e .

   ※依存パッケージ（requests 等）は実プロジェクトに応じて pyproject.toml / requirements.txt に追加してください。

3. 環境変数の準備
   - プロジェクトルートに .env を作成してください。自動で読み込まれます。
   - .env.local を置くと .env を上書き（優先）できます。

例: .env（テンプレート）
-----------------------
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時はデフォルトを使用）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境（development | paper_trading | live）
KABUSYS_ENV=development

# ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）
LOG_LEVEL=INFO

自動読み込みを無効化する（テストなど）
------------------------------------
自動で .env を読み込ませたくない場合:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------
- 設定値を取得する

  from kabusys.config import settings

  # 必須値は設定されていなければ ValueError が発生します
  token = settings.jquants_refresh_token
  password = settings.kabu_api_password

  # オプション値の取得（デフォルト付き）
  base_url = settings.kabu_api_base_url  # デフォルト: http://localhost:18080/kabusapi
  duckdb_path = settings.duckdb_path      # Path オブジェクト
  sqlite_path = settings.sqlite_path

  # 実行環境判定
  if settings.is_live:
      # 実売買用処理
      pass
  elif settings.is_paper:
      # ペーパートレード用処理
      pass

- エラー挙動
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID が未設定の場合、
    対応プロパティにアクセスすると ValueError が送出されます（.env.example を作成して設定してください）。

内部の .env パースの注意点
--------------------------
- export KEY=val 形式をサポートします。
- 値がシングル/ダブルクォートで囲まれている場合、バックスラッシュによるエスケープ処理を行い、閉じクォートまでを値として扱います（以降のインラインコメントは無視）。
- クォートなしの場合は、'#' の直前がスペースまたはタブであればコメントとして認識されます（それ以外は '#' を値の一部として扱います）。
- OS 環境変数は protected として扱われ、.env による上書きを制御します。

ディレクトリ構成
----------------
リポジトリの主要ファイル／ディレクトリ:

- src/
  - kabusys/
    - __init__.py                # パッケージ初期化（__version__ 等）
    - config.py                  # 環境変数 / 設定管理ロジック（自動 .env ロード、Settings）
    - data/
      - __init__.py              # データ取得関連モジュール（拡張用）
    - strategy/
      - __init__.py              # 戦略（ストラテジ）関連モジュール（拡張用）
    - execution/
      - __init__.py              # 注文実行・ブローカー連携（拡張用）
    - monitoring/
      - __init__.py              # モニタリング関連（拡張用）

開発・拡張のヒント
------------------
- strategy / execution / data / monitoring は空のパッケージ雛形です。具体的なアルゴリズムや API クライアントはここに実装してください。
- Secrets（API トークン等）は .env または環境変数で管理してください。リポジトリに直接コミットしないでください。
- テスト時などで .env の自動ロードを妨げたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからテストを実行してください。

連絡・ライセンス
----------------
本 README はリポジトリに含まれるコードを基に作成しています。ライセンスやコントリビューション方法はプロジェクトのルートにある LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。