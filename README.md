# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）

このリポジトリは、J‑Quants / JPX 等から日本株の時系列データ・財務データ・マーケットカレンダー・ニュースを取得し、DuckDB に保存してETL/品質チェック、監査ログ、ニュース収集、カレンダー管理を行うための共通ライブラリ群を提供します。戦略・発注・監視コンポーネントと連携して自動売買システムを構築することを想定しています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J‑Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得
  - レート制限 (120 req/min) と固定間隔スロットリング
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - フェッチ時刻（fetched_at）を UTC で記録して Look‑ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- ETL パイプライン
  - 差分取得（最終取得日に基づく差分更新）
  - バックフィル（後出し修正吸収のため過去 n 日を再取得）
  - 市場カレンダーの先読み取得
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集
  - RSS フィードから記事を収集して正規化保存（ID は正規化 URL の SHA‑256）
  - SSRF・XML Bomb・圧縮爆弾対策（defusedxml、受信サイズ上限、リダイレクト検証）
  - 銘柄コード抽出と news_symbols テーブルへの紐付け

- マーケットカレンダー管理
  - JPX カレンダーを差分更新する夜間ジョブ
  - 営業日判定・前後営業日取得・営業日リスト取得 API

- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比閾値）、将来日付・非営業日チェック
  - 問題は QualityIssue オブジェクト群で返却（severity に応じて上位で判断）

- 監査ログ（audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブル群（UUID ベース、冪等キー）
  - 発注要求のエラー/棄却も記録する設計

---

## 前提・依存

- Python 3.10+（型ヒントに union types 等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- （プロジェクト配布時の pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして、プロジェクトルートに移動します。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または開発中はパッケージを editable install:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的にロードされます（詳しくは config.py）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   代表的な環境変数（README 用サンプル）:

   ```
   # .env.example
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

5. DB スキーマ初期化（DuckDB）
   - データベースファイルを初期化してテーブル群を作成します（冪等）。
   - 例:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   ```

6. 監査ログ（Audit）テーブルの初期化（必要に応じて）
   - init_schema で作成された接続に対し audit の初期化を行います:

   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な API と例）

以下はライブラリの主要な使い方サンプルです。

- J‑Quants データ取得

```python
from kabusys.data import jquants_client as jq
# IDトークンを自動で取得（settings.jquants_refresh_token を使用）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- DuckDB に保存（冪等）

```python
import duckdb
from kabusys.data import jquants_client as jq
conn = duckdb.connect("data/kabusys.duckdb")
saved = jq.save_daily_quotes(conn, records)
```

- 日次 ETL 実行（カレンダー取得、株価、財務、品質チェックを順に実行）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得と保存）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出用）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

- カレンダー更新ジョブ（夜間バッチ想定）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

- 営業日判定ユーティリティ

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = get_connection("data/kabusys.duckdb")
print(is_trading_day(conn, date(2024,3,20)))
print(next_trading_day(conn, date(2024,3,20)))
```

- 品質チェック（個別または全件）

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API（kabuステーション）パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト時等）

config.py ではプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイルと階層（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J‑Quants API クライアント、保存ロジック
    - news_collector.py       # RSS → raw_news、news_symbols への収集
    - schema.py               # DuckDB スキーマ定義 & init_schema/get_connection
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # カレンダー更新と営業日ユーティリティ
    - audit.py                # 監査ログテーブル初期化
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py             # 戦略層（拡張用のエントリ）
  - execution/
    - __init__.py             # 発注/約定管理（拡張用のエントリ）
  - monitoring/
    - __init__.py             # 監視用モジュール（拡張）

データベーススキーマは次の層で設計されています:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions（監査用）

---

## 設計上の注意点・運用メモ

- J‑Quants API はレート制限（120 req/min）と再試行を考慮してあります。大量取得時は _MIN_INTERVAL_SEC によりスロットルされます。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）を保証していますが、外部からの直接挿入やスキーマ変更時は別途注意が必要です。
- ニュース収集は外部 URL を処理するため SSRF 対策（スキーム検証、プライベートIPブロック、リダイレクト検査）を行っています。
- ETL は Fail‑Fast ではなく、可能な限り処理を継続して問題点を報告する方針です（品質チェック結果は呼び出し元で判断してください）。
- 本ライブラリは「基盤部分」を提供します。実際の取引（発注）や Slack 通知、戦略実行、監視ルールは上位アプリケーション側で実装してください。

---

## 貢献・拡張

- strategy/、execution/、monitoring/ 以下にアプリ固有の実装や戦略を追加してください。
- 新しい外部データソースを追加する場合は data/ にモジュールを追加し、schema.py に必要なテーブルを追記してください。
- テストの際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、settings の自動ロードを無効化して環境を制御すると便利です。

---

この README はコードベースの主要機能・使い方を簡潔にまとめたものです。詳細な設計ドキュメント（DataPlatform.md 等）がある場合はそちらを参照してください。必要であれば README を英語版や運用手順（systemd / cron / Airflow 等での定期実行）を含めて拡張できます。