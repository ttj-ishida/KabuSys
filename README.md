# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、J-Quants API などから市場データを取得・ETL・検査し、戦略・発注・監査までを支援するコンポーネント群を提供します。主にデータレイヤ（Raw / Processed / Feature / Execution）および関連ユーティリティに重点を置いた設計です。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・市場カレンダーを安全かつ冪等に取得・格納する
- RSS フィードからニュースを収集して記事・銘柄紐付けを行う
- DuckDB に対するスキーマ定義・初期化を提供する
- ETL（差分取得・バックフィル・品質チェック）パイプラインを実行する
- マーケットカレンダーの判定・探索ロジック、監査ログスキーマを提供する
- 品質チェック（欠損・スパイク・重複・日付不整合）を行う

設計上の特徴：
- API レート制御（固定間隔スロットリング）およびリトライ（指数バックオフ）
- 取得時刻（fetched_at）の記録による Look-ahead Bias 対策
- DuckDB への保存は冪等（ON CONFLICT ...）で実装
- RSS収集は SSRF / XML Bomb / 大量レスポンス対策を実装

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local / OS 環境変数）
- J-Quants API クライアント
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
- ニュース収集（RSS）
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化・トラッキングパラメータ除去・つながりのある銘柄抽出
- DuckDB スキーマ管理
  - init_schema(), get_connection()
- ETL パイプライン
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
  - 差分取得・バックフィル、品質チェック統合
- マーケットカレンダー管理
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), is_sq_day(), calendar_update_job()
- 監査ログスキーマ（信頼性の高いトレーサビリティ）
  - init_audit_schema(), init_audit_db()
- データ品質チェック
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()

（strategy/execution/monitoring パッケージの土台は用意されていますが、実装は別途拡張します）

---

## セットアップ手順

前提：
- Python 3.9+（typing などに基づく記述があるため）
- pip が使用可能

1. リポジトリをクローン／展開します。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール  
   代表的な依存例（requirements.txt がないためプロジェクトに応じて調整してください）:
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

4. 環境変数を設定する  
   必須:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN — Slack 通知用トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   任意（デフォルト値あり）:
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) (default: development)
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

   .env 自動ロードの仕様:
   - プロジェクトルートを .git または pyproject.toml から検出し、優先順は
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. DuckDB スキーマの初期化例:
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. 監査ログスキーマの初期化（任意）:
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

---

## 使い方（主要なユースケース）

以下にライブラリを使った代表的なサンプルを示します。

1) DuckDB を初期化して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（ファイルがなければ作成）
conn = init_schema("data/kabusys.duckdb")

# 当日分の ETL を実行（id_token を渡さない場合はモジュール内のキャッシュ/自動取得を使用）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

3) J-Quants の ID トークンを明示的に取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用して取得
```

4) マーケットカレンダー API を使った判定
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 3, 20)))
print(next_trading_day(conn, date(2026, 3, 20)))
```

5) 監査 DB を分離して初期化する
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 実装上の注意点 / 設計ポリシー（要点）

- API 呼び出しは RateLimiter（120 req/min）と最大3回のリトライを備えています。401 はトークンリフレッシュを行い1回だけリトライされます。
- データ保存は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）しています。既存データの上書きルールは各 save_* 関数の SQL に従います。
- ニュース収集は SSRF の防止、XML パーサーの安全化（defusedxml）、最大受信バイト数制限などセキュリティ対策を実装しています。
- 品質チェックは Fail-Fast を避け、複数の問題を収集して呼び出し元が判断できるようにしています。
- すべてのタイムスタンプは原則 UTC を利用（監査ログは明示的に TimeZone='UTC' を設定）。

---

## ディレクトリ構成

以下は主要なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / .env のロードと Settings
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化 (init_schema, get_connection)
    - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py — マーケットカレンダー管理・判定ユーティリティ
    - audit.py — 監査ログスキーマ（signal / order_request / executions）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py — 戦略層のためのパッケージプレースホルダ（拡張用）
  - execution/
    - __init__.py — 発注 / 約定層のプレースホルダ（拡張用）
  - monitoring/
    - __init__.py — 監視用コンポーネントのプレースホルダ（拡張用）

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

.env の読み込み挙動:
- プロジェクトルートを .git または pyproject.toml で検出し、そのルート下の .env と .env.local を順に読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ロギング / デバッグ

- 各モジュールは Python の logging を用いて情報・警告・エラーを出力します。LOG_LEVEL を環境変数で設定してください。
- ETL 実行やニュース収集は詳細ログを記録するため、運用時にはログの出力先・ローテーション等を別途設定してください。

---

## テスト / 開発向けヒント

- .env 自動ロードを無効にしてテスト用の環境変数を注入すると安全です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- jquants_client の _urlopen や news_collector._urlopen はモック差し替え可能に設計されているため、ネットワーク呼び出しを置換してユニットテストが書きやすくなっています。
- DuckDB の ":memory:" を使えばインメモリ DB での単体テストが可能です（init_schema(":memory:")）。

---

この README はコードベースの現状実装に基づいてまとめています。strategy / execution / monitoring の具象実装や外部連携（証券会社 API の送受信等）はプロジェクトの拡張によって追加してください。質問やサンプルコードの追加が必要なら教えてください。