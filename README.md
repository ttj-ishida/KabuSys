# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETLパイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（トレーサビリティ）など、アルゴリズムトレーディング基盤の中核を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得し DuckDB に保存する ETL パイプライン
- RSS からニュースを安全に収集して正規化・保存し、銘柄コードを抽出して紐付けるニュースコレクター
- 市場カレンダー（JPX）の管理と営業日判定ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合など）
- 監査ログ（signal → order_request → execution のトレース）用スキーマと初期化処理
- 環境変数による設定管理（.env 自動読み込み機能あり）

設計上の注力点は「冪等性」「Look-ahead バイアス回避（fetched_at 保存）」「API レート制御」「セキュリティ（SSRF／XML 脆弱性対策）」「トレーサビリティ（監査ログ）」です。

---

## 機能一覧

主な機能

- 環境設定管理
  - .env / .env.local から自動読み込み（プロジェクトルート検出）
  - 必須設定を抽出する Settings オブジェクト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回、401 時はトークン自動リフレッシュ）
  - DuckDB へ冪等保存（ON CONFLICT ... DO UPDATE）
  - fetched_at による取得時刻の UTC 記録

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化とトラッキングパラメータ除去
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）
  - サイズ制限（最大 10MB）や gzip 解凍チェック
  - DuckDB へ冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING）
  - 記事から銘柄コード抽出（4桁数字）と news_symbols へ紐付け

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL 定義
  - テーブル・インデックスの作成（init_schema）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日に基づく自動差分算出）
  - backfill による再取得（API の後出し修正吸収）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（quality モジュール）との統合
  - 主要エントリポイント: run_daily_etl

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、prev/next_trading_day、期間内営業日取得
  - calendar_update_job による夜間差分更新

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と索引
  - init_audit_schema / init_audit_db による初期化
  - UTC タイムゾーン固定および冪等性／監査要件の考慮

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク検出、重複、日付不整合の検査
  - 問題は QualityIssue オブジェクトで返却（severity: error|warning）
  - run_all_checks で一括実行

---

## 前提・依存パッケージ

少なくとも下記が必要です（プロジェクトの pyproject/requirements に合わせてください）:

- Python 3.9+
- duckdb
- defusedxml

インストール例（プロジェクトルートで）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはパッケージ配布があれば
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを取得）

2. 仮想環境を作成し依存をインストール（上記参照）

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（必要なら `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

必要な主な環境変数（一例）:

- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL      (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN        (必須) — 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID       (必須) — 通知先チャンネル ID
- DUCKDB_PATH            (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH            (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV            (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例: `.env`（簡略）

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

4. DuckDB スキーマ初期化

Python REPL やスクリプトで:

```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# 監査ログを別DBで使う場合
# from kabusys.data.audit import init_audit_db
# audit_conn = init_audit_db('data/kabusys_audit.duckdb')
```

---

## 使い方（基本例）

以下は主要な操作のサンプルコードです。

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）:

```python
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)  # デフォルトは今日
print(result.to_dict())
```

- ニュース収集ジョブを実行:

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# sources を省略すると DEFAULT_RSS_SOURCES が使われる
res = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
print(res)
```

- 市場カレンダーの夜間更新ジョブ:

```python
from kabusys.data import calendar_management, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- 監査スキーマの初期化（既存接続へ追加）:

```python
from kabusys.data import schema
from kabusys.data import audit
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn, transactional=True)
```

- J-Quants から直接データ取得（テスト用）:

```python
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使う
quotes = jq.fetch_daily_quotes(id_token=token, code='7203', date_from=...)
```

注意:
- run_daily_etl などは内部で例外処理を行い、個々のステップが失敗しても他のステップを続行します。戻り値の ETLResult で errors / quality_issues を確認してください。
- テスト時に環境変数自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して import してください。

---

## 設計上のポイント（開発者向けメモ）

- J-Quants クライアントはモジュール内で ID トークンをキャッシュし、401 時に1回だけリフレッシュして再試行します。
- レート制御は固定間隔スロットリングで実装（120 req/min → 最小インターバル 0.5s）。
- DuckDB への保存は出来るだけ冪等（ON CONFLICT）にして、複数実行や再実行に耐えるようにしています。
- NewsCollector は SSRF、XML Bomb、gzip bomb、トラッキングパラメータに配慮した堅牢実装です。
- Calendar 管理は DB の存在に応じて DB 値優先／曜日フォールバックの一貫した挙動を提供します。
- 監査テーブルは UTC を前提にしており、削除しない前提（ON DELETE RESTRICT）です。

---

## ディレクトリ構成

主要ファイルとモジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                    -- DuckDB スキーマ（DDL）と init_schema
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       -- マーケットカレンダー管理
      - audit.py                     -- 監査ログスキーマ（signal/order/execution）
      - quality.py                   -- データ品質チェック
    - strategy/
      - __init__.py                  -- 戦略層（拡張想定）
    - execution/
      - __init__.py                  -- 発注／実行層（拡張想定）
    - monitoring/
      - __init__.py                  -- 監視用（拡張想定）

各モジュールは役割ごとに分割されており、戦略・実行層は今後の追加実装を想定しています。

---

## よくある操作のヒント

- テスト時に .env の自動読み込みを避けたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を先にセットしてから import してください。

- DuckDB をインメモリで試したい場合:
  - schema.init_schema(":memory:")

- ログレベルや実行モードは環境変数で制御:
  - KABUSYS_ENV は development / paper_trading / live
  - LOG_LEVEL を DEBUG 等に設定して詳細ログを確認

---

## 免責・今後の拡張

- このリポジトリはコア機能を提供するための基盤です。実際の売買を行う前に入念なテストとリスク評価を行ってください（特に live 環境）。
- strategy/, execution/, monitoring/ は拡張ポイントです。リスク管理、ポジション管理、注文実行のブリッジ実装を追加してください。

---

ご質問や README に追加したい例（CI、デプロイ、運用手順など）があればお知らせください。README をそれに合わせて拡張します。