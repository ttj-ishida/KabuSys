# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ライブラリ層）。  
J-Quants や kabuステーション 等の外部 API と連携してデータ収集・ETL・品質チェック・監査ログ等を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集と銘柄紐付け（SSRF / XML Bomb 等の対策を実装）
- DuckDB を使ったスキーマ定義・初期化・ETL パイプライン（差分取得・冪等保存）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティを確保する監査スキーマ）
- 市場カレンダー管理（営業日判定、翌営業日/前営業日計算、夜間バッチ）

設計上の特徴：
- 冪等性（DuckDB へは ON CONFLICT を用いた保存）
- Look-ahead bias 防止（fetched_at 等で「いつデータを知ったか」を記録）
- ネットワーク耐性（レート制御、指数バックオフ、トークンリフレッシュ）
- セキュリティ考慮（RSS の XML パースに defusedxml、SSRF 対策、受信サイズ制限）

---

## 機能一覧

主要モジュールと機能の概要：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）。環境変数管理。
  - settings オブジェクト経由で必須設定を取得。

- kabusys.data.jquants_client
  - ID トークン取得（refresh token を用いた POST）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）

- kabusys.data.news_collector
  - RSS フィード取得（gzip 対応、サイズ上限、SSRF リダイレクト検査）
  - 記事前処理（URL 除去、空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news および news_symbols への保存（トランザクション・チャンク処理）

- kabusys.data.schema
  - DuckDB 用テーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / get_connection

- kabusys.data.pipeline
  - 差分 ETL：市場カレンダー・日足・財務を差分で取得して保存
  - run_daily_etl による日次 ETL（品質チェック含む）
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ

- kabusys.data.calendar_management
  - 営業日判定・next/prev_trading_day・期間内営業日取得
  - calendar_update_job（夜間バッチでカレンダーを差分更新）

- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合のチェック機能
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db

---

## 前提条件

- Python 3.10+（typing の一部表記に合わせて）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク通信が可能な環境（J-Quants / RSS 取得等）

（プロジェクトの requirements.txt / packaging に従ってインストールしてください。最低限 duckdb と defusedxml は必要です。）

例：
pip install duckdb defusedxml

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt や pyproject.toml があればそちらを使用してください。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が読み込み）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 必要な環境変数（最小）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知に使用するボットトークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - 任意:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 .env（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema.init_schema を実行して DB ファイルとテーブルを作成します（親ディレクトリは自動作成されます）。

例：
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

6. 監査ログ DB 初期化（オプション）
   - 監査専用 DB を初期化する場合は init_audit_db を使用します（または既存 conn に init_audit_schema を呼ぶ）。

例：
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（コード例）

以下は代表的な利用例です。実際のプロダクションは適切な起動スクリプト / スケジューラで呼び出してください。

- 設定値の取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡さなければ今日
print(result.to_dict())
```

- 個別 ETL（例：株価のみ）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- J-Quants トークン取得 / API 呼び出し（テストやデバッグ）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

# 既存の conn を使う
# known_codes: 銘柄抽出に使う有効コードセット（例: 上場銘柄コード一覧）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 環境変数と自動 .env 読み込み

- 自動ロード優先順位：OS 環境変数 > .env.local > .env
- 自動ロードは kabusys.config がパッケージインポート時に行います（プロジェクトルートは .git または pyproject.toml で検出）。
- テストや一時的に自動ロードを無効にするには環境変数を設定します：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（再掲）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）：
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

settings オブジェクト経由でこれらを取得できます。

---

## ディレクトリ構成

（ソースツリーの重要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得／保存）
    - news_collector.py      — RSS ニュース収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（日次 ETL 等）
    - calendar_management.py — カレンダー管理（営業日判定／夜間更新）
    - audit.py               — 監査ログスキーマ初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連（拡張領域）
  - execution/
    - __init__.py            — 発注/約定/ポジション管理（拡張領域）
  - monitoring/
    - __init__.py            — 監視・メトリクス（拡張領域）

各モジュールは将来的に拡張されることを想定しており、strategy / execution / monitoring は骨組みを提供しています。

---

## 運用上の注意

- DuckDB は単一ファイル DB です。運用時はバックアップとロックの運用に注意してください（同時書き込み等）。
- J-Quants のレート制限（120 req/min）に合わせた実装が組み込まれていますが、大量取得や並列化する場合は追加の調整が必要です。
- RSS 取得や外部 URL の処理では SSRF、XML Bomb、巨大レスポンス等の対策を行っています。これらの制約（最大受信サイズなど）は要件に応じて調整してください。
- 監査ログ（audit）は UTC タイムゾーンでの保存を前提としています。

---

README の内容は現状のソースコードに基づく概要・利用方法です。実際の運用スクリプト（スケジューラや Web サービス）・ CI 設定・パッケージ化（pyproject.toml）等は別途整備してください。必要であればサンプル起動スクリプトや .env.example を作成できます。