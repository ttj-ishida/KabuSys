# KabuSys

日本株自動売買システム（ライブラリ）。  
株価データ取得・ストラテジー実装・注文実行・監視用のモジュール群を提供することを想定したパッケージの骨組みです。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買に必要な機能をモジュール化したパッケージです。  
現在はプロジェクトの基本構造と環境変数設定の取り扱い周りの実装が含まれています（データ取得、ストラテジー、注文実行、監視のためのパッケージ・名前空間を用意）。

パッケージ公開時には、`src/kabusys` 以下に次のサブパッケージを想定しています:

- data — データ取得・保存関連
- strategy — 売買ルール（ストラテジー）
- execution — 注文発行ロジック（kabuステーション等）
- monitoring — 監視・ログ・通知関連

## 機能一覧

現状（0.1.0）で実装されている主な機能:

- 環境変数 / 設定の管理（Settings クラス）
  - 必須項目を取得し未設定時はエラーを投げる `_require` 実装
  - env（development / paper_trading / live）とログレベルの検証
  - パス（DuckDB / SQLite）を Path 型で取得
- プロジェクトルート自動検出（.git または pyproject.toml を基準）
- .env ファイル自動読み込み（`.env` → `.env.local`、`.env.local` が優先）
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能
- .env パーサ（export プレフィックス、クォート、エスケープ、コメント処理に対応）
- パッケージのエクスポート設定（`__all__`）

## 要件

- Python 3.10 以上（型ヒントに `|` を使用）
- （実際の利用では）kabuステーション API や J-Quants API の認証情報、Slack トークンなどが必要

## セットアップ手順（開発環境）

1. リポジトリをクローンする
   - 例: git clone <リポジトリURL>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. パッケージをインストール
   - 開発中: pip install -e .
   - あるいは依存管理に合わせて poetry / pip-tools 等を使用

4. 必要な環境変数を設定（次節参照）

## 環境変数 (.env) と自動読み込み

パッケージは起動時にプロジェクトルート（`.git` または `pyproject.toml` が存在するディレクトリ）を探索し、以下の順で `.env` を読み込みます:

1. OS 環境変数（既存のプロセス環境）
2. .env（ルート/.env）：未設定のキーのみ設定
3. .env.local（ルート/.env.local）：上書き可能（ただし OS 環境で既に存在するキーは上書きしない）

- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。
- .env の読み込みで OS 環境変数は「保護（protected）」され、.env/.env.local からは上書きされません。

### パーサの挙動（主な仕様）

- 空行・行頭 `#` は無視
- `export KEY=value` の `export ` プレフィックスに対応
- 値がシングル/ダブルクォートで囲まれている場合、内部のバックスラッシュエスケープを解釈して対応する閉じクォートまでを値として取り込む（その後の文字列はコメント等として無視）
- クォートなしの値では `#` が現れ、直前がスペースまたはタブの場合にコメントとみなす

### 必須・任意の環境変数（例）

必須（Settings._require により未設定時は ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite(DB) のファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト: INFO）

#### .env の例

例としてプロジェクトルートに `.env` を用意する:

JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token_here"
KABU_API_PASSWORD='your_kabu_password'
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN= xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
SQLITE_PATH=~/kabusys/data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

※ 実際のトークンやパスワードは漏洩に注意し、`.env.local` を gitignore に入れて管理することを推奨します。

## 使い方（簡単な例）

パッケージから設定を取得する例:

from kabusys.config import settings

# 必須キーが未設定だと ValueError が発生します
token = settings.jquants_refresh_token
kabu_password = settings.kabu_api_password

# 実行環境チェック
if settings.is_live:
    print("本番モードで実行します")
elif settings.is_paper:
    print("ペーパートレードモードです")
else:
    print("開発モードです")

# データベースパス
duckdb_path = settings.duckdb_path
sqlite_path = settings.sqlite_path

パッケージのエントリポイント（モジュール利用）:

import kabusys
print(kabusys.__version__)  # バージョン表示

将来的には次のようにサブパッケージを利用します:

from kabusys.data import ...
from kabusys.strategy import ...
from kabusys.execution import ...
from kabusys.monitoring import ...

（上記サブパッケージは骨組みとして用意されています。各自実装を追加してください。）

## エラーと挙動

- 必須環境変数が未設定の場合、Settings の該当プロパティアクセスで ValueError が送出されます（アプリケーション起動前に早めに検出できます）。
- .env ファイル読み込みに失敗した場合は警告が出ますが、動作は継続します。

## ディレクトリ構成

リポジトリ（主要ファイルのみ）の構成例:

.
├── pyproject.toml                # （存在する前提）プロジェクトルート検出に使用
├── .git/                         # （存在する場合）プロジェクトルート検出に使用
├── .env                          # 環境変数（任意）
├── .env.local                    # 環境毎の上書き（任意、.gitignore 推奨）
└── src
    └── kabusys
        ├── __init__.py           # パッケージ定義（__version__, __all__）
        ├── config.py             # 環境変数・設定管理（自動 .env ロード含む）
        ├── data
        │   └── __init__.py       # データ関連パッケージ（骨組み）
        ├── strategy
        │   └── __init__.py       # ストラテジー関連パッケージ（骨組み）
        ├── execution
        │   └── __init__.py       # 注文実行関連パッケージ（骨組み）
        └── monitoring
            └── __init__.py       # 監視・通知関連パッケージ（骨組み）

## 開発メモ / 注意点

- 機密情報（API トークン等）は `.env.local` に置き、`.gitignore` に追加してコミットしないでください。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、テストなどでカレントディレクトリだけを変更した場合に期待どおりに動作しないことはありません（__file__ を基準に探索します）。
- 必要に応じて Settings を拡張して他の設定や認証フロー（例: J-Quants の OAuth 更新処理等）を実装してください。

---

ご希望があれば、実際のデータ取得・ストラテジー・注文実行のテンプレートやサンプル実装、CI 設定、.env.example のファイルテンプレートなどを作成します。どの部分を優先して整備したいか教えてください。