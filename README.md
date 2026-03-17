# KabuSys

日本株自動売買システム向け基盤ライブラリ (KabuSys)

このリポジトリは、日本株のデータ収集・ETL・品質検査・監査ログ・ニュース収集など、アルゴリズム売買システムのデータ基盤周りを提供する Python パッケージです。J-Quants API 経由で株価・財務・マーケットカレンダーを取得し、DuckDB に保存・整形し、戦略層／実行層が利用できる形に整えます。

バージョン: 0.1.0

---

## 主要機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務諸表、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）に準拠するスロットリング
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを回避

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - 冪等な初期化 (CREATE TABLE IF NOT EXISTS 等)
  - インデックス定義

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）、バックフィル（日数指定）対応
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）

- ニュース収集
  - RSS から記事を収集して raw_news に保存
  - URL 正規化／トラッキングパラメータ削除、記事ID は URL の SHA-256（先頭 32 文字）
  - SSRF 対策（スキーム検証、リダイレクト先検査、プライベートホスト拒否）
  - defusedxml を使った安全な XML パース、受信サイズ制限

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までトレース可能な監査テーブル群
  - 発注の冪等キー（order_request_id）や broker_execution_id による重複防止
  - UTC タイムスタンプ固定

- データ品質モジュール
  - 複数チェックを提供し QualityIssue として集約して返す（Fail-Fast ではない）

---

## セットアップ手順（開発環境）

前提: Python 3.10 以上を想定しています（型表現に | を使用）。

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

2. 必要なパッケージをインストールします（例）:

   ```
   pip install duckdb defusedxml
   ```

   追加でプロジェクト固有の依存があれば requirements.txt / pyproject.toml に従ってください。

3. パッケージとして編集可能インストール（任意）:

   ```
   pip install -e .
   ```

   （本リポジトリに pyproject.toml/setup.cfg がある想定です。ない場合は上の必須ライブラリを個別にインストールしてください。）

---

## 環境変数・設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準とします。優先順位は OS 環境変数 > `.env.local` > `.env`。テスト時などに自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須なものに注意）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack bot token
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

サンプル `.env`（置き場所はプロジェクトルート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

コード内では `from kabusys.config import settings` でアクセスできます（例: `settings.jquants_refresh_token`）。

---

## 使い方（代表的な操作）

以下は Python REPL / スクリプト内での利用例です。DuckDB 接続は必ず init_schema または get_connection を通して取得してください。

- スキーマ初期化（DuckDB）:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 日次 ETL（株価・財務・カレンダーの差分取得 + 品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトは今日
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

- ニュース収集（RSS）ジョブ:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 銘柄抽出用の有効コードセット（例として "7203" 等）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- 監査ログスキーマ初期化（独立DB または既存 conn に追加）:

```python
from kabusys.data.audit import init_audit_db, init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

# 監査専用 DB を初期化
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

# 既存 conn に監査テーブルを追加する場合
main_conn = init_schema(settings.duckdb_path)
init_audit_schema(main_conn, transactional=True)
```

- 設定値参照:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path
is_live = settings.is_live
```

---

## 主要モジュール概要

- kabusys.config
  - 環境変数読み込み（.env 自動読み込み）、settings オブジェクト提供

- kabusys.data.jquants_client
  - J-Quants API とのやりとり、fetch_* / save_* 関数

- kabusys.data.news_collector
  - RSS 取得、記事正規化、raw_news 保存、銘柄抽出・news_symbols 紐付け

- kabusys.data.schema
  - DuckDB スキーマ定義、init_schema / get_connection

- kabusys.data.pipeline
  - ETL ロジック（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）

- kabusys.data.calendar_management
  - 営業日判定や next/prev_trading_day、calendar_update_job

- kabusys.data.audit
  - 監査ログテーブルの初期化（信頼性・トレーサビリティ確保）

- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）

- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略／実行／監視層のための名前空間（現時点ではモジュールが揃っている構成）

---

## ディレクトリ構成

以下は主要ファイル・モジュールのツリーです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のプロジェクトルートに pyproject.toml / setup.cfg / requirements.txt がある想定）

---

## 運用上の注意点・設計上のポイント

- 自動環境読み込みはプロジェクトのルート検出 (.git または pyproject.toml) に依存します。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- J-Quants API のレート制限（120 req/min）に準拠するため、クライアントは固定間隔スロットリングを行います。大量取得時は注意してください。
- DB 保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）となるよう設計されています。
- RSS 収集は SSRF や XML 攻撃対策を施しています（スキーム検証、プライベートアドレスチェック、defusedxml、最大受信サイズ制限）。
- 監査ログは削除しない前提で設計されており、UTCタイムゾーンを使用します。

---

## ライセンス / コントリビューション

この README はコードベースの説明を目的としたものです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

---

質問や利用方法の具体例（ETL のチューニング、バックフィル戦略、監査モデルの統合など）が必要であれば、目的に合わせた利用例・スニペットを追加で作成します。どの部分のドキュメントが欲しいか教えてください。