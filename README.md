# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買に向けた基盤ライブラリです。市場データの保管・前処理、特徴量生成、戦略・発注・モニタリングのためのスキーマや設定管理を提供します（現在はスキーマ定義と設定周りが実装済み）。

概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を以下にまとめます。

## プロジェクト概要
- 日本株の自動売買プラットフォーム用の共通ライブラリ群（データレイヤ、実行レイヤ、戦略、監視）。
- DuckDB を用いたローカルデータベーススキーマ（Raw / Processed / Feature / Execution 層）を提供。
- 環境変数/`.env` による設定管理を提供（自動ロード機能あり）。
- Slack、kabuステーション API、J-Quants と連携するための設定項目を想定。

## 主な機能
- DuckDB 用の包括的なスキーマ定義と初期化（init_schema）
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤ
  - prices_daily, market_calendar, fundamentals, news_articles などの Processed レイヤ
  - features, ai_scores などの Feature レイヤ
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤ
- インデックス定義（パフォーマンスを考慮した頻出クエリ向け）
- 環境変数管理（.env/.env.local 自動ロード、明示的取得用 API）
- settings オブジェクトでアプリケーション設定へ簡単アクセス

## 要件
- Python 3.9+（型ヒントや標準ライブラリ Path を使用）
- duckdb（DB 操作用）

インストール例:
- pip を使用する場合:
  - pip install duckdb
  - 開発中はプロジェクトルートで `pip install -e .`（pyproject.toml / setup がある想定）
- もしくは仮想環境を作って上記をインストールしてください。

## セットアップ手順

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb

   （プロジェクトをパッケージとして扱う場合）
   - pip install -e .

3. 環境変数の準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置きます。
   - 既存 OS 環境変数を保護しつつ、`.env` を自動で読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. データベース初期化
   - DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）に対してスキーマを作成します（以下の使い方参照）。

## 設定（.env の例）
必要な環境変数と推奨項目の例:

.env.example（例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス（オプション）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

.env のパース仕様（主なポイント）
- 空行・# で始まる行は無視されます。
- export KEY=val 形式をサポートします。
- クォートされた値はエスケープ処理を考慮して復元します。
- クォートなしの値は、`#` の前が空白またはタブの場合にコメントとして扱います。

読み込み優先順位:
- OS 環境変数 > .env.local > .env
（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていると自動読み込みは無効になります）

## 使い方（簡単なコード例）

- settings の利用例
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 未設定だと ValueError
print(settings.kabu_api_base_url)     # デフォルト値あり
print(settings.duckdb_path)           # Path オブジェクト
print(settings.is_live)               # 実行環境フラグ
```

- DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)

# DuckDB 接続 (例: pandas や SQL 実行)
df = conn.execute("SELECT count(*) FROM prices_daily").fetchdf()
```

- 既存 DB へ接続のみを取得する
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

注意:
- get_connection() はスキーマ初期化を行いません。初回は init_schema() を使ってください。

## ディレクトリ構成
（ソースに基づく抜粋）
```
src/
  kabusys/
    __init__.py        # パッケージ定義（__version__ = "0.1.0"）
    config.py          # 環境変数・設定管理
    data/
      __init__.py
      schema.py        # DuckDB スキーマ定義と初期化ロジック
    strategy/
      __init__.py      # 戦略用モジュール（未実装のプレースホルダ）
    execution/
      __init__.py      # 発注/実行関連（未実装のプレースホルダ）
    monitoring/
      __init__.py      # モニタリング関連（未実装のプレースホルダ）
```

## 注意事項 / 補足
- 環境変数の必須項目（呼び出すと ValueError を出すもの）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- duckdb のインストールが必要です。バイナリ依存に注意してください。
- .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索して決定）を基準に行います。ルートが見つからない場合は自動読み込みをスキップします。
- このリポジトリは現在スキーマと設定管理が中心で、戦略実装や実行エンジンは今後拡張する想定です。

---

ご不明点や README に追記したい内容（API ドキュメント、運用手順、CI/CD 手順など）があれば教えてください。必要に応じてサンプル戦略や実行フローの例も追加します。