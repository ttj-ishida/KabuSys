# KabuSys

日本株向けの自動売買システムの骨組み（ライブラリ）。データ取得・スキーマ定義・環境設定・発注/モニタリングのためのモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な基盤機能を提供するパッケージです。  
主な責務は次の通りです。

- 環境変数/設定の読み込み・管理
- DuckDB によるデータスキーマ定義・初期化
- 戦略（strategy）、発注/実行（execution）、モニタリング（monitoring）用のモジュール群の基盤

パッケージは、アプリケーション層（戦略、実行、監視）実装の土台として利用されることを想定しています。

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須設定値を取得する便利な API（settings オブジェクト）
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - 有効な KABUSYS_ENV 値の検証（development / paper_trading / live）
- データベーススキーマ（src/kabusys/data/schema.py）
  - DuckDB を用いた 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義
  - インデックス定義、外部キーを考慮した作成順の冪等的初期化
  - init_schema(db_path) による初期化 API、get_connection(db_path) による接続取得
- パッケージ構造の骨組み（strategy / execution / monitoring パッケージ）

主要なテーブル例（抜粋）:
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles
- Feature: features, ai_scores
- Execution: signals, signal_queue, orders, trades, positions, portfolio_performance

---

## 動作環境・依存

- Python 3.10 以上（型ヒントに | 演算子を使用）
- duckdb（DuckDB Python パッケージ）
- 実際の運用では kabu API、J-Quants、Slack トークン等の外部サービス接続が必要

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# パッケージをローカルで編集しながら使う場合:
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動で読み込まれます。
   - 自動読み込みを無効にしたいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
4. 必須の環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
5. データベースの初期化（次節の使い方参照）

サンプル .env:
```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# Kabu API
KABU_API_PASSWORD="your_kabu_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"

# Slack
SLACK_BOT_TOKEN="xoxb-...."
SLACK_CHANNEL_ID="C01234567"

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス（省略時は data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意:
- `.env.local` は `.env` を上書きする用途で優先的に読み込まれます（OS 環境変数は保護されます）。
- .env のパースはシェル風の書式（export を許容、クォート・エスケープ・コメント処理あり）に対応しています。

---

## 使い方

以下はライブラリの基本的な利用例です。

1) 設定へのアクセス（settings オブジェクト）
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
```

未設定の必須変数にアクセスすると ValueError が発生します（例: JQUANTS_REFRESH_TOKEN が未設定）。

2) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path は Path を返す（デフォルト: data/kabusys.duckdb）
db_path = settings.duckdb_path

# 初回: スキーマを作成して接続を取得
conn = init_schema(db_path)

# 以降: 単に接続を取得する場合
conn2 = get_connection(db_path)

# クエリ例
with conn:
    rows = conn.execute("SELECT count(*) FROM prices_daily").fetchall()
    print(rows)
```

- init_schema は指定したファイルパスの親ディレクトリを自動作成します（メモリ DB を使う場合は ":memory:" を指定可能）。
- 既にテーブルが存在する場合はスキップされるため冪等に実行できます。

3) 自動環境読み込みを無効化する（例: テスト）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('auto load disabled')"
```

---

## ディレクトリ構成

リポジトリ内の主要なファイル/ディレクトリは次の通りです（抜粋）。

- src/kabusys/
  - __init__.py                : パッケージのメタ情報（__version__ など）
  - config.py                  : 環境変数／設定管理
  - data/
    - __init__.py
    - schema.py                : DuckDB スキーマ定義と初期化 API
  - strategy/
    - __init__.py              : 戦略関連モジュールのエントリ（拡張ポイント）
  - execution/
    - __init__.py              : 発注/実行関連モジュールのエントリ（拡張ポイント）
  - monitoring/
    - __init__.py              : モニタリング関連モジュールのエントリ（拡張ポイント）
- .env, .env.local             : （プロジェクトルートで）環境設定ファイル（自動読み込み対象）
- data/                        : データベースファイル等（デフォルトの出力先）

---

## 補足・注意点

- settings で取得する必須項目が未設定の場合は ValueError が発生します。実運用時は `.env` の管理と Secrets 管理にご注意ください。
- .env のパース実装は一般的なシェル風のルールを採っていますが、特殊ケースの扱いに注意してください。複雑な設定は OS の環境変数やシークレットマネージャを利用することを推奨します。
- DuckDB のスキーマは初期化後も安全に再実行できるように CREATE TABLE IF NOT EXISTS を用いています。カラム追加や大幅な変更を行う場合はマイグレーション方針を検討してください。

---

必要であれば以下の追加情報も作成できます:
- .env.example のテンプレート
- よく使う SQL クエリ集（スキーマ参照用）
- 戦略／実行／モニタリングのサンプル実装テンプレート

ご希望があれば教えてください。