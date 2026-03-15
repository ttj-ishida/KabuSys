# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ層）。  
このリポジトリはデータ取得／スキーマ定義、環境設定、戦略・発注・監視の基盤モジュールを提供します。

- バージョン: 0.1.0
- パッケージ: `kabusys`

## プロジェクト概要

KabuSys は日本株の自動売買に必要な基盤機能を提供する Python パッケージです。  
主に以下を目的とします。

- 市場データ／財務／ニュースなどの生データ保存（Raw Layer）
- 整形済み市場データ（Processed Layer）
- 戦略やAIが利用する特徴量（Feature Layer）
- シグナル・発注・約定・ポジション管理（Execution Layer）
- 環境変数設定の読み込み・管理（自動 .env ロード）
- DuckDB を用いた永続化・スキーマ初期化

## 主な機能一覧

- 環境設定管理（`kabusys.config.Settings`）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可能）
  - 必須環境変数の取得と検証
  - `KABUSYS_ENV`（development / paper_trading / live）やログレベル検証
- DuckDB スキーマ定義・初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution の各層テーブル定義
  - インデックス定義、外部キー依存を考慮した作成順序
  - `init_schema()` による冪等な初期化と接続取得
- パッケージ構成（戦略・発注・監視用のモジュール雛形）
  - `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`（各 __init__ は現状空）

## 必要条件

- Python 3.10 以上（型注釈に `X | Y` 構文を使用）
- duckdb Python パッケージ

インストール例：
```bash
python -m pip install --upgrade pip
python -m pip install duckdb
# 開発環境としてこのパッケージをインストールする場合（pyproject.toml がある前提）
pip install -e .
```

## セットアップ手順

1. リポジトリをクローン / チェックアウトする。

2. 必要ライブラリをインストールする（例: duckdb）。
   ```
   pip install duckdb
   ```

3. 環境変数を設定する
   - プロジェクトルート（`src/` と同階層に .git または pyproject.toml がある場所）に `.env` を作成すると、自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

   例 `.env`:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（任意、デフォルトは data/kabusys.duckdb）
   DUCKDB_PATH=data/kabusys.duckdb

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   これらが未設定の場合、`kabusys.config.Settings` の該当プロパティアクセスで `ValueError` が発生します。

## 使い方（簡単な例）

- 設定取得:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("env:", settings.env)
print("is_live:", settings.is_live)
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path の既定値は "data/kabusys.duckdb"
conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（DuckDBPyConnection）
```

- 既存 DB に接続（スキーマ初期化しない場合）:
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- 自動 .env ロードの挙動（補足）
  - プロジェクトルートを、`config.py` の位置から親方向に `.git` または `pyproject.toml` を検索して決定します（CWD に依存しない）。
  - 読み込み順序:
    1. OS 環境変数（既存）
    2. `.env`（未設定のキーのみ設定）
    3. `.env.local`（`.env.local` は既存のキーを上書きする）
  - `.env` のパースはシェル形式に近いルールをサポート（`export KEY=val`、シングル/ダブルクォート、インラインコメントなど）。詳細は `kabusys.config._parse_env_line` を参照してください。

## スキーマ（概略）

各レイヤーと主要テーブル（抜粋）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

テーブルは `kabusys.data.schema._ALL_DDL` に定義されており、`init_schema()` はこれらを冪等に作成します。インデックスも多数定義されています。

## ディレクトリ構成

リポジトリ内の主なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のプロジェクトルートには pyproject.toml やその他スクリプトが存在する想定）

## 注意事項・補足

- Python バージョンは 3.10 以上を推奨します（型注釈の構文を使用）。
- DuckDB をデータ永続化に使用します。デフォルトパスは `data/kabusys.duckdb`（`settings.duckdb_path` で変更可）。
- `Settings` は必要な環境変数が未定義の場合に例外を投げます。アプリケーション起動前に `.env` を準備するか OS 環境変数を設定してください。
- `KABUSYS_ENV` の有効値: `development`, `paper_trading`, `live`
- `LOG_LEVEL` の有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

ご不明点（例: .env の具体的なフォーマット、追加の初期化処理、戦略/発注フローの導入方法など）があれば教えてください。README をプロジェクトの運用ルールやデプロイ手順に合わせてさらに拡張できます。