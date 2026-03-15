# KabuSys

日本株向けの自動売買システムの骨格ライブラリです。データレイヤ（Raw / Processed / Feature / Execution）を持つ DuckDB スキーマ定義、環境変数管理、戦略・実行・モニタリング用のモジュール群を含みます。

バージョン: 0.1.0

---

## 主な特徴

- 環境変数ベースの設定管理（.env/.env.local の自動読み込み、無効化オプションあり）
- DuckDB を用いた多層スキーマ定義（Raw / Processed / Feature / Execution）
- 発注・約定・ポジション管理のためのテーブル定義（signals, signal_queue, orders, trades, positions など）
- J-Quants / kabuステーション / Slack などの外部サービス連携用設定を想定
- テストや配布後も動作するように、.env の読み込みはプロジェクトルート（.git または pyproject.toml）を基準に実施

---

## 機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み
  - 必須環境変数の取得・バリデーション（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL の値検証（有効値を限定）
- データベーススキーマ
  - DuckDB 用のテーブル定義を一括で作成可能（init_schema）
  - インデックス定義を含む冪等な初期化処理
  - prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など
- API (簡易)
  - settings: 環境変数から設定を取得するクラス
  - init_schema / get_connection: DuckDB の初期化と接続取得

---

## 前提条件

- Python 3.10 以上（PEP 604 の型アノテーション (X | Y) を使用）
- 必要パッケージ（例）
  - duckdb

依存関係はプロジェクトの配布方法により requirements.txt または pyproject.toml に記載してください。最小限の例:

```
duckdb
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

```
git clone <repository-url>
cd <repository>
```

2. 仮想環境を作成・有効化（任意）

```
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. 依存パッケージをインストール

```
pip install duckdb
# または requirements.txt / pyproject.toml があればそれに従う
```

4. 環境変数を設定
   - プロジェクトルートに `.env` （および必要なら `.env.local`）を作成します。
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。

例: `.env`（必須キーのみ抜粋）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO           # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

- 自動ロードを無効にする場合:

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# Windows PowerShell:
# $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```

---

## 使い方

以下は基本的な使用例です。

- 設定値の取得

```python
from kabusys.config import settings

# 必須トークンや設定にアクセス
token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
duckdb_path = settings.duckdb_path
```

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)

# メモリ内 DB を使う場合
# conn = init_schema(":memory:")
```

- 既存 DB へ接続（スキーマの初期化を行わない）

```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# conn.execute("SELECT * FROM prices_daily LIMIT 1").fetchall()
```

- .env の読み込み挙動
  - 自動ロードはプロジェクトルートを基準に `.env` を先に読み込み、次に `.env.local` を読み込みます。
  - `.env` の読み込みでは既存の OS 環境変数を上書きしません（override=False）。
  - `.env.local` は override=True で読み込まれ、`.env` や OS 環境変数の上から値を上書きしますが、OS 環境変数は保護され上書きされません。
  - コメントや export 文、クォート（シングル/ダブル）のエスケープ処理に対応しています。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- KABUSYS_ENV (省略可, 有効値: development, paper_trading, live; デフォルト: development)
- LOG_LEVEL (省略可, 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env の自動読み込みを無効化)

必須の環境変数が未設定の場合、settings の該当プロパティにアクセスすると ValueError が発生します。

---

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義と初期化関数 (init_schema / get_connection)
    - strategy/
      - __init__.py            # 戦略関連モジュール（実装の拡張点）
    - execution/
      - __init__.py            # 発注・実行関連モジュール（実装の拡張点）
    - monitoring/
      - __init__.py            # モニタリング関連（実装の拡張点）

- .env.example                 # （推奨）テンプレート
- pyproject.toml / setup.py    # （任意）パッケージ管理ファイル

---

## 補足・注意点

- init_schema は冪等であり、既に存在するテーブルはそのままにして追加のテーブル・インデックスを作成します。
- DuckDB のファイルを永続化するディレクトリ（例: data/）は自動作成されます（init_schema 内で親ディレクトリを作成）。
- 現状の実装はスキーマ定義と設定管理を提供する骨格です。実際のデータ取得、戦略ロジック、注文送信（kabu API 呼び出し）、Slack 通知などは各モジュールで実装・拡張してください。
- 環境変数の自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使います。配布後に自動読み込みが不要・不都合な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

この README はコードベース（src/kabusys）に基づいて作成されています。実運用を行う際は、外部 API の認証情報や本番環境での動作確認、十分なテストを行ってください。