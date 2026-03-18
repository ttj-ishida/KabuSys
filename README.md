# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）等の基盤機能を提供します。

## 主な特徴（概要）
- J-Quants API クライアント
  - 株価（日足 OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）に従うレートリミッタ付き
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装
- ニュース収集（RSS）
  - RSS から記事を収集し前処理（URL除去、空白正規化）して DuckDB に冪等保存
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、ホストプライベート判定、リダイレクト検査）、受信サイズ制限（10MB）
  - 銘柄コード抽出・紐付け機能
- ETL パイプライン
  - 差分更新（最終取得日＋バックフィル）で効率的にデータを取得・保存
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - スキーマ初期化（init_schema / init_audit_schema）
- 監査ログ（audit）
  - signal → order_request → execution の UUID 連鎖によるトレーサビリティ
  - 監査用テーブル群の初期化、インデックス定義を提供

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env または環境変数の自動読み込み（プロジェクトルート探索）
  - アプリ設定アクセス（settings）
  - 必須環境変数チェック
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.data.schema / audit
  - DuckDB スキーマ定義と init_schema / init_audit_db 等
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（日次 ETL）
- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合チェック
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job

---

## 必要条件
- Python 3.10+
- パッケージ依存（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外のパッケージは requirements.txt がある場合はそちらを使用してください）

※本リポジトリに requirements.txt が含まれていない場合は、上記最低限の依存を導入してください。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成し、必要な環境変数を設定してください（下記参照）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます（テスト時など）。

---

## 環境変数（主な項目）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知の Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境 (development, paper_trading, live)。デフォルト: development
- LOG_LEVEL (任意) — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)。デフォルト: INFO

注意: Settings クラスは必須変数未設定時に ValueError を投げます。

---

## スキーマ初期化（DuckDB）
Python REPL やスクリプトで実行します。

例: DuckDB のスキーマを初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成してテーブルを作成
```

監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に接続するだけなら get_connection() を使用します。

---

## 使い方（代表的な例）

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務データ取得 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 収集して raw_news に保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes に有効な銘柄コード集合を渡すと抽出・紐付けを実行します（省略可能）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
```

- J-Quants から株価を取得して保存（テスト用）
```python
from kabusys.data.schema import init_schema
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved={saved}")
```

- カレンダー操作例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 1, 1)))
print(next_trading_day(conn, date(2026, 1, 1)))
print(get_trading_days(conn, date(2026,1,1), date(2026,1,10)))
```

---

## ロギングと動作モード
- ログレベルは環境変数 LOG_LEVEL で制御します（Settings.log_level）。
- 実行モードは KABUSYS_ENV（development | paper_trading | live）で切り替え可能。設定値は Settings.is_dev 等で参照できます。

---

## 注意事項 / 設計に関するメモ
- J-Quants API のレート制限（120 req/min）を守るためにモジュール内部でスロットリングを行います。大量取得時は全体のスループットに注意してください。
- J-Quants の 401 応答時はリフレッシュトークンを用いて自動リフレッシュを行い、1 回だけ再試行します。
- news_collector は SSRF 対策、XML パーサに defusedxml を使用する等、セキュリティに配慮しています。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で実装されており、再実行が安全になるよう設計されています。
- ETL は Fail-Fast を基本とせず、各ステップのエラーを収集して報告する設計です。品質チェック（quality）で検出された問題は ETLResult で返されます。

---

## ディレクトリ構成
（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ __init__.py
  - strategy/ __init__.py
  - monitoring/ __init__.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - calendar_management.py
    - audit.py
    - quality.py

各ファイルの役割は上の「機能一覧」を参照してください。

---

## 開発・貢献
- 変更を加える場合はユニットテストを追加し、既存の ETL や保存ロジックの回帰を確認してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ご不明点や README に追記してほしい具体的な使い方（例: スケジューラ設定、slack 通知の使い方、kabu API 統合例など）があれば教えてください。追記して README を拡張します。