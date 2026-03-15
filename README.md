# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買基盤（プロトタイプ）です。市場データ取得、特徴量生成、シグナル管理、発注／約定記録（監査ログ）などを想定したデータモデルとユーティリティを提供します。

主なポイント:
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）
- 発注フローを完全にトレース可能にする監査ログ（order_request_id を冪等キーとして扱う）
- 環境変数 / .env の柔軟な読み込み・管理
- Slack / kabuステーション / J-Quants 等の設定を環境変数から取得する Settings API

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - 必須/任意設定を Python プロパティとして参照可能（例: settings.jquants_refresh_token）
  - 有効な実行環境: development / paper_trading / live。LOG_LEVEL のバリデーション

- DuckDB ベースのデータスキーマ（data.schema）
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義と冪等（CREATE IF NOT EXISTS）による安全な初期化
  - init_schema() / get_connection() API

- 監査ログ（data.audit）
  - signal_events, order_requests, executions の監査テーブル
  - order_request_id（UUID）を冪等キーとして扱う設計
  - UTC による TIMESTAMP 保存（init_audit_schema は TimeZone を UTC に設定）
  - init_audit_schema() / init_audit_db() API

- パッケージ構造の拡張ポイント
  - strategy/, execution/, monitoring/ フォルダを想定（現在は初期化モジュールのみ）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションの union | を使用）
- pip が使用可能

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - duckdb が必須です:
     - pip install duckdb
   - （将来的に他の依存が増える場合は requirements.txt / pyproject.toml を参照）

4. パッケージのインストール（任意、開発モード）
   - リポジトリルートに pyproject.toml 等がある想定で:
     - pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（既存の OS 環境変数が優先されます）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1  (Windows: set KABUSYS_DISABLE_AUTO_ENV_LOAD=1)

必須の環境変数（Settings から参照される）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意の環境変数（デフォルト値あり）
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

.env のパース仕様（簡潔）
- 空行・先頭が # の行は無視
- export KEY=val 形式に対応
- 値はシングル／ダブルクォートで囲める（エスケープシーケンス対応）
- クォート無しの場合、inline の # は直前がスペース/タブのときコメント扱い

---

## 使い方

以下は代表的な使用例です。

- Settings の参照例
```
from kabusys.config import settings

# 必須項目は設定されていないと例外が上がる
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.env)
print(settings.is_live)
```

- DuckDB スキーマの初期化（ファイルベース）
```
from kabusys.data.schema import init_schema

# デフォルトのパスを使う場合は settings.duckdb_path を参照して init_schema に渡す
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection。以降 SQL を実行可能
```

- DuckDB をインメモリで初期化（テスト等）
```
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
# 必要なら init_audit_schema を同じ接続に追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- 監査ログ専用 DB 初期化
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 自動ロードをテスト時に無効化
```
import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
# その後パッケージをインポートすると .env 読み込みは行われない
```

注意:
- init_schema は親ディレクトリを自動作成します（例: data/）。
- init_schema / init_audit_db は冪等（存在するテーブルはそのまま）なので安全に複数回呼べます。

---

## ディレクトリ構成

リポジトリ内の主なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py              (パッケージ定義、バージョン)
    - config.py                (環境変数・設定管理)
    - data/
      - __init__.py
      - schema.py              (DuckDB スキーマ定義・初期化: init_schema, get_connection)
      - audit.py               (監査ログ定義・初期化: init_audit_schema, init_audit_db)
      - audit.py               (監査用 DDL・インデックス定義)
      - ...                    (将来のデータ処理モジュール)
    - strategy/
      - __init__.py            (戦略層のエントリポイント)
    - execution/
      - __init__.py            (発注/実行層のエントリポイント)
    - monitoring/
      - __init__.py            (モニタリング関連のエントリポイント)
- .env.example (想定: 環境変数の例を置くと良い)
- pyproject.toml / setup.cfg / requirements.txt (プロジェクトに応じて)

---

## 補足・設計メモ

- data/schema.py は「Raw → Processed → Feature → Execution」の4層を意識したスキーマ設計です。特徴量や AI スコア、ポートフォリオ情報まで含みます。
- data/audit.py はシグナルから約定までのトレーサビリティを重視して設計されています。order_request_id を冪等キーとして扱い、失敗や棄却も含めて必ず永続化する前提です。
- タイムゾーン: 監査ログ初期化時（init_audit_schema）は UTC を強制しています。アプリ側は updated_at を更新するときに current_timestamp をセットする設計です。
- .env の自動読み込み順序: OS 環境変数 > .env.local > .env。プロジェクトルートが検出できない場合は自動ロードをスキップします。

---

必要に応じて README を拡張して、実際のデータ取得スクリプト、戦略の実装テンプレート、監視アラート（Slack 連携例）などを追加してください。質問や追記したい項目があれば教えてください。