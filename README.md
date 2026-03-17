# KabuSys — 日本株自動売買基盤ライブラリ

簡潔な説明書（README）。このリポジトリは日本株の自動売買/データ基盤を構築するためのライブラリ群を提供します。主にデータ取得（J-Quants）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログなどの基盤機能を含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から日本株の株価（OHLCV）、財務データ、JPX マーケットカレンダーを安全・効率的に取得する
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL（差分取得・バックフィル・品質チェック）を実行するパイプライン
- RSS を使ったニュース収集と、ニュース → 銘柄コード紐付け
- カレンダーバッチ更新（営業日判定・next/prev_trading_day 等）
- 発注／約定フローの監査ログ管理（監査テーブル初期化・インデックス等）
- 環境変数による設定管理（.env/.env.local の自動読み込み対応）

設計上のポイント：
- API のレート制限（例：J-Quants 120 req/min）を尊重する RateLimiter を実装
- リトライ（指数バックオフ）や ID トークン自動リフレッシュを備え堅牢な取得処理
- DuckDB への保存は冪等性（ON CONFLICT ... DO UPDATE / DO NOTHING）を担保
- NewsCollector は SSRF 対策、XML脆弱性対策（defusedxml）、受信サイズ制限などセキュリティ配慮あり
- 品質チェックモジュールで欠損・重複・スパイク・日付不整合を検出

---

## 主な機能（抜粋）

- kabusys.config.Settings：環境変数管理と自動ロード（.env/.env.local）
- kabusys.data.jquants_client：
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（リフレッシュトークンから id token を取得）
- kabusys.data.schema：
  - init_schema(db_path) : DuckDB の全スキーマ作成
  - get_connection(db_path)
- kabusys.data.pipeline：
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl : 日次 ETL の統合エントリポイント（品質チェックを含む）
- kabusys.data.news_collector：
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - extract_stock_codes（テキストから銘柄コード抽出）
- kabusys.data.calendar_management：
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）
- kabusys.data.audit：
  - init_audit_schema / init_audit_db（監査ログ用テーブル初期化）
- kabusys.data.quality：
  - run_all_checks（欠損・スパイク・重複・日付不整合チェック）

---

## 動作要件

- Python 3.10 以上（型注釈や union 型（|）を使用）
- 主要依存ライブラリ（最低限）:
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime, pathlib 等）を使用

requirements.txt がない場合は手動でインストールしてください。例:
```
pip install duckdb defusedxml
```

（実運用では Slack 通知や kabu API クライアント等の追加依存がある想定です）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードはデフォルトで有効ですが、テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須のものを含む）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（使用する機能がある場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 有効値: development, paper_trading, live（デフォルト development）
- LOG_LEVEL — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=hoge1234
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注: config._require() は必須変数が未設定の場合に ValueError を投げます。.env.example を参考に作成してください。

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境を作成・有効化（推奨）
```
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 依存パッケージをインストール
（必要なパッケージリストに基づき）
```
pip install duckdb defusedxml
# 追加: requests 等を使う機能があれば適宜インストール
```

4. 環境変数を設定（.env / .env.local をプロジェクトルートに作成）
例: `.env` をプロジェクトルートに配置（上記「環境変数」参照）

5. DuckDB スキーマ初期化
Python REPL やスクリプトで実行:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ（audit）スキーマを別途追加する場合:
```python
from kabusys.data import audit
audit.init_audit_schema(conn)  # conn は init_schema の返り値
```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（デフォルトは今日の日付）:
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既に初期化済みであること
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ETL の一部（価格のみ）を差分取得:
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュースを収集して保存:
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# sources を省略するとデフォルトの RSS ソースが使われる
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存数}
```

- カレンダーの夜間バッチ更新:
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- 営業日判定や次の営業日取得:
```python
from kabusys.data import calendar_management, schema
from datetime import date
conn = schema.get_connection("data/kabusys.duckdb")
d = date(2024, 1, 1)
print(calendar_management.is_trading_day(conn, d))
print(calendar_management.next_trading_day(conn, d))
```

- 品質チェックを個別に実行:
```python
from kabusys.data import quality, schema
from datetime import date
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数/設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS 収集・前処理・保存処理
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py          — マーケットカレンダー管理・営業日ロジック
    - audit.py                        — 監査ログ（signal/order/execution）テーブル初期化
    - quality.py                      — データ品質チェック
  - strategy/
    - __init__.py                      — 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py                      — 発注/実行関連モジュール（拡張ポイント）
  - monitoring/
    - __init__.py                      — 監視・メトリクス関連（拡張ポイント）

（README 内で説明した関数群は上記ファイルに定義されています。）

---

## 運用上の注意 / トラブルシューティング

- J-Quants のレート制限を超えないようモジュール内で制御していますが、複数プロセスから同時に実行する場合は外部で調整してください。
- get_id_token はリフレッシュトークンを使用して id token を取得します。環境変数 `JQUANTS_REFRESH_TOKEN` の管理には十分注意してください。
- news_collector は外部 URL を取り扱うため SSRF 対策や受信サイズ上限等の保護ロジックを含んでいます。独自拡張の際もセキュリティに注意してください。
- DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）は設定可能です。バックアップ・アクセス権限を運用で管理してください。
- config.py はプロジェクトルート（.git または pyproject.toml の存在）を起点に .env 自動ロードを行います。CI 等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 拡張ポイント

- strategy / execution / monitoring パッケージはプレースホルダになっており、独自の取引ロジック・発注ドライバ・監視機能を実装可能です。
- Slack 通知や監視アラートの統合（Slack Bot の利用）は設定変数が用意されているため組み込みやすくなっています。

---

以上がこのリポジトリの README（日本語）です。追加で「セットアップの自動スクリプト」「requirements.txt」「実行用 CLI」「運用手順書（Runbook）」などを作成する場合は、目的に応じたテンプレートや具体的なコマンドを準備できます。必要であれば追記します。