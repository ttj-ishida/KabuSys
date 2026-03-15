# KabuSys

日本株向け自動売買システムのコアライブラリ（プロトタイプ）。  
データ取得・スキーマ管理、戦略・実行・モニタリングの基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤モジュール群です。  
主に以下の責務を持ちます。

- データレイク（DuckDB）向けのスキーマ定義と初期化
- 環境変数 / 設定の集中管理（.env の自動ロードを含む）
- 戦略、発注、モニタリングのためのパッケージ構成（拡張ポイント）

注: 本リポジトリはライブラリ/コア層であり、実際のデータ取り込みや注文送信ロジックは個別に実装して利用します。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - クォート／エスケープ／コメント対応の .env パーサ
  - 必須環境変数チェック（未設定時に例外を投げる helper）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の4層スキーマをDDLで定義
  - インデックス定義、外部キー依存を考慮した作成順
  - init_schema(db_path) による冪等な初期化と接続取得
  - get_connection(db_path) による接続取得（初期化は行わない）

- パッケージ構成（拡張用）
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

---

## 必要条件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb

（実運用で J-Quants / kabuステーション / Slack 連携を行う場合は、それらのクレデンシャル／依存も必要です）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb
   - pip install -e .  （開発インストール。setup がある場合）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` や `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（kabusys.config.Settings が参照）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルトあり:
- KABUS_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)

例: .env（参考）
```env
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabuステーション API
KABU_API_PASSWORD="your_kabu_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"

# Slack
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"

# DB
DUCKDB_PATH="data/kabusys.duckdb"

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースは以下に対応しています：
- export KEY=val 形式
- シングル／ダブルクォート内でのエスケープ（バックスラッシュ）
- クォートなしの値では、直前の文字が空白またはタブである `#` をコメントとみなす

---

## 使い方

基本的な利用例を示します。

- 設定値の読み取り
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print(settings.env, settings.is_live, settings.log_level)
```

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema, get_connection

# ファイルベース DB を初期化して接続を得る
conn = init_schema("data/kabusys.duckdb")

# インメモリ DB を使用したい場合
mem_conn = init_schema(":memory:")

# 既存 DB へ接続（スキーマ初期化はしない）
conn2 = get_connection("data/kabusys.duckdb")
```

- パッケージ情報
```python
import kabusys
print(kabusys.__version__)
# サブモジュール: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring
```

注意:
- init_schema は必要なディレクトリが無ければ自動作成します（ファイルベース時）。
- 実際の発注処理（kabuステーションへの送信）やデータ取得は別モジュールで実装／接続してください。

---

## ディレクトリ構成

プロジェクトルート（抜粋）:

```
.
├─ pyproject.toml / setup.cfg / setup.py (任意)
├─ .git/ (プロジェクトルート検出に使用)
├─ .env
├─ .env.local
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ定義 (version, __all__)
│     ├─ config.py              # 環境変数・設定管理
│     ├─ data/
│     │  ├─ __init__.py
│     │  └─ schema.py           # DuckDB DDL と初期化 API (init_schema, get_connection)
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

主要ファイル:
- src/kabusys/config.py: 環境変数の自動読み込み・バリデーション機能
- src/kabusys/data/schema.py: DuckDB の全テーブル定義（Raw/Processed/Feature/Execution）と初期化関数

---

## 運用上の注意

- KABUSYS_ENV により動作モードを切り替えられます（development / paper_trading / live）。live モードでは実取引に注意してください。
- 実取引を行う場合は `KABU_API_PASSWORD` などの認証情報を適切に管理してください（公開リポジトリに置かない等）。
- .env の自動ロードはプロジェクトルートを .git / pyproject.toml で検出します。CI やテストで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば、README に以下も追加できます:
- CI / テスト手順
- 各テーブルの詳細説明（DataSchema.md 相当の抜粋）
- データ取り込み・戦略・実装例

追加したい内容があれば教えてください。