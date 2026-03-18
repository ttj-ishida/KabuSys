# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS 等から市場データ・ニュースを取得し、DuckDB に保存・整形し、戦略や発注レイヤーへ渡すための ETL / データ品質・監査機能を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT）で保存
- API レート制限・リトライ・トークン自動リフレッシュを実装
- ニュース収集は SSRF 対策、サイズ制限、XML 脆弱性対策あり
- DuckDB を中心としたスキーマ設計（Raw / Processed / Feature / Execution / Audit）

---

## 主要機能一覧

- 環境変数 / .env の自動読み込みと設定ラッパー（kabusys.config）
  - 必須設定のチェック、環境（development/paper_trading/live）・ログレベルの検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務（四半期）データ、JPX カレンダーの取得
  - API レート制御（120 req/min）、指数バックオフ、最大3回リトライ
  - 401 時はリフレッシュトークンから id_token を自動更新して再試行
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理、記事ID の一意化（正規化URL→SHA-256）
  - defusedxml による XML パース、安全なリダイレクト検証（SSRF 対策）
  - 受信サイズ上限、gzip 解凍チェック、DuckDB へのバルク保存（RETURNING を使用）
  - 記事と銘柄コードの紐付け（news_symbols）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル、インデックスを定義
  - init_schema / get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（backfill サポート）、市場カレンダー先読み、品質チェック統合
  - run_daily_etl を中心に prices/financials/calendar 個別 ETL も提供
- マーケットカレンダー管理ユーティリティ（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間カレンダー更新バッチ（calendar_update_job）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
  - run_all_checks で一括実行
- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定までトレース可能な監査テーブル群と初期化関数
  - init_audit_schema / init_audit_db
- パッケージ構成上、strategy / execution / monitoring 用のプレースホルダパッケージあり

---

## 前提条件

- Python 3.9+（型ヒントに Path | None 等を使用しているため、3.9+ を想定）
- 必要なライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt があればそれを利用してください）

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトの packaging があれば pip install -e . または requirements.txt を使用）

3. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（コード例）

以下は主要なワークフロー例です。実運用ではロギングや例外ハンドリング、スケジューラ（cron / Airflow 等）での実行を推奨します。

1) DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)  # settings.duckdb_path は Path
```

2) 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS から記事を収集して保存、既知銘柄で紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は有効な銘柄コードセット。未指定なら紐付けはスキップ
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数, ...}
```

4) 監査用 DB の初期化（監査ログ専用）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

6) 品質チェックを個別実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 主要 API（要点）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id, settings.duckdb_path, settings.env, settings.log_level, settings.is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list of new ids
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None)

---

## ディレクトリ構成（リポジトリ内の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定の読み込み
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS 収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・init
    - pipeline.py                   — 日次 ETL / 個別 ETL ジョブ
    - calendar_management.py        — カレンダー管理・営業日判定
    - audit.py                      — 監査ログテーブル定義・初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略関連（プレースホルダ）
  - execution/
    - __init__.py                   — 発注実行関連（プレースホルダ）
  - monitoring/
    - __init__.py                   — 監視関連（プレースホルダ）

---

## 開発・運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を親ディレクトリに持つ場所）を基準に行います。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レート制限（120 req/min）は jquants_client 内で RateLimiter により保護されています。複数プロセスで API を叩く際は追加の共有制御が必要です。
- DuckDB はファイルベースの軽量 DB です。バックアップやロックの運用に注意してください。
- ニュース収集は外部からの RSS を扱うため、SSRF・XML Bomb 対策を実装していますが、外部入力を扱う際は常に注意してください。
- ログレベルは LOG_LEVEL 環境変数で制御します（デフォルト INFO）。

---

もし README に追加してほしい内容（例: 実行スクリプト例、CI/テスト手順、より詳細な環境変数一覧、パッケージの exact requirements）や、特定の機能についての詳しいドキュメントが必要であれば教えてください。