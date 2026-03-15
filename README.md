# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システム基盤ライブラリです。市場データの収集・永続化、特徴量生成、注文・約定のトレーサビリティ（監査ログ）など、アルゴリズム売買に必要な共通機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- DuckDB を用いたデータレイク（raw / processed / feature / execution レイヤ）を定義・初期化する。
- 戦略 → 発注 → 約定 に至る監査ログ（監査テーブル）を別途管理し、UUID 連鎖でフローを完全にトレース可能にする。
- 環境変数 / .env 管理、アプリケーション設定を提供する（自動 .env ロード機能を含む）。
- kabuステーションや J-Quants、Slack 等との連携に必要な設定項目を収集するための設定ラッパを提供する。

設計上、DB スキーマは冪等（既存テーブルがあればスキップ）かつ外部キー・インデックスなどを考慮した構成になっています。

---

## 主な機能一覧

- 環境変数 / .env ファイルの自動ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に .env, .env.local を読み込み
  - export プレフィックス、クォート、エスケープ、インラインコメントなどに対応したパーサを実装
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 設定（Settings）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - データベースパス: DUCKDB_PATH, SQLITE_PATH
  - 実行環境: KABUSYS_ENV (development / paper_trading / live)
  - ログレベル: LOG_LEVEL（DEBUG/INFO/...）

- DuckDB ベースのデータスキーマ初期化
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - パフォーマンスを考慮したインデックスを自動作成

- 監査（Audit）
  - signal_events, order_requests, executions の監査テーブルを別モジュールで初期化
  - 監査ログは削除しない方針、TIMESTAMP は UTC 保存、冪等キー（order_request_id / broker_execution_id 等）

---

## 前提条件

- Python >= 3.10（型注釈に | 演算子を使用しているため）
- duckdb パッケージ（DuckDB Python バインディング）

必要に応じて他の依存（kabu API クライアント、J-Quants クライアント、slack_sdk 等）を追加してください。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（任意だが推奨）
   - Unix / macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 最低限 DuckDB が必要です:
     ```bash
     pip install duckdb
     ```
   - 開発中はローカル editable インストール:
     ```bash
     pip install -e .
     ```

4. 環境変数 (.env) の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と/または `.env.local` を置くと自動でロードされます（デフォルトで自動ロードが有効）。
   - 自動ロードを無効にするには:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須となる主要キー（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - データベースパスは任意指定:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN="xxx"
   KABU_API_PASSWORD="secret"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

- 設定の読み取り

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # JQUANTS_REFRESH_TOKEN が未設定だと ValueError が発生
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_live)                # KABUSYS_ENV == "live" の判定
```

- データベーススキーマの初期化（DuckDB）

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path に基づいて DB ファイル（または :memory:）を作成し、全テーブルを作成
conn = init_schema(settings.duckdb_path)

# 必要に応じて既存接続を取得する場合
from kabusys.data.schema import get_connection
conn2 = get_connection(settings.duckdb_path)
```

- 監査テーブルの初期化

方法 A: 既存の接続に監査テーブルを追加する
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema の返り値など
```

方法 B: 監査専用 DB を初期化して接続を得る
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 自動 .env 読み込みの挙動
  - パッケージ import 時にプロジェクトルートを探し、.env → .env.local の順で読み込みます（.env.local は上書き）。
  - OS 環境変数は保護され、.env がそれらを上書きすることは通常ありません。
  - テストなどで自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。

---

## よく使う API（まとめ）

- kabusys.config
  - settings: アプリケーション設定アクセス用インスタンス
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.kabu_api_base_url
    - settings.slack_bot_token
    - settings.slack_channel_id
    - settings.duckdb_path, settings.sqlite_path
    - settings.env / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（全テーブルを作成）
  - get_connection(db_path) -> 既存 DB への接続

- kabusys.data.audit
  - init_audit_schema(conn) -> 既存接続に監査テーブルを追加
  - init_audit_db(db_path) -> 監査専用 DB を作成して接続を返す

---

## ディレクトリ構成

リポジトリ内の主要なファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理（自動 .env ロード）
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ（raw / processed / feature / execution）
      - audit.py               # 監査ログ（signal_events / order_requests / executions）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py            # 戦略関連のパッケージ（拡張想定）
    - execution/
      - __init__.py            # 発注 / ブローカ連携のためのパッケージ（拡張想定）
    - monitoring/
      - __init__.py            # 監視・メトリクス関連（拡張想定）

（注）上記は現在のコードベースに存在するモジュールの概略です。strategy / execution / monitoring は現状で初期化用 __init__.py のみが含まれ、個別実装は拡張を想定しています。

---

## 開発メモ・注意点

- Python バージョンは 3.10 以降を想定しています（型注釈に | を使用）。
- .env パースは POSIX ライクな形式をサポートします（export プレフィックス、クォート／エスケープ、コメント対応）。
- DB の初期化は冪等（既存テーブルがある場合はスキップ）です。運用ではマイグレーション方針を別途検討してください。
- 監査ログは削除しない運用を前提に設計されています（FK は ON DELETE RESTRICT 等を利用）。
- 時刻は監査テーブルで UTC 保存を明示しています（init_audit_schema は TimeZone='UTC' を設定）。

---

必要であれば README に実際の .env.example の雛形、より詳しい初期化スクリプト例、CI やローカルでのテスト手順、追加依存の一覧（slack_sdk 等）を追記します。どの情報を補足したいか教えてください。