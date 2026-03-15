# KabuSys

日本株向けの自動売買システム基盤ライブラリです。データ管理（DuckDB スキーマ定義）、環境設定読み込み、戦略・発注・モニタリング用のモジュール群の骨組みを提供します。

主な目的は、データ取得 → 前処理 → 特徴量生成 → シグナル生成 → 発注／約定／ポジション管理、というワークフローを支える共通基盤を用意することです。

---

## 主な機能

- 環境変数／.env 管理
  - プロジェクトルートの `.env` と `.env.local` を自動読み込み（OS 環境変数は保護）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須変数に未設定がある場合にエラーを返す `Settings` インターフェース。
  - 利用可能なプロパティ例: J-Quants トークン、kabu API パスワード、Slack トークン、DB パス、環境（development/paper_trading/live）、ログレベル など。

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution の 4 層でテーブル定義済み。
  - 各種テーブル（prices_daily, features, signals, signal_queue, orders, trades, positions, portfolio_performance など）とインデックスを作成する `init_schema()` を提供。
  - `:memory:` を使ったインメモリ DB の初期化も可能。
  - 初回起動時に DB ファイルの親ディレクトリを自動作成。

- パッケージ分割（拡張性）
  - strategy, execution, monitoring モジュールの雛形を用意。個別戦略や発注ロジック、運用監視を実装しやすい構成。

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | Y` 表記を使用しています）
- DuckDB を利用するため `duckdb` パッケージが必要

例: 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# パッケージをプロジェクトに組み込む場合（setup.py/pyproject.toml がある前提）
pip install -e .
```

環境変数設定
- プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を作成してください。`.env.local` はローカル上書き用です（`.env.local` は優先して読み込まれます）。
- 重要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabuAPI のベース URL（省略時は http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（省略時は data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（省略時は data/monitoring.db）
  - KABUSYS_ENV: development | paper_trading | live（省略時は development）
  - LOG_LEVEL: DEBUG/INFO/...（省略時は INFO）

サンプル `.env`
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロード無効化（テスト時など）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（簡単なコード例）

Settings を使って設定取得
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_paper)     # 環境判定ヘルパー
```

DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイル DB を初期化
conn = init_schema(settings.duckdb_path)

# またはインメモリ DB を初期化
mem_conn = init_schema(":memory:")
```

既存 DB へ接続（スキーマの初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

シンプルなワークフロー例（擬似）
1. データ取得モジュールで raw_* テーブルを埋める
2. 前処理で prices_daily / fundamentals を作成
3. features / ai_scores を作成して features テーブルに保存
4. strategy が features を参照して signals を生成
5. signal_queue に流し、execution が orders/trades を登録
6. positions / portfolio_performance を更新、monitoring で Slack へ通知

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）:
```
src/
└─ kabusys/
   ├─ __init__.py            # パッケージ初期化（バージョン等）
   ├─ config.py              # 環境変数・設定管理（Settings）
   ├─ data/
   │  ├─ __init__.py
   │  └─ schema.py           # DuckDB スキーマ定義・初期化 API (init_schema, get_connection)
   ├─ strategy/
   │  └─ __init__.py         # 戦略ロジック（各戦略を追加する場所）
   ├─ execution/
   │  └─ __init__.py         # 発注・約定処理（kabu API 絡みの実装場所）
   └─ monitoring/
      └─ __init__.py         # 監視・通知ロジック（Slack 通知など）
```

各主要ファイルの役割
- src/kabusys/config.py
  - プロジェクトルートを検出して .env/.env.local を自動読み込み
  - 必須環境変数を検査する Settings クラスを公開（settings インスタンス）
- src/kabusys/data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）
  - テーブルと指数を作成する init_schema()
  - 既存 DB に接続する get_connection()

---

## 注意事項 / 実装上のポイント

- プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行います。配布後や特殊な配置では検出できない場合があるため、その場合は自動ロードがスキップされます。
- .env の自動読み込み時、既に OS 環境変数に存在するキーは `.env` によって上書きされません（`.env.local` は override=True なのでローカルのみで上書きしますが、OS 環境変数は保護されます）。
- init_schema() は冪等（同じ DDL を複数回実行しても安全）です。
- API キーやパスワードなどの秘密情報は `.env.local` に置いて git 管理から除外することを推奨します。
- 実際の取引（live 環境）に移す前に paper_trading で十分なテストを行ってください。

---

必要に応じて、strategy / execution / monitoring のサンプル実装や CI 用のセットアップ手順（テスト DB の初期化など）も追加できます。どの箇所を優先して詳述したいか教えてください。