# KabuSys

日本株向けの自動売買基盤（骨組み）で、データ管理・特徴量生成・戦略・発注監査ログなどの基盤機能を提供します。  
このリポジトリはライブラリとして利用する想定で、DuckDB によるデータスキーマ、環境変数管理、監査ログの初期化 API などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を想定したバックエンド基盤です。

- 市場データ・財務データ・ニュース・約定データなどの Raw / Processed / Feature / Execution の多層データスキーマ（DuckDB）
- 戦略層・発注層の監査ログ（トレーサビリティ）を保持する監査スキーマ（DuckDB）
- 環境変数（.env/.env.local/OS）からの設定読み込みユーティリティ（自動読み込み機能あり）
- 設定の取得インターフェース（settings）と便利な初期化 API

本リポジトリ自体は戦略や注文実行ロジックの実装を含むスケルトンであり、実際のアルゴリズムやブローカー接続はユーザー実装を想定しています。

---

## 主な機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` と `.env.local` を自動読み込み（OS 環境変数優先）
  - 読み込み無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 必須設定をチェックする `settings` オブジェクト

- データスキーマ（DuckDB）
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 普通に使うクエリを想定したインデックス定義
  - スキーマ初期化用 API: init_schema(), get_connection()

- 監査ログ（トレーサビリティ）
  - signal_events（戦略が出したシグナルの記録）
  - order_requests（発注要求 / 冪等キー）
  - executions（証券会社の約定情報）
  - すべての TIMESTAMP は UTC 保存（init_audit_schema は TimeZone を UTC に設定）
  - 初期化 API: init_audit_schema(), init_audit_db()

- パッケージ構成（戦略 / 実行 / モニタリング用のパッケージスケルトン）

---

## 動作環境 / 要件

- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- 必要パッケージ（例）
  - duckdb

インストールはプロジェクトの setup/pyproject に依存しますが、開発時は次の手順が一般的です。

例（仮想環境を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# パッケージを開発モードでインストールする（pyproject または setup がある前提）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を準備して依存をインストールします（上記参照）。

2. 環境変数を設定する
   - プロジェクトルートに `.env` を作成してください（例は下記）。
   - 自動読み込みは OS 環境変数 > .env.local > .env の順で適用されます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

`.env` の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等で使用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

3. データベース（DuckDB）を初期化する（下記「使い方」を参照）。

---

## 使い方（簡単な例）

- settings（環境変数の取得）
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("env:", settings.env)
if settings.is_live:
    print("LIVE mode")
```

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema, get_connection

# ファイル DB を作成・初期化して接続を取得
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続（スキーマ初期化は行わない）
conn2 = get_connection("data/kabusys.duckdb")
```

- 監査ログスキーマの初期化（既存の DuckDB 接続に追記する場合）
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema() の戻り値など
init_audit_schema(conn)
```

- 監査専用 DB を別ファイルで作る
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- SQL 実行例
```python
with conn:
    # 例: prices_daily の行数を数える
    res = conn.execute("SELECT count(*) FROM prices_daily").fetchone()
    print(res)
```

---

## 自動 .env 読み込みルール

- 自動的にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込みます。
- 読み込み優先順位:
  1. OS 環境変数（最優先）
  2. .env.local（存在すれば上書き）
  3. .env（存在すればセット。ただし既に OS に存在するキーは上書きしない）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テストなどで利用）。

.env のパースはシェルライクな簡易パーサを使い、シングル／ダブルクォートやエスケープ、行コメントなどの基本的なケースをサポートしています。

---

## ディレクトリ構成

プロジェクトの主要ファイル/ディレクトリ構成（抜粋）:
```
src/
  kabusys/
    __init__.py         # パッケージ情報（__version__ 等）
    config.py           # 環境変数 / Settings 管理
    data/
      __init__.py
      schema.py         # DuckDB スキーマ定義・初期化（init_schema, get_connection）
      audit.py          # 監査ログ（signal_events/order_requests/executions）の定義・初期化
      audit.py
      audit.py
    strategy/
      __init__.py       # 戦略モジュール（拡張ポイント）
    execution/
      __init__.py       # 発注実行モジュール（拡張ポイント）
    monitoring/
      __init__.py       # モニタリング / メトリクス（拡張ポイント）
```

主要モジュールの役割:
- kabusys.config: アプリ設定と .env 読み込みロジック
- kabusys.data.schema: プロダクションで使う DuckDB テーブル群の DDL と初期化 API
- kabusys.data.audit: 監査用の DDL と初期化 API（トレーサビリティ）
- kabusys.strategy / kabusys.execution / kabusys.monitoring: 将来の戦略ロジック・発注・監視ロジックのためのプレースホルダ

---

## 開発メモ / 注意点

- DuckDB ファイルパスはデフォルトで `data/kabusys.duckdb`（settings.duckdb_path）です。初期化時に親ディレクトリが存在しない場合は自動作成されます。
- 監査ログテーブルは削除しない前提（ON DELETE RESTRICT など）で設計されています。監査ログの運用・バックアップ方針を検討してください。
- 監査ログの TIMESTAMP は UTC に固定して保存されます（init_audit_schema が `SET TimeZone='UTC'` を実行）。
- env 値のチェックを厳格に行います（例: KABUSYS_ENV は development/paper_trading/live のいずれか、LOG_LEVEL は標準ログレベル）。

---

## 追加情報 / 今後の拡張

- strategy、execution、monitoring パッケージを拡張して具体的な戦略、取引ブローカー連携、アラート・監視ダッシュボードを実装してください。
- 堅牢な発注処理（再送、冪等性、部分約定処理）や、外部ブローカーのコールバック受信処理はこの基盤を起点に実装できます。
- データ取得（マーケットデータ / 財務 / ニュース）コンポーネントを追加し、raw_* テーブルへ定期投入するフローを設計してください。

---

必要があれば README に含める具体的なコマンド例、.env.example のテンプレート、またはサンプルスクリプト（戦略の骨組み）を追加で作成します。どの情報を優先して追加しますか？