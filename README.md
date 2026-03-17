# KabuSys

日本株向けの自動売買データプラットフォームおよびETLライブラリです。  
J-Quants API からの市場データ取得、DuckDB への冪等保存、データ品質チェック、RSS ベースのニュース収集、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 主要な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）に従う RateLimiter 実装
  - 再試行（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ対応
  - データ取得時刻（fetched_at）を UTC で記録（Look-ahead bias 対策）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - インデックス、外部キー制約を含む冪等的なテーブル作成（init_schema）

- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル（後出し修正吸収）
  - 市場カレンダー先読み（lookahead）を考慮した営業日調整
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行し結果を返す

- ニュース収集（RSS）
  - RSS フィードの取得・XML パース（defusedxml による安全パース）
  - トラッキングパラメータ除去・URL 正規化、記事 ID は正規化URLの SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証・プライベートアドレス拒否）、レスポンスサイズ上限
  - DuckDB に対するバルクかつ冪等的な保存（INSERT ... RETURNING）

- マーケットカレンダー管理（営業日判定・next/prev/trading days）
- 監査ログ（signal → order_request → executions の追跡テーブル群）
- 設定管理モジュール（.env 自動読み込み、環境変数アクセス via settings）

---

## 動作要件 / 依存関係

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime, hashlib, ipaddress, socket 等）

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を記載してください）

---

## セットアップ手順

1. リポジトリをクローン／取得する

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用）pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただしテスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
     - DUCKDB_PATH=data/kabusys.duckdb  （省略時のデフォルト）
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

   - `.env` の自動ロードは OS 環境変数を上書きしない（.env.local は上書き可）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（サンプル）

以下は基本的な利用例です。適宜ログ設定やエラーハンドリングを追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
# ディスク上のファイル
conn = schema.init_schema("data/kabusys.duckdb")
# インメモリ
# conn = schema.init_schema(":memory:")
```

2) 監査ログ専用テーブル初期化（既存接続に追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
# もしくは新しい audit DB を作る場合:
# audit_conn = audit.init_audit_db("data/audit.duckdb")
```

3) J-Quants からの ETL（デイリー実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl, get_last_price_date
# conn は init_schema で作成済みの接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETL の詳細結果
```

個別に実行する場合:
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

4) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コードの集合（"7203","6758",...）を渡すと紐付けを行う
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count, ...}
```

5) J-Quants API クライアントの直接利用例
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token 経由で取得される（.env の JQUANTS_REFRESH_TOKEN を参照）
daily = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存（DuckDB conn）
jq.save_daily_quotes(conn, daily)
```

6) 設定取得（settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## よく使う API の説明（概観）

- kabusys.config
  - settings: 環境変数からアプリ設定を取得するオブジェクト
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可）

- kabusys.data.schema
  - init_schema(db_path): DuckDB の全スキーマ（Raw, Processed, Feature, Execution）を作成し接続を返す
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) / save_financial_statements / save_market_calendar

  内部でレート制御（120 req/min）・再試行・401 自動リフレッシュなどを行います。

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...): 日次 ETL（カレンダー取得 → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) → list[NewsArticle]
  - save_raw_news(conn, articles) → list[str]（新規挿入された記事ID一覧）
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None) → {source: inserted_count}

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency
  - QualityIssue 型で問題の詳細を返す（severity: error/warning）

- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path): 監査ログ用テーブル（signal_events, order_requests, executions）を初期化

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なファイル配置（src ベース）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                  — DuckDB スキーマ定義・初期化
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン
    - news_collector.py          — RSS ニュース収集・保存ロジック
    - calendar_management.py     — マーケットカレンダー管理・バッチ
    - audit.py                   — 監査ログ（発注/約定のトレーサビリティ）
    - quality.py                 — データ品質チェック
  - strategy/                     — 戦略関連（未実装のエントリポイント）
  - execution/                    — 発注 / 実行関連（未実装のエントリポイント）
  - monitoring/                   — 監視（未実装のエントリポイント）

（この README は現状のソースに基づく概要です。strategy/、execution/、monitoring/ はパッケージ空ディレクトリとして定義されています）

---

## セキュリティ・設計上の注意点 / 実装ノート

- J-Quants API のレート制限（120 req/min）を守るため固定間隔のスロットリングを使用。
- ネットワーク障害や 429/408/5xx に対して指数バックオフで再試行（最大3回）。
- 401 Unauthorized 受信時はリフレッシュトークンから id_token を再取得して 1 回リトライする。
- ニュース収集は SSRF 対策を施し、リダイレクト先のスキームやホストの検証、レスポンスサイズ上限（10 MB）を設けています。
- データ保存は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を重視。
- すべての監査用 TIMESTAMP は UTC を想定して保存する設計。

---

## 貢献 / 開発

- 新しい機能追加やバグ修正は Pull Request を送ってください。
- 大きな設計変更を行う場合は事前に Issue で提案してください。

---

以上です。必要があれば README に含める実行スクリプト例、CI 設定、pyproject.toml のサンプルやより詳細なデータベース/テーブル仕様（DataPlatform.md 等の参照）を追記します。どの部分を詳しく書き足しましょうか？