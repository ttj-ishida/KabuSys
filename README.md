# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API や RSS を用いたデータ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、マーケットカレンダー管理、品質チェック、監査ログ（オーダー/約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数/設定管理
  - `.env` / `.env.local` から自動ロード（必要なら無効化可）
  - 実行環境（development / paper_trading / live）やログレベル検証
- J-Quants API クライアント
  - 日足（OHLCV）・財務（四半期 BS/PL）・JPX カレンダー取得
  - レート制限遵守（120 req/min）、リトライ、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等保存（ON CONFLICT）
- ニュース収集（RSS）
  - RSS 取得、XML の安全パース（defusedxml）、URL 正規化・トラッキング除去
  - SSRF 対策（リダイレクト/ホスト検証）、レスポンスサイズ制限
  - DuckDB へ冪等保存（INSERT ... RETURNING）および銘柄コード抽出・紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブルを定義・初期化
  - インデックスの作成、監査ログ用スキーマも提供
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、backfill のサポート）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・期間内営業日取得、夜間更新ジョブ
- 監査ログ（audit）
  - シグナル → 発注 → 約定のトレーサビリティを担保するテーブル群と初期化関数

---

## セットアップ手順

前提: Python 3.10+（typing における | ユニオン等を使用しています）

1. リポジトリをチェックアウト（開発時）
   - 例: git clone ...

2. 仮想環境を作成して有効化
   - Linux/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 基本的に以下が必要です:
     - duckdb
     - defusedxml
   - 例（pip）:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にローカルインストールする場合:
     ```
     pip install -e .
     ```
     （プロジェクトに setup/pyproject がある想定）

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成してください（`.env.example` 相当の項目）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - 自動読み込みはデフォルトで有効。無効化する場合は環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（サンプル）

以下は典型的な利用例（Python インタプリタやスクリプト内で実行）。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルベース DB を初期化
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（株価 / 財務 / カレンダー の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡して任意の日に実行可
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# sources を指定しない場合はデフォルト RSS ソースを使用
known_codes = {"7203", "6758", "6501"}  # 有効な銘柄コードセットを渡すと紐付けを行う
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

5) 監査ログスキーマ初期化（監査専用 DB を別で使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

6) マーケットカレンダー判定ユーティリティ例
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(prev_trading_day(conn, d))
```

7) 設定アクセス
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.duckdb_path)
```

---

## 主要 API（概要）

- kabusys.config
  - settings: 環境変数に基づく設定オブジェクト
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)
- kabusys.data.calendar_management
  - calendar_update_job(...)
  - is_trading_day(...)
  - next_trading_day(...)
  - prev_trading_day(...)
  - get_trading_days(...)
- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, ...)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token のために使用。

- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用トークン（必要な場合）。

- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH (任意)  
  SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)  
  実行環境: development | paper_trading | live（デフォルト: development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD  
  1 を設定すると `.env` 自動ロードを無効化します（テスト用途など）。

---

## ディレクトリ構成

（主要ファイル/モジュール）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

説明:
- data/: データ取得・ETL・スキーマ・品質チェック・ニュース収集などデータプラットフォームの中核処理
- strategy/: 戦略ロジック（拡張用）
- execution/: 実際の発注/ブローカー連携ロジック（拡張用）
- monitoring/: 監視・メトリクス（拡張用）

---

## 注意事項 / ベストプラクティス

- DuckDB 初期化は一度行えば OK。スキーマ変更時は注意してマイグレーションを行ってください。
- J-Quants のレート制限に従う設計ですが、運用時は API 実行の頻度やバックフィル設定に留意してください。
- ニュース収集は外部 RSS を扱います。defusedxml と SSRF 対策を組み込んでいますが、運用環境のネットワーク制限やプロキシ設定を検討してください。
- 本パッケージはデータ取得・保存・チェック基盤を提供します。実際の売買ロジック（資金管理、リスク管理、ブローカー送信）は strategy/ と execution/ に実装してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の副作用を切ると便利です。

---

## 開発・拡張

- 新しい ETL ジョブやデータソースを追加する場合は、data/ 以下にモジュールを追加し、schema.py に必要なテーブルを追加してください。
- strategy/ や execution/ のインターフェースはプロジェクトの方針に合わせて定義・拡張してください。
- ロギングは標準 logging を使用。必要に応じてハンドラやフォーマッタを設定してください。

---

ご不明点や README に追加したい使用例・運用手順があれば教えてください。README に追記します。