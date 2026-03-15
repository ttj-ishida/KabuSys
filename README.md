# KabuSys

KabuSys は日本株の自動売買（アルゴリズム取引）を目的としたパッケージです。データ収集、前処理、特徴量作成、発注／約定管理までの基本的なレイヤーを備え、DuckDB を用いたローカルデータ管理と外部 API（J-Quants、kabuステーション、Slack 等）との連携を想定しています。

バージョン: 0.1.0

主なエクスポートモジュール: `data`, `strategy`, `execution`, `monitoring`

---

## 機能一覧

- 環境変数/設定管理
  - `.env` / `.env.local` ファイルや OS 環境変数から設定を読み込む自動ロード機能
  - 必須設定の取得とバリデーション（環境、ログレベル等）
- データ層（DuckDB スキーマ）
  - 3 層（Raw / Processed / Feature）に加え Execution 層を想定したスキーマ定義
  - 価格、決算、ニュース、特徴量、AI スコア、シグナル、注文、取引、ポジション、ポートフォリオ等のテーブル定義
  - インデックス定義・テーブル作成を含むスキーマ初期化 API（冪等）
- モジュール分割による拡張可能なアーキテクチャ
  - `data`：DB スキーマとデータ操作
  - `strategy`：売買ロジック（フレームワーク）
  - `execution`：発注／約定ハンドリング（kabu API 等）
  - `monitoring`：監視・ログ／通知（Slack 等）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型注釈を利用）
- 必要ライブラリ（最小限）: duckdb
  - 他に J-Quants クライアントや kabu ステーション API クライアント、Slack SDK 等を利用する場合はそれらを追加でインストールしてください。

例（仮の手順）
1. リポジトリをクローンして、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成してください（下記の「環境変数」参照）。
   - 自動ロードはデフォルトで有効です（.git または pyproject.toml の存在する親ディレクトリをプロジェクトルートとして探索して `.env` → `.env.local` を読み込みます）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なキー）

Settings クラスで参照される主要なキー（必須のものは必須と記載）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、デフォルト: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (任意、デフォルト: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

例（.env の雛形）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースルールについて:
- 空行や `#` で始まる行は無視
- `export KEY=val` 形式に対応
- シングル/ダブルクォートで囲った値、バックスラッシュによるエスケープに対応
- クォート無しの場合、`#` の直前がスペース/タブのとき以降をコメントとして扱う

---

## 使い方（簡単なサンプル）

- 設定値の取得
  - settings を直接インポートして使用します。

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
```

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema, get_connection
from pathlib import Path

db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # テーブル作成済みの接続を返す（冪等）
# または既存 DB に接続のみ行う場合:
conn2 = get_connection(db_path)
```

- 自動 .env 読み込みの無効化（テストなど）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定しておくと、パッケージインポート時の自動ロード処理をスキップします。

---

## ディレクトリ構成

（リポジトリルート想定）

- src/
  - kabusys/
    - __init__.py                — パッケージ初期化（バージョン情報、公開モジュール）
    - config.py                  — 環境変数 / Settings 管理（自動 .env ロード含む）
    - data/
      - __init__.py
      - schema.py                — DuckDB スキーマ定義と初期化 API（init_schema, get_connection）
    - strategy/
      - __init__.py              — 戦略関連モジュール（拡張箇所）
    - execution/
      - __init__.py              — 発注／実行関連（拡張箇所）
    - monitoring/
      - __init__.py              — 監視／通知関連（拡張箇所）
- pyproject.toml (想定)
- .git/ (想定)
- .env, .env.local (任意)

※ schema.py 内では Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル DDL が定義されています。テーブル作成は idempotent（既存ならスキップ）で、いくつかのインデックスも同時に作成されます。

---

## 実装上の注意点・補足

- schema 初期化は init_schema() を使ってください。get_connection() は既存の DB に接続するだけでスキーマ作成は行いません。
- Settings は必須の環境変数が未設定の場合に ValueError を投げます。CI / テスト環境では適切にモックまたは環境変数を注入してください。
- .env 自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。配布パッケージなどでプロジェクトルートが検出できない場合、自動ロードはスキップされます。
- 実運用（live）で使用する前に、paper_trading モードで十分な検証を行ってください。

---

必要に応じて README を拡張していきます。たとえば:
- インストール可能なパッケージ依存関係の一覧（requirements.txt / pyproject.toml から）
- 実際の戦略サンプルコード
- 発注フロー（kabu API 連携例）
- ロギング / モニタリングの設定方法

追加で追記したい内容があれば教えてください。