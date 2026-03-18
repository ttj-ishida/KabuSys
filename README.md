# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ、監査ログなど、取引戦略実行に必要な基盤機能を提供します。

## 概要

KabuSys は以下を主な目的とする Python パッケージです。

- J-Quants API から株価（OHLCV）、財務データ、JPX カレンダー等を取得して DuckDB に保存する ETL パイプライン
- RSS フィードからのニュース収集と銘柄紐付け（SSRF / XML Bomb 対策あり）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- DuckDB 上のスキーマ初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ用スキーマ（シグナル→発注→約定までのトレーサビリティ）
- 設定管理（.env / 環境変数自動ロード、強制設定チェック）

設計上のポイント：
- API レート制限（J-Quants 120 req/min）を考慮した RateLimiter を実装
- リトライ（指数バックオフ）・401 自動リフレッシュ・ページネーション対応
- DuckDB への保存は冪等（ON CONFLICT）で上書き・重複排除
- ニュースの URL 正規化・ID は SHA-256 先頭32文字で冪等化
- RSS 収集での SSRF 対策（スキーム検証、プライベートIP防止、リダイレクト検査）
- すべてのタイムスタンプは UTC で扱う（監査DB等）

---

## 主な機能一覧

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.jquants_client
  - J-Quants API クライアント（token refresh、リトライ、レート制御）
  - fetch/save: 日次株価、財務、マーケットカレンダー
- kabusys.data.schema
  - DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution）
  - インデックス定義
- kabusys.data.pipeline
  - 差分 ETL（prices / financials / calendar）および日次 ETL 実行(run_daily_etl)
  - 品質チェックの呼び出し（kabusys.data.quality）
- kabusys.data.news_collector
  - RSS 取得、前処理、記事の冪等保存、銘柄コード抽出・紐付け
  - セキュリティ対策（defusedxml、SSRF 防止、レスポンスサイズ制限等）
- kabusys.data.quality
  - 欠損 / スパイク / 重複 / 日付不整合のチェック
  - QualityIssue を返し、呼び出し側で重大度に応じた対応が可能
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - 監査DB 初期化ヘルパー

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで | を使用）
- DuckDB を利用するため sqlite/duckdb バイナリが利用可能な環境

1. リポジトリをクローンし、パッケージをインストール
   - 開発環境であれば editable install を推奨
   ```
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```
   ※ 実際の requirements.txt / pyproject.toml があればそちらを使ってください。

2. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN - J-Quants の refresh token（必須）
   - KABU_API_PASSWORD - kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN - Slack 通知用 Bot token（必須）
   - SLACK_CHANNEL_ID - Slack チャネル ID（必須）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development|paper_trading|live) - default: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - default: INFO

3. DuckDB スキーマ初期化
   例:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

4. 監査ログスキーマ（必要な場合）
   例（同一 DB に追加）:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```
   または別 DB:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（基本例）

以下は主要な機能の使用例です。実運用ではログ設定やエラーハンドリングを追加してください。

1. 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（なければ作る）
conn = init_schema(settings.duckdb_path)

# 日次 ETL（target_date を指定しなければ今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

2. ニュース収集ジョブを実行して DB に保存する
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings
import duckdb

conn = init_schema(settings.duckdb_path)

# known_codes を DB から集める（例: prices_daily のコード一覧）
known_rows = conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()
known_codes = {row[0] for row in known_rows}

# タイムアウトや sources を上書き可能
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes, timeout=30)
print(results)  # {source_name: 新規保存件数}
```

3. J-Quants の生データを直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# 例: 特定銘柄の過去1週間分を取得して保存
from datetime import date, timedelta
to_date = date.today()
from_date = to_date - timedelta(days=7)
records = jq.fetch_daily_quotes(date_from=from_date, date_to=to_date, code="7203")
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

4. 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## .env 自動読み込みの挙動

- 自動ロード対象ファイル順:
  1. OS 環境変数（優先）
  2. .env.local（ある場合、OS を除く変数を上書き）
  3. .env（上書きしない）

- プロジェクトルートの検出:
  - このパッケージの __file__ を起点に親ディレクトリを走査し、.git または pyproject.toml が見つかったディレクトリをプロジェクトルートとします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env ファイルのフォーマットは一般的な KEY=VALUE、シングル/ダブルクォート対応、export KEY=val 形式対応、コメント行対応などに対応します。

---

## 主要 API の説明（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env など

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)  — refresh token から id token を取得

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)  — 単一フィード取得
  - save_raw_news(conn, articles)  — raw_news へ保存（挿入された記事 id を返す）
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)  — 複数ソースをまとめて収集

- kabusys.data.schema
  - init_schema(db_path)  — DuckDB スキーマ初期化
  - get_connection(db_path)

- kabusys.data.audit
  - init_audit_db(db_path), init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成

リポジトリ内（src/kabusys）のおおまかな構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
    - news_collector.py      — RSS 収集・正規化・保存ロジック
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py — マーケットカレンダー操作ユーティリティ
    - audit.py               — 監査ログテーブル定義・初期化
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連（未実装ファイル群のため拡張を想定）
  - execution/                — 発注・執行関連（未実装ファイル群のため拡張を想定）
  - monitoring/               — 監視（未実装ファイル群のため拡張を想定）

---

## 注意事項 / 運用上のヒント

- J-Quants API のレート制限（120 req/min）やリトライ挙動を考慮して実行間隔を設計してください。
- run_daily_etl は品質チェックで検出された問題を返します。重大な問題がある場合は運用側でアラートや ETL リトライ方針を決めてください。
- news_collector では RSS の XML をパースする際に defusedxml を利用しており、レスポンスサイズ上限が設定されています（デフォルト 10MB）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップや権限管理を忘れずに。
- 監査ログ（audit）を有効にすることで、シグナルから約定に至る全フローのトレーサビリティが確保されます。運用時はタイムゾーン（UTC）や updated_at の更新をアプリ側で正しく扱ってください。

---

もし README に追加したい内容（例えば CI・テスト手順、詳細な .env.example、実運用のワークフロー例、Docker / systemd サービス定義など）があれば教えてください。必要に応じて追記します。