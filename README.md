# KabuSys

日本株向け自動売買システム基盤（KabuSys）。データレイヤ（取得済み生データ / 整形済み市場データ / 特徴量 / 発注・約定管理）と監査ログ（シグナル→発注→約定のトレーサビリティ）を中心にしたライブラリ群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム構築のための基盤ライブラリです。主に以下を提供します。

- 環境変数・設定の読み取り（.env 自動ロード、必須チェック）
- データ保存用 DuckDB スキーマ（原データ層・整形層・特徴量層・実行層）の定義と初期化
- 監査ログ（Signal → Order Request → Execution）の独立した初期化ユーティリティ
- 戦略・発注・監視用のパッケージ骨格（strategy, execution, monitoring）

設計上の特徴として、データスキーマは冪等に初期化され、外部キーやインデックスを想定した順序で作成されます。監査ログは発注系のトレーサビリティを重視し、すべてのイベントを削除しない前提で設計されています。

---

## 主な機能一覧

- 環境設定管理
  - プロジェクトルート（.git / pyproject.toml を基準）から .env / .env.local を自動読み込み（環境変数優先）
  - export 付き行、シングル／ダブルクォートとエスケープ、インラインコメントの取り扱いをサポート
  - 必須環境変数の存在チェック（未設定時に明確なエラーを投げる）

- データスキーマ（DuckDB）
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種インデックスの作成

- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブル
  - 冪等キー（order_request_id / broker_execution_id 等）やステータス遷移管理
  - UTC タイムゾーン保存保証（初期化時に SET TimeZone='UTC'）

- ユーティリティ
  - DuckDB の初期化関数（init_schema / get_connection）
  - 監査ログ初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | を使用しているため）
- duckdb パッケージが必要

推奨手順（例）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係をインストール（最低限）
   ```
   pip install duckdb
   ```

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings より）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルト値:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (デフォルト: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (デフォルト: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

備考: .env のパースは以下の点をサポートします
- `export KEY=val` 形式
- シングル／ダブルクォートとバックスラッシュでのエスケープ
- クォートなしの場合、`#` の直前が空白またはタブならコメントとみなす

---

## 使い方（簡単な例）

1) 設定を取得する
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("ENV:", settings.env)
```

2) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイル DB を初期化して接続を取得
conn = init_schema(settings.duckdb_path)

# またはインメモリ DB
mem_conn = init_schema(":memory:")
```

- init_schema はテーブルやインデックスをすべて作成し、duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）を返します。
- 既に存在するテーブルはスキップされるため冪等です。
- ファイルパスの親ディレクトリがなければ自動作成します。

3) 監査ログ（Audit）を追加で初期化する
```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存の conn に監査テーブルを追加
init_audit_schema(conn)

# または別 DB として初期化して接続を取得
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

4) get_connection を使って既存 DB に接続
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py            — パッケージ定義（__version__ = "0.1.0"）
  - config.py              — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py            — DuckDB スキーマ定義・初期化 (init_schema, get_connection)
    - audit.py             — 監査ログスキーマ（signal_events / order_requests / executions）
    - audit.py の補足: init_audit_schema, init_audit_db を提供
    - other modules...      — (将来的にデータ取得や ETL 用モジュールを配置)
  - strategy/
    - __init__.py          — 戦略を配置するためのパッケージ
  - execution/
    - __init__.py          — 発注関連コードを置くパッケージ
  - monitoring/
    - __init__.py          — 監視・アラート関連コードを置くパッケージ

ドキュメント参照:
- DataSchema.md, DataPlatform.md（コード中のコメントに言及がありますが、リポジトリに合わせて参照してください）

---

## 注意点 / 補足

- DuckDB を利用しているため大きな CSV や OLAP 的な集計に向いています。
- 監査ログは削除を前提としない設計です（ON DELETE RESTRICT を採用）。監査整合性を壊さない運用が必要です。
- 時刻は監査用テーブルで UTC に固定されます（init_audit_schema が TimeZone を設定します）。
- .env の自動ロードはプロジェクトルート検出（.git または pyproject.toml）に基づくため、パッケージ配布後も期待通りに動作するように設計されています。
- テストなどで .env 自動読み込みを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

以上が現状の README（概要・セットアップ・基本的な使い方）です。必要であれば、例となる .env.example、依存関係ファイル（requirements.txt / pyproject.toml）、およびサンプルデータ投入スクリプトの追加を提案します。必要なら追記します。