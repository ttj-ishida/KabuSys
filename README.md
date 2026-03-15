# KabuSys

日本株自動売買システムの基盤ライブラリ。市場データ取得・整形、特徴量生成、シグナル生成、発注管理、モニタリングなどを想定したモジュール群と、DuckDBスキーマ定義・初期化機能、環境変数設定管理を提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（優先度: OS 環境 > .env.local > .env）
  - 必須設定の取得とバリデーション（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution レイヤーに渡るテーブル群をDDLとして定義
  - インデックス定義、外部キー依存を考慮したテーブル作成順
  - init_schema() によりファイル or インメモリ DB を初期化
- パッケージ構造（戦略、実行、モニタリング等の拡張ポイントを想定）
  - モジュール: data, strategy, execution, monitoring（各モジュールの拡張に対応）

---

## 動作環境 / 依存

- Python 3.10 以上（型注釈の union 演算子 `|` を利用）
- duckdb（DuckDB Python バインディング）
- （将来的に）kabu API クライアント、J-Quants クライアント、Slack クライアント等

最低限のセットアップ例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

プロジェクト配布時は requirements.txt / pyproject.toml を追加して依存管理してください。

---

## 環境変数（例）

以下の環境変数を設定する必要があります（必須は .env.example を参照のこと）。プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます。

必須（コード中で _require により参照される例）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (valid: development, paper_trading, live; デフォルト: development)
- LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト: INFO)

サンプル .env:
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 env ロードを無効化する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb
   ```
   （他に必要なクライアントがあれば requirements.txt を追加して pip install -r でインストールしてください）
4. プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な環境変数を設定
5. DuckDB スキーマを初期化（下記「使い方」を参照）

---

## 使い方

主に設定取得とデータベース初期化の方法を紹介します。

- 設定（Settings）の利用例
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path がファイルパス（Path）を返すためそのまま渡せます
conn = init_schema(settings.duckdb_path)

# 接続オブジェクト conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
# conn.execute(...) で SQL を実行できます
```

- 既存 DB に接続（スキーマ初期化を行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みについて
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し、`.env` と `.env.local` を順に読み込んで環境変数を設定します。
  - OS 環境変数は保護され、`.env` は既存環境変数を上書きしません（`.env.local` は上書きします）。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py              (パッケージ初期化、version)
    - config.py                (環境変数・設定管理)
    - data/
      - __init__.py
      - schema.py              (DuckDB スキーマ定義と初期化: init_schema, get_connection)
    - strategy/
      - __init__.py            (戦略モジュールの配置場所)
    - execution/
      - __init__.py            (発注 / 実行関連モジュールの配置場所)
    - monitoring/
      - __init__.py            (モニタリング関連モジュールの配置場所)

DuckDB のテーブルは以下のレイヤーで定義されています（主なテーブル）:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

---

## 進め方のヒント / 拡張

- strategy/、execution/、monitoring/ 以下に機能を実装していく設計になっています。各モジュールは settings と DuckDB 接続を利用してデータ取得→特徴量→シグナル→発注→状態管理と連携してください。
- schema.py のテーブル定義は冪等で実行できます。スキーマ変更を行う場合はマイグレーション計画（既存データのバックアップや ALTER 文）を検討してください。
- テスト環境では init_schema(":memory:") を使うとインメモリ DB で素早くユニットテストが書けます。
- セキュリティ: API トークンやパスワードは `.env` ファイルをリポジトリに含めないでください。CI / 本番では環境変数やシークレット管理サービスを利用してください。

---

何か追加したい機能（例: サンプル戦略、発注シミュレータ、マイグレーションスクリプト等）があれば教えてください。README をその用途に合わせて拡張します。