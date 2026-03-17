# KabuSys

日本株自動売買システムのコアライブラリ（KabuSys）。  
データ取得（J-Quants / RSS）、ETL、データ品質チェック、DuckDB スキーマ、監査ログなど自動売買に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けの共通ライブラリ群です。主な役割は以下です。

- J-Quants API からの市場データ（株価日足・財務データ・マーケットカレンダー）取得
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いた階層化されたデータスキーマ（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 設定管理（.env / 環境変数）

設計上のポイント:
- API レート制御（J-Quants: 120 req/min）
- 冪等性（DB 保存は ON CONFLICT で安全に上書き/スキップ）
- リトライ・トークン自動リフレッシュ（401 の際に1回リトライ）
- ニュース収集での SSRF 対策 / XML パースの安全化 / レスポンスサイズ制限
- 品質チェックで欠損・重複・スパイク・日付不整合を検出

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（OS 環境変数 > .env.local > .env）
  - 必須設定の取得（settings オブジェクト）

- データ取得（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar
  - レート制御・リトライ・ページネーション対応

- ニュース収集（kabusys.data.news_collector）
  - fetch_rss(url, source, timeout)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - extract_stock_codes(text, known_codes)
  - run_news_collection(...) — 複数 RSS ソースをまとめて収集・保存・銘柄紐付け

- スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) — DuckDB スキーマの初期化（冪等）
  - get_connection(db_path)

- ETL（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(...) — 日次 ETL 実行（差分取得 + バックフィル + 品質チェック）

- 品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(conn, ...)

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn)
  - init_audit_db(db_path)

- その他: execution, strategy, monitoring 各パッケージのプレースホルダ（将来の発注/戦略/監視機能）

---

## セットアップ手順

前提: Python 3.10+ （型ヒントに Union 型記法などを使っているため想定）

1. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   例:
     - python -m pip install duckdb defusedxml

   （実運用では logging, requests 等の追加や、パッケージ管理ファイルを用意してください）

3. パッケージを開発モードでインストール（任意）
   - プロジェクトルートに setup.cfg / pyproject.toml がある想定で:
     - python -m pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"

例 .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方

以下は主要な機能の利用例（抜粋）。実際はロガー設定やエラーハンドリングを追加してください。

- 設定の利用
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path("data/kabusys.duckdb") 等
```

- スキーマ初期化（DuckDB）
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)  # ファイルを自動作成してテーブル作成
```

- 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

- J-Quants からデータ取得と保存（例: 株価）
```python
from kabusys.data import jquants_client as jq
# id_token を明示しない場合は settings.jquants_refresh_token を使って自動取得/キャッシュされます
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"保存件数: {saved}")
```

- 日次 ETL を実行（差分取得 + 品質チェック）
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- RSS ニュース収集（単一ソース）
```python
from kabusys.data import news_collector as nc

articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = nc.save_raw_news(conn, articles)
# 銘柄紐付けを行う場合は known_codes を渡す run_news_collection を使うか、個別に save_news_symbols を呼ぶ
```

- ニュース収集ジョブ（複数ソース・銘柄紐付け）
```python
from kabusys.data import news_collector as nc
known_codes = {"7203", "6758", "9984"}  # 実際には銘柄一覧を用意
results = nc.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API の refresh token

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード

- KABU_API_BASE_URL (任意)
  - デフォルト "http://localhost:18080/kabusapi"

- SLACK_BOT_TOKEN (必須)
  - Slack 通知に使用する Bot トークン

- SLACK_CHANNEL_ID (必須)
  - 通知先チャネル ID

- DUCKDB_PATH (任意)
  - デフォルト "data/kabusys.duckdb"

- SQLITE_PATH (任意)
  - デフォルト "data/monitoring.db"

- KABUSYS_ENV (任意)
  - development / paper_trading / live（デフォルト development）
  - settings.is_live / is_paper / is_dev が使用可能

- LOG_LEVEL (任意)
  - ログレベル（デフォルト INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。

---

## ディレクトリ構成

ソースは `src/kabusys` 以下に配置されています。主要ファイル:

- src/kabusys/
  - __init__.py  -- パッケージ定義（version, __all__）
  - config.py    -- 環境変数・設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py   -- RSS 収集、前処理、保存、銘柄抽出
    - schema.py           -- DuckDB スキーマ定義 & 初期化
    - pipeline.py         -- ETL パイプライン（差分取得・品質チェック）
    - audit.py            -- 監査ログスキーマ（signal / order_request / executions）
    - quality.py          -- データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py         -- 戦略層（プレースホルダ）
  - execution/
    - __init__.py         -- 発注/約定管理（プレースホルダ）
  - monitoring/
    - __init__.py         -- 監視関連（プレースホルダ）

---

## 開発・運用上の注意

- J-Quants API のレート制限（120 req/min）を厳守しているため、バッチ処理はその点に注意してください。
- DuckDB のスキーマは冪等に作られる設計です。既存のデータを壊さないよう ON CONFLICT 等で安全に保存します。
- ニュース収集では SSRF 対策や XML パース対策（defusedxml）を実装していますが、外部ソースの扱いには常に注意してください。
- ETL の品質チェックは警告/エラーを報告します。呼び出し側で重大度に応じた運用対応を実装してください。
- 本ライブラリは発注・実際のブローカー接続ロジックは含みません（execution, strategy パッケージは将来的実装想定）。実行環境での安全策（テストネット / paper_trading モード）を必ず整備してください。

---

必要に応じて README を拡張します。README に追加したい具体的な内容（例: 完全な依存関係ファイル、CI/デプロイ手順、具体的な ETL スケジュール例など）があれば教えてください。