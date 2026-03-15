# KabuSys

KabuSys は日本株向けの自動売買基盤の骨組み（ライブラリ）です。  
環境変数による設定管理、DuckDB を用いた多層データスキーマの初期化機能、戦略/実行/監視モジュールのエントリポイントを提供します。

バージョン: 0.1.0

---

## 概要

このパッケージは以下のような機能を想定した基盤コードを含みます。

- 環境変数と .env ファイルの自動読み込み・管理（kabusys.config）
- アプリケーション設定（Settings）による型付きアクセス
- DuckDB を使ったデータスキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層テーブルを定義
- strategy / execution / monitoring のモジュールの雛形（各 __init__.py）

これにより、データ取得 → 前処理 → 特徴量作成 → シグナル生成 → 発注／約定管理 → パフォーマンス計測 の一連のワークフローを実装する土台を提供します。

---

## 主な機能

- .env / .env.local の自動パースと環境変数設定
  - コメント、export 形式、クォート文字、エスケープ対応
  - OS 環境変数を保護する仕組み（.env.local は上書き）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
- Settings クラス（kabusys.config.settings）により、必要な設定値へ安全にアクセス
  - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など
- DuckDB 用の包括的なスキーマ初期化関数 `init_schema(db_path)`
  - Raw / Processed / Feature / Execution レイヤーのテーブル群を作成
  - インデックス作成や parent ディレクトリ自動作成を行う
  - 冪等（既存テーブルはスキップ）
- get_connection(db_path) による既存 DB への接続取得

---

## 要件

- Python 3.10 以上
  - （型注釈で PEP 604 の '|' 型結合などを利用しているため）
- duckdb Python パッケージ
- （実際の運用では Slack、kabu API、J-Quants などの API クライアントライブラリや依存が必要になることが想定されますが、本リポジトリのコードには明示的な外部依存定義は含まれていません）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# またはパッケージとして配布されている場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb
   # 他に必要なパッケージがあれば追加でインストールしてください
   ```

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` と任意で `.env.local` を置くと自動で読み込まれます
   - 自動読み込みを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. `.env` に最低限必要なキー（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   - `.env.example` を用意して運用すると安全です（リポジトリに含める場合は機密情報を含めないこと）。

---

## 使い方（例）

- Settings を使って環境変数にアクセスする:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定だと例外(ValueError)
print(settings.kabu_api_base_url)      # デフォルト http://localhost:18080/kabusapi
print(settings.duckdb_path)            # Path オブジェクト
```

- DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す
conn = init_schema(settings.duckdb_path)

# 簡単なクエリの例
with conn:
    for row in conn.execute("SELECT name FROM sqlite_master LIMIT 10").fetchall():
        print(row)
```
（上記の sqlite_master は DuckDB ではなく例です。実際にはテーブル一覧は system tables または PRAGMA 等で確認してください。DuckDB では `SHOW TABLES` などが使用できます。）

- 自動環境読み込みの挙動
  - パッケージ import 時点でプロジェクトルートを探索し `.env` / `.env.local` を読み込みます。
  - OS 環境変数は保護され、`.env` は既存の OS 環境変数を上書きしません。
  - `.env.local` は `.env` の値を上書きします（ただし OS 環境変数は保護されます）。

---

## ディレクトリ構成

以下は主要ファイルの構成（src layout）です:

- src/
  - kabusys/
    - __init__.py                # パッケージメタ情報（__version__）
    - config.py                  # 環境変数読み込み・Settings 定義
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義と init_schema, get_connection
    - strategy/
      - __init__.py              # 戦略モジュールのエントリポイント（拡張箇所）
    - execution/
      - __init__.py              # 発注・実行ロジックのエントリポイント（拡張箇所）
    - monitoring/
      - __init__.py              # 監視・ログ・メトリクスのエントリポイント（拡張箇所）

- .gitignore
- pyproject.toml or setup.cfg    # （プロジェクトによっては存在）
- .env, .env.local               # （環境ごとに設定）

---

## 開発時の注意点 / 補足

- Python バージョンは 3.10 以上を推奨します。
- 実運用では各 API クライアント（kabuステーション、J-Quants、Slack 等）の実装と、それらの認証トークン保護に注意してください。
- DuckDB のファイルパスは Settings.duckdb_path で管理され、パスの親ディレクトリが無ければ自動作成されます。
- schema の DDL はテーブルの制約（型・CHECK・外部キー）やインデックスを含みます。既存テーブルへの変更は現状サポートしていないため、スキーマ変更時はマイグレーションを検討してください。

---

必要があれば README にサンプルワークフロー（データ取り込み → 特徴量生成 → シグナル生成 → 注文送信）や、CI/テスト手順、推奨依存関係一覧を追加します。どの情報を追加したいか教えてください。