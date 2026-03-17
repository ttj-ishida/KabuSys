# KabuSys

日本株自動売買プラットフォーム（KabuSys）の軽量SDK / コアモジュール群です。  
データ収集（J-Quants API、RSS）、DuckDBベースのデータスキーマ、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアライブラリ群です。  
主に次の責務を持ちます。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー）
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB を用いた永続的なデータスキーマ（Raw / Processed / Feature / Execution）
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）

設計上のポイント:
- API レート制御、リトライ、トークン自動リフレッシュ、Look-ahead バイアス対策（fetched_at の記録）
- DuckDB への保存は冪等（ON CONFLICT）を採用
- RSS 周りは SSRF / XMLBomb 対策済み（defusedxml、受信サイズ制限、リダイレクト検査）

---

## 機能一覧

- config: 環境変数の読み込み・管理（.env 自動読み込み機能を含む）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行う
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- data.jquants_client: J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB に冪等保存
  - レートリミット制御、リトライ、401 時のトークン自動更新
- data.news_collector: RSS 収集と DuckDB 保存ロジック
  - URL 正規化・記事ID（SHA-256先頭32文字）生成・トラッキングパラメータ除去
  - SSRF対策・gzip制限・XMLパース保護・bulk insert（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁コード）
- data.schema: DuckDB の DDL 定義とスキーマ初期化（Raw / Processed / Feature / Execution）
- data.pipeline: ETL パイプライン（差分取得、backfill、品質チェック）
- data.calendar_management: 市場カレンダー管理（営業日判定、更新ジョブ）
- data.audit: 監査ログ（signal_events / order_requests / executions 等）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- execution / strategy / monitoring: プレースホルダ（拡張用パッケージ構造）

---

## 要件（推奨）

- Python >= 3.10（型ヒントに | 演算子を使用）
- 必要な主要パッケージ:
  - duckdb
  - defusedxml

（実行環境に応じて追加のパッケージが必要になる場合があります。setup.py / pyproject.toml に依存関係があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係をインストール

   （プロジェクトに pyproject.toml / requirements がある場合はそれに従ってください。ここでは最低限のパッケージを例示します）

   ```
   pip install duckdb defusedxml
   ```

   開発インストール:

   ```
   pip install -e .
   ```

4. 環境変数（.env）の準備

   ルートディレクトリに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。  
   主要な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（省略時 data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（省略時 development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   自動ロードを無効にするには:

   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（主要ワークフローの例）

以下は代表的な利用例です。DuckDB ファイルの初期化、ETL 実行、RSS 収集、カレンダー更新、監査スキーマ初期化など。

- DuckDB スキーマ初期化

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・接続
  ```

  - メモリ DB を使う場合: init_schema(":memory:")

- 日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 今日を対象に実行
  print(result.to_dict())
  ```

  - オプションで id_token を注入してテスト可能
  - backfill_days, spike_threshold 等のパラメータを指定可能

- RSS ニュース収集と保存

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出用の有効コード集合（例: 全上場銘柄の4桁コード）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー夜間更新ジョブ（calendar_update_job）

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査ログ（Audit）スキーマ初期化（監査専用DB または既存接続に追加）

  - 既存接続に監査テーブルを追加:

    ```python
    from kabusys.data.audit import init_audit_schema
    conn = init_schema("data/kabusys.duckdb")
    init_audit_schema(conn, transactional=True)
    ```

  - 監査専用 DB を作る:

    ```python
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    ```

- 品質チェック（単体実行）

  ```python
  from kabusys.data.quality import run_all_checks
  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.log_level など

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles) -> list[new_ids]
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.calendar_management
  - is_trading_day(conn, date)
  - next_trading_day(conn, date)
  - prev_trading_day(conn, date)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

---

## 注意事項 / 運用メモ

- J-Quants の API レート制限（120 req/min）に注意。jquants_client は内部で固定間隔のレート制御を行います。
- get_id_token はリフレッシュトークンを使って id_token を取得し、401 時は自動リフレッシュを行います。
- .env の自動読み込みはプロジェクトルート（.git か pyproject.toml を含む）で行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb。バックアップや移行はファイル単位で扱えます。
- RSS の受信サイズ上限（10MB）や Gzip 解凍後のサイズチェック、SSRF リダイレクト検査など安全対策が組み込まれています。
- run_daily_etl は品質チェックで見つかった問題を返しますが、重大度の扱い（ETL を止めるかどうか）は呼び出し側で決めてください（Fail-Fast ではなく全件収集思想）。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数 & 設定管理
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント（fetch/save）
    - news_collector.py       - RSS ニュース収集・保存
    - schema.py               - DuckDB スキーマ定義と初期化
    - pipeline.py             - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  - 市場カレンダー管理
    - audit.py                - 監査ログ用スキーマ初期化
    - quality.py              - データ品質チェック
  - strategy/
    - __init__.py             - 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py             - 発注・約定関連（拡張ポイント）
  - monitoring/
    - __init__.py             - 監視/メトリクス（拡張ポイント）

---

## 貢献 / 拡張ポイント

- strategy / execution / monitoring パッケージは拡張を想定したプレースホルダです。戦略ロジックやブローカー API 統合、運用監視を追加してください。
- ニュースの銘柄抽出ロジック（extract_stock_codes）は単純な4桁一致です。より高精度な NER や文脈解析を導入する余地があります。
- ETL のスケジューリングは外部の cron / Airflow / Prefect 等と組み合わせることを想定しています。

---

必要な箇所のサンプルコードや追加の説明が必要であれば、どの機能について詳細がほしいか教えてください。