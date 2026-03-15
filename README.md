# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。  
このリポジトリはデータ取得・スキーマ管理、戦略、発注（execution）および監視（monitoring）の土台を提供します。

---
## プロジェクト概要
KabuSys は日本株に対する自動売買プラットフォームの基盤部分を実装した Python パッケージです。  
主に以下を目的としています。

- 市場データ・ファンダメンタル・ニュース・約定などの永続化（DuckDB）
- 処理済みデータ・特徴量（feature）レイヤの提供
- 発注・約定・ポジション管理のスキーマ
- シグナルから約定までの監査（トレーサビリティ）テーブル
- 環境変数による設定管理（自動ロード機能）

バージョン: 0.1.0

---
## 機能一覧
- 環境変数/設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須キー取得とバリデーション（KABUSYS_ENV / LOG_LEVEL 等）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
- データスキーマおよび初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを DuckDB DDL で定義
  - init_schema(db_path) による DB 初期化（冪等）
  - get_connection(db_path) による接続取得
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを担保する監査テーブル
  - init_audit_schema(conn) / init_audit_db(db_path) による監査スキーマ初期化
  - UTC タイムゾーンでの TIMESTAMP 保存を強制
- 基礎モジュールのプレースホルダ
  - strategy, execution, monitoring パッケージ（将来の拡張ポイント）

---
## 前提条件 / 依存関係
- Python 3.9+
- duckdb（DuckDB Python バインディング）
- （必要に応じて）その他戦略・API クライアントライブラリ

インストール例（pip）:
```
pip install duckdb
```

プロジェクトがパッケージ化されていれば以下のようにローカルインストールできます:
```
pip install -e .
```

---
## セットアップ手順
1. リポジトリをクローン / ワークディレクトリへ配置
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（少なくとも duckdb）
4. プロジェクトルートに `.env`（必要なら `.env.local`）を作成して設定を記述
   - 自動読み込みは .git または pyproject.toml が存在するディレクトリを基準に行われます
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. DuckDB スキーマを初期化（後述の使い方参照）

.env の例（必須キーはプロジェクトの利用用途により異なります）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

.env のパースはシェル風の書式（export プレフィックス、引用符、コメント）を考慮して行われます。

---
## 環境変数（主な設定項目）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定値は kabusys.config.settings からプロパティとしてアクセスできます。

例:
```py
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

---
## 使い方（簡単な例）
1) DuckDB のスキーマを初期化して接続を取得する:
```py
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す
conn = init_schema(settings.duckdb_path)
# 以降 conn.execute(...) などで操作可能
```

2) 既存 DB へ接続する（スキーマ初期化は行わない）:
```py
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

3) 監査ログ用スキーマを既存接続へ追加する:
```py
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

または監査専用 DB を初期化:
```py
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- init_schema は冪等（既存テーブルがあればスキップ）です。
- init_audit_schema は UTC タイムゾーンを設定して TIMESTAMP を保存します。

---
## ディレクトリ構成
このリポジトリの主要なファイル・ディレクトリ:

- src/
  - kabusys/
    - __init__.py
    - config.py              : 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py            : DuckDB の DDL 定義・初期化 (Raw/Processed/Feature/Execution)
      - audit.py             : 監査ログ（signal / order_request / execution）定義・初期化
      - audit (.py)          : 監査関連モジュール（ファイル名は audit.py）
    - strategy/
      - __init__.py          : 戦略関連モジュール（拡張ポイント）
    - execution/
      - __init__.py          : 発注/ブローカー連携関連（拡張ポイント）
    - monitoring/
      - __init__.py          : 監視・メトリクス関連（拡張ポイント）

主なスキーマファイル:
- src/kabusys/data/schema.py
  - raw_prices, raw_financials, raw_news, raw_executions
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - features, ai_scores
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種インデックス定義
- src/kabusys/data/audit.py
  - signal_events, order_requests, executions
  - 監査用インデックス定義

---
## 備考 / 運用上の注意
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml が存在するディレクトリ) を基準に行います。CWD に依存しないため、パッケージ配布後も正しく機能します。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- .env の読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env の上書き）
- テーブルやインデックスは初期化時に作成されますが、アプリケーションロジック（データ取得、戦略、発注）部分は別モジュールで実装する想定です。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。

---
もしREADMEに加えたい運用フロー、サンプル戦略、またはCI/デプロイ手順があれば教えてください。必要に応じて追加で記載します。