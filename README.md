# KabuSys

日本株の自動売買システム（KabuSys）の軽量なコアパッケージです。  
このリポジトリは設定読み込みとパッケージ骨組み（データ取得、売買ロジック、注文実行、監視）を含みます。

バージョン: 0.1.0

## 概要
- Pythonパッケージとして提供される日本株自動売買システムの基盤モジュール群。
- 環境変数や .env ファイルから設定を安全に読み込む設定管理モジュールを含みます。
- 将来的にデータ取得（data）、ストラテジー（strategy）、注文実行（execution）、監視（monitoring）を実装するための名前空間を提供します。

## 機能一覧
- プロジェクトルート自動検出（.git または pyproject.toml を基準）
- .env / .env.local の自動読み込み（OS 環境 > .env.local > .env の優先順位）
- export プレフィックスやクォート/エスケープに対応した .env パース
- 必須設定を取得するときの検証（未設定時は ValueError を送出）
- 環境（development / paper_trading / live）とログレベルのバリデーション
- settings オブジェクト経由でのシンプルな設定アクセス

## 必要条件
- Python 3.10+
  - 型注釈で `Path | None` などの構文を使用しているため Python 3.10 以上を推奨します。

（実際に DuckDB や SQLite を利用する場合はそれらのパッケージを別途インストールしてください）

## セットアップ手順（開発向け）
1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成と有効化（例: venv）
   ```
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

4. 設定ファイルの準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - サンプルは下記「.env の例」を参照。

## 環境変数 (.env) の例
以下は最低限必要となる主要変数の例です。プロジェクトのルートに `.env` を置いてください。

```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabuステーション API
KABU_API_PASSWORD="your_kabu_api_password"
# (省略可能) デフォルト: http://localhost:18080/kabusapi
KABU_API_BASE_URL="http://localhost:18080/kabusapi"

# Slack
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"

# データベースファイルパス（省略可）
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"

# 実行環境: development | paper_trading | live
KABUSYS_ENV="development"

# ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_LEVEL="INFO"
```

.env に関する注意:
- `export KEY=val` 形式に対応します。
- 値が引用符で囲まれている場合、エスケープ文字（\）を解釈します。
- 引用符なしの値では、`#` の直前にスペースまたはタブがある場合にコメントとして認識します。

自動読み込みの挙動:
- 自動ロードの優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化したい場合（テスト等）は環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

## 重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API へのパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知の Bot トークン（必須）
- SLACK_CHANNEL_ID — 通知先の Slack チャンネル ID（必須）

これらは settings を経由してアクセスした際、未設定だと ValueError が発生します。

## 使い方（設定アクセス例）
Python コード内で設定を参照する例:

```py
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path
```

- settings.env: "development" / "paper_trading" / "live"
- settings.log_level: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

自動ロードを無効にしてテスト等で手動設定する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

## 実装上のポイント
- プロジェクトルートの検出は、現在ファイルの位置（__file__）から親を上がって `.git` または `pyproject.toml` の存在で行います。これにより作業ディレクトリに依存せずに .env を読み込みます。
- .env の読み込みでは既存の OS 環境変数を保護するために `protected` セットを使用し、.env.local は .env より優先して上書きします（ただし OS 環境変数は上書きされません）。

## ディレクトリ構成
リポジトリの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py              — パッケージ初期化（__version__ = 0.1.0）
    - config.py                — 環境変数・設定管理モジュール（自動 .env ロード、Settings）
    - data/
      - __init__.py            — データ取得名前空間
    - strategy/
      - __init__.py            — ストラテジー名前空間
    - execution/
      - __init__.py            — 注文実行名前空間
    - monitoring/
      - __init__.py            — 監視/モニタリング名前空間
- .env.example (任意で追加すると親切)
- pyproject.toml / setup.cfg / setup.py (プロジェクト管理ファイル、存在する想定)

## 今後の拡張
- data: 市場データフェッチャー、ヒストリカルデータ保存
- strategy: 売買ロジックのプラグイン化
- execution: 注文管理（kabuステーション連携）、リスク管理
- monitoring: 取引ログ、Slack通知、メトリクス収集

---

問題や機能追加の要望があれば issue を立ててください。