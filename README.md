# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（ライブラリ）です。  
環境変数による設定管理、株価データ／戦略／発注／監視といったモジュールを想定したパッケージ構成を提供します（現状は主要な設定ロード処理が実装されています）。

バージョン: 0.1.0

---

## 主な機能

- 環境変数 / .env ファイルによる設定管理
  - .env, .env.local の自動読み込み（OS 環境変数は優先）
  - クォートやエスケープ、コメントに対応した .env パーサ
  - 必須設定が未定義の場合はエラーを発生
- J-Quants / kabuステーション / Slack / データベース関連の設定プロパティを提供
- パッケージ化されたモジュール構成（data, strategy, execution, monitoring）を用意

（注）現状のリポジトリでは設定ロードの実装が中心で、実際の売買戦略や発注実装は各モジュールに実装していく想定です。

---

## 機能一覧（概要）

- 環境変数読み込みとアクセス（kabusys.config.Settings）
  - jquants_refresh_token（JQUANTS_REFRESH_TOKEN、必須）
  - kabu_api_password（KABU_API_PASSWORD、必須）
  - kabu_api_base_url（KABU_API_BASE_URL、デフォルト: http://localhost:18080/kabusapi）
  - slack_bot_token（SLACK_BOT_TOKEN、必須）
  - slack_channel_id（SLACK_CHANNEL_ID、必須）
  - duckdb_path（DUCKDB_PATH、デフォルト: data/kabusys.duckdb）
  - sqlite_path（SQLITE_PATH、デフォルト: data/monitoring.db）
  - env（KABUSYS_ENV、development/paper_trading/live）
  - log_level（LOG_LEVEL、DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - is_live / is_paper / is_dev ブールプロパティ

---

## 動作条件（推奨）

- Python 3.9+（typing の Union 表記や Pathlib を使用）
- 必要に応じて使用する外部ライブラリ（例: duckdb, sqlalchemy, slack-sdk 等）は個別に導入してください

---

## セットアップ

1. リポジトリをクローン（既にファイルがある前提なら不要）
   - git clone ...

2. 仮想環境を作成して有効化
   - macOS / Linux
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell)
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. パッケージを開発モードでインストール
   - pip install -e .

4. 必要な追加パッケージ（例）
   - pip install duckdb slack-sdk など（プロジェクト要件に応じて）

---

## 環境変数（.env）設定

自動読み込みの順序（優先順位）
- OS 環境変数（最優先）
- プロジェクトルートの .env
- プロジェクトルートの .env.local（.env の上書き、ただし OS 環境変数は上書きされない）

自動ロードはデフォルトで有効です。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時などに利用）。

必須となる環境変数（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (default: INFO)

.example .env:
```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabu ステーション
KABU_API_PASSWORD="your_kabu_api_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"

# Slack
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"

# DB paths
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env パーサの特徴
- 行頭の `export KEY=val` 形式に対応
- シングル/ダブルクォート内のエスケープ（\）を正しく扱う
- クォートなしの値では、`#` の直前が空白またはタブの場合はコメントと認識

---

## 使い方（簡単な例）

Python スクリプトや REPL から設定にアクセスする例：

```python
from kabusys import __version__
from kabusys.config import settings

print("KabuSys version:", __version__)
print("環境:", settings.env)
print("ログレベル:", settings.log_level)

# 必須値の参照（未設定の場合は ValueError が発生）
token = settings.jquants_refresh_token
kabu_pw = settings.kabu_api_password

if settings.is_dev:
    print("開発環境です")
```

自動環境ロードを無効化してテスト等を行う場合：

- プロセス起動時に環境変数を設定して無効化
  - Linux/macOS: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -c "from kabusys.config import settings; ..."
  - Windows (PowerShell): $env:KABUSYS_DISABLE_AUTO_ENV_LOAD=1; python -c "..."

またはプロジェクトルートに適切な .env / .env.local を配置して運用してください。

---

## ディレクトリ構成

現状の主要ファイルとディレクトリ:

- src/
  - kabusys/
    - __init__.py          # パッケージエントリ、__version__ 等
    - config.py            # 環境変数 / .env の読み込み・Settings 実装
    - data/
      - __init__.py        # データ取得・管理に関するモジュール用
    - strategy/
      - __init__.py        # 売買戦略の実装用
    - execution/
      - __init__.py        # 発注 / 実行ロジック用
    - monitoring/
      - __init__.py        # 監視・通知関連の実装用

README や .env.example 等はリポジトリルートに配置してください（プロジェクトルートの判定は .git または pyproject.toml を使用します）。

---

## 注意事項 / 実運用について

- 実際の売買を行う場合は、必ずペーパートレード環境で十分に検証してください。KabuSys は現状設定管理の骨組みを提供するものであり、戦略と発注のロジックは利用者が実装・検証する必要があります。
- 機密情報（APIトークン、パスワード等）は .env ファイルや CI シークレットなど安全な方法で管理してください。
- KABUSYS_ENV が `live` の場合は実取引に繋がる想定です。環境設定を誤らないようご注意ください。

---

## 貢献 / ライセンス

現時点でライセンスやコントリビューションガイドラインはプロジェクトルートに明示していないため、追加することを推奨します。プルリクエストや issue での相談を歓迎します。

---

ご不明点があれば、利用したいケース（例: J-Quants 連携例や Slack 通知の実装）を教えてください。追加の使い方サンプルやテンプレートを作成します。