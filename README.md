# KabuSys

日本株向けの自動売買基盤（ライブラリ）です。  
このリポジトリはデータ管理（DuckDB スキーマ定義）、環境設定の読み込み、戦略／発注／モニタリングを実装するための土台を提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は次の目的を想定した軽量な自動売買フレームワークの基盤です。

- 外部 API（J-Quants、kabuステーション、Slack など）の認証情報や設定を環境変数から管理
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- 戦略、発注、モニタリング用のモジュール構成（雛形）

このリポジトリはライブラリ形式で配布されることを想定しており、内部で .env ファイルの自動読み込み機能を備えています。

---

## 機能一覧

- 環境変数・設定読み込み
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - export KEY=val 形式、クォート付き値、コメントのパースに対応
  - 自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
  - 必須環境変数の取得（未設定時にエラー）
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤに対応するテーブル群を作成
  - インデックス作成（パフォーマンス向け）
  - init_schema(db_path) で冪等にスキーマ初期化可能
  - get_connection(db_path) で既存 DB に接続
- パッケージ構成
  - kabusys.data: データ処理・スキーマ
  - kabusys.strategy: 戦略（雛形）
  - kabusys.execution: 発注ロジック（雛形）
  - kabusys.monitoring: モニタリング（雛形）

---

## 要件

- Python 3.9+
- duckdb
- （必要に応じて）kabuステーション API クライアント、J-Quants API ライブラリ、Slack SDK などを追加でインストールしてください。

例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# 他の依存は用途に応じて追加
```

パッケージを編集/開発しながら使う場合:
```bash
pip install -e .
```

（pyproject.toml がある想定での手順です。実際の依存はプロジェクトに合わせて設定してください）

---

## セットアップ手順

1. 仮想環境を作成して有効化
2. 必要なパッケージをインストール（上記参照）
3. プロジェクトルートに `.env`（および必要なら`.env.local`）を作成
4. DuckDB スキーマを初期化

例: `.env`（最低限必要なキー）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

環境変数の自動読み込みは以下の優先度で行われます:
- OS 環境変数
- .env.local （存在する場合、.env の値を上書き）
- .env

自動ロードを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（簡単な例）

設定値にアクセスする:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
```

DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイル DB を初期化（必要に応じてパスを上書き）
conn = init_schema(settings.duckdb_path)
# 或いはインメモリ DB
# conn = init_schema(":memory:")
```

既存 DB へ接続する（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

環境設定の読み込み挙動・パースルールのポイント:
- export KEY=val 形式に対応
- シングル／ダブルクォートされた値はエスケープを考慮してパース
- クォート無しの値では、`#` の直前が空白/タブの場合をコメントとして扱う

---

## DuckDB スキーマ（テーブル概観）

スキーマは以下のレイヤに分かれています。

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

各テーブルは主キー・制約を含む定義になっており、一般的なクエリに備えてインデックスも作成されます。

---

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリは次の通りです（抜粋）:

- src/
  - kabusys/
    - __init__.py              # バージョン情報など
    - config.py                # 環境変数読み込み・Settings クラス
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py            # 戦略実装用のモジュール（雛形）
    - execution/
      - __init__.py            # 発注実装用のモジュール（雛形）
    - monitoring/
      - __init__.py            # モニタリング実装用のモジュール（雛形）

プロジェクトルート（.git / pyproject.toml の有無）を基に .env 自動読み込みを行います。

---

## 開発メモ / ヒント

- 必須の環境変数が設定されていない場合、settings のプロパティアクセスで ValueError が発生します。CI やテストでは意図的に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑制してください。
- DuckDB の初回初期化は init_schema() を使って行ってください。既存 DB に対しては get_connection() を使用します。
- 戦略、発注、モニタリングの実装は各サブモジュール（kabusys.strategy, kabusys.execution, kabusys.monitoring）に追加してください。

---

必要であれば README に以下を追加できます:
- 具体的な戦略テンプレート
- 発注フロー（kabuステーション連携例）
- Slack 通知の実装例
- テストの仕組みや CI 設定

要望があれば追記します。