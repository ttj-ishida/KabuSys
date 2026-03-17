# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB スキーマ定義、監査ログ用スキーマ等の基盤機能を提供します。

## 概要
KabuSys は以下を主目的とするライブラリ群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得・保存
- RSS からニュースを収集し記事と銘柄コードを紐付け
- DuckDB に対するスキーマ定義・初期化機能
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ

設計方針として、API レート制限とリトライ、冪等性（ON CONFLICT）、Look-ahead バイアス防止のための fetched_at 記録、SSRF 対策などを考慮しています。

---

## 主な機能一覧
- J-Quants クライアント（`kabusys.data.jquants_client`）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークン→IDトークン取得、401 自動リフレッシュ対応）
  - HTTP レート制御（120 req/min）、指数バックオフリトライ、ページネーション対応
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- ニュース収集（`kabusys.data.news_collector`）
  - RSS 取得（gzip 対応、XML の安全パース、SSRF / private address チェック）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256 頭32文字）
  - raw_news 保存、news_symbols（記事⇄銘柄）紐付け
- DuckDB スキーマ定義（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義・初期化
  - 初期化関数: init_schema(db_path) / get_connection(db_path)
- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL: run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェック統合（quality モジュールと連携）
- データ品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
  - QualityIssue オブジェクトで検出結果を返却
- カレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定 / 前後の営業日取得 / カレンダー夜間更新ジョブ
- 監査ログ（`kabusys.data.audit`）
  - signal_events / order_requests / executions テーブルの初期化（init_audit_schema / init_audit_db）
- 設定管理（`kabusys.config`）
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で各種設定にアクセス

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントにより）
- DuckDB が利用可能（pip で duckdb をインストール）

1. リポジトリを取得（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. パッケージのインストール（開発環境例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .         # または必要な依存を個別にインストール
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として設定を置けます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（少なくともテスト・稼働で必要なもの）:
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（kabu API パスワード）
     - SLACK_BOT_TOKEN（Slack ボットトークン）
     - SLACK_CHANNEL_ID（通知先チャンネル ID）
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
     - DUCKDB_PATH（例: data/kabusys.duckdb）デフォルト: data/kabusys.duckdb
     - SQLITE_PATH（監視 DB など）デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   SLACK_BOT_TOKEN=zzz
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイル DB。":memory:" も可
   # 監査テーブルを追加する場合
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

---

## 使い方（主要なコード例）

- 設定を取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)      # Path オブジェクト
  print(settings.is_live)          # bool
  ```

- J-Quants からデータ取得（トークンは settings から自動取得する）
  ```python
  from kabusys.data import jquants_client as jq
  # 日足取得（期間指定）
  from datetime import date
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,31))
  ```

- ETL 日次ジョブの実行
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済み想定
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # 既定の RSS ソースから収集し保存
  result = news_collector.run_news_collection(conn)
  print(result)  # {source_name: saved_count}
  ```

- DuckDB スキーマ初期化（再掲）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema(":memory:")  # インメモリ DB で素早く試す
  ```

- 監査用 DB 初期化（監査専用ファイルを用意する場合）
  ```python
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/audit.duckdb")
  ```

ログや例外は各モジュールで詳細に出力します。運用時は LOG_LEVEL を適切に設定してください。

---

## ディレクトリ構成（主なファイル）
プロジェクトの主要ファイルとモジュールは以下の通りです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数 / .env 読み込みと settings
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得・保存・認証）
    - news_collector.py            : RSS 収集・前処理・DB 保存
    - schema.py                    : DuckDB スキーマ定義・初期化
    - pipeline.py                  : ETL パイプライン（差分取得・品質チェック統合）
    - calendar_management.py       : カレンダー更新・営業日判定
    - audit.py                     : 監査ログスキーマ初期化（signal/order/execution）
    - quality.py                   : データ品質チェック
  - strategy/
    - __init__.py                  : 戦略関連の入り口（実装は別途）
  - execution/
    - __init__.py                  : 発注・実行関連（実装は別途）
  - monitoring/
    - __init__.py                  : 監視 / アラート関連（実装は別途）

---

## 運用・注意点
- J-Quants API のレート制限（120 req/min）をモジュール内で遵守する実装がありますが、外部から大量呼び出しする場合は注意してください。
- get_id_token はリフレッシュトークンを使って ID トークンを取得します。401 発生時は自動リフレッシュ（1 回）を行います。
- DuckDB の INSERT は多くが ON CONFLICT を使った冪等設計です。初回ロード・バックフィルで重複がある場合でも上書きやスキップにより整合性を保ちます。
- news_collector は RSS の XML を defusedxml でパースし、SSRF（プライベートアドレス・不正スキーム）対策や受信サイズ上限を設けています。
- .env 自動読み込みはプロジェクトルートを基準に行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます。
- 型注釈や設計文書はコード内コメントに豊富にあります。詳細は該当ファイルを参照してください。

---

## 参考（代表的な API）
- data.schema.init_schema(db_path) → DuckDB 接続（スキーマ作成）
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.news_collector.fetch_rss(url, source)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.pipeline.run_daily_etl(conn, target_date=None, ...)

---

必要に応じて README を拡張して、CI/デプロイ手順、運用 Runbook、具体的な戦略／実行モジュールの実装例を追加してください。質問や補足があれば教えてください。