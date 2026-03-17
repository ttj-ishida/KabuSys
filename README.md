# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）。

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・監査ログまでをカバーするデータ基盤および自動売買システムのコアライブラリです。  
主に以下を目的としています。

- J-Quants API からの市場データ（株価日足、財務指標、JPX カレンダー）取得と DuckDB への保存（冪等性確保）
- RSS を使ったニュース収集と記事の正規化・銘柄紐付け（SSRF / XML 攻撃対策を実装）
- ETL パイプライン（差分取得・バックフィル・品質チェック）を簡単に実行可能
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ定義
- 市場カレンダーの管理（営業日の判定、次/前営業日の計算）

設計上の特徴として、API レート制御・堅牢なリトライ・レスポンスの安全処理・DuckDB に対する冪等保存やトランザクションを意識した実装を行っています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）と指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/news_collector.py
  - RSS フィード取得、XML の安全パース（defusedxml）、URL 正規化、記事ID の SHA-256 ハッシュ化
  - SSRF 防止（スキーム検証、リダイレクト先の内部アドレス検出）、受信サイズ制限、gzip 対応
  - DuckDB へ冪等保存（INSERT ... RETURNING）・銘柄コード抽出（4桁コード）
- data/schema.py / data/audit.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化ユーティリティ（init_schema, init_audit_db）
- data/pipeline.py
  - 日次 ETL パイプライン（差分取得、backfill、品質チェック、ログ化）
  - run_daily_etl により、カレンダー→価格→財務→品質チェックの一連処理を実行
- data/calendar_management.py
  - JPX カレンダー管理、営業日判定、next/prev_trading_day、期間内営業日取得
- data/quality.py
  - 欠損検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue 型で問題を集約（error / warning）

その他、config.py により環境変数ベースの設定管理（.env 自動読み込み機能）を提供します。

---

## 要求環境（推奨）

- Python 3.9+（コードは型注釈と標準ライブラリを前提）
- 必須 Python パッケージ:
  - duckdb
  - defusedxml

（その他は標準ライブラリで実装されています。プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください。）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` によって行います。自動読み込みは `kabusys.config` により .env をプロジェクトルートから検索して行われます（.git または pyproject.toml を基準にルートを特定）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (development / paper_trading / live)（任意、デフォルト: development）
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)（任意）

settings オブジェクトからこれらを参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをチェックアウトし、Python 仮想環境を作成・有効化:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール:

   ```bash
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があれば `pip install -e .` や `pip install -r requirements.txt` を実行してください。）

3. 環境変数の設定:
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定してください。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. データベーススキーマの初期化（DuckDB の作成）:

   Python から直接実行する例:

   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

   これにより parent ディレクトリがなければ自動作成され、必要なテーブルとインデックスが作られます。

---

## 使い方（主要な API と実行例）

ここではよく使う操作のサンプルを示します。実際はアプリ側でこれら関数を呼び出して運用します。

- DuckDB 初期化（再掲）:

  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema('data/kabusys.duckdb')
  ```

- 日次 ETL 実行（run_daily_etl）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  run_daily_etl は市場カレンダー→株価→財務→品質チェックを順に実行し、ETLResult を返します。

- RSS ニュース収集ジョブ（全ソース）:

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  # known_codes を与えると記事から銘柄コード抽出と紐付けを行います
  known_codes = {'7203', '6758', '9984'}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- J-Quants の ID トークン取得（内部的に run_daily_etl 等で使われる）:

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して POST で取得
  ```

- RSS 単体取得（fetch_rss）:

  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- jquants_client は API レート制限（120 req/min）を厳守するため内部でスロットリングしています。
- ネットワークエラーや 408/429/5xx に対する指数バックオフのリトライを行います。401 は自動でリフレッシュを試みます（1 回）。
- news_collector は SSRF・XML 攻撃・Gzip bomb 対策等の安全対策が組み込まれています。

---

## 実運用上のヒント

- テストや CI で環境変数自動ロードを避けたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（kabusys.config の .env 自動ロードを無効化します）。
- DuckDB はローカルファイル（デフォルト data/kabusys.duckdb）を想定しています。メモリ DB を使う場合は db_path に `":memory:"` を渡せます（テスト用）。
- run_daily_etl の backfill_days や spike_threshold は引数で調整可能です。
- 監査ログは data.audit モジュールで別 DB として初期化できます（init_audit_db）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数・設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得 + 保存）
      - news_collector.py          — RSS ニュース収集・前処理・保存
      - schema.py                  — DuckDB スキーマ定義・初期化
      - pipeline.py                — ETL パイプライン（run_daily_etl など）
      - calendar_management.py     — マーケットカレンダー管理
      - audit.py                   — 監査ログスキーマ / 初期化
      - quality.py                 — データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

※ strategy / execution / monitoring パッケージは骨組みを提供しており、各プロジェクト固有の戦略ロジックやブローカー連携、監視機構を実装して拡張します。

---

## ライセンス / 貢献

この README にはライセンス情報を含めていません。実際のリポジトリでは LICENSE ファイル、および貢献ガイド（CONTRIBUTING.md）を用意してください。

バグ報告、機能要望、PR は歓迎します。コードの設計方針（冪等性、セキュリティ、トレーサビリティ）を尊重した実装をお願いします。

---

必要であれば、README にサンプル .env.example、requirements.txt、運用 runbook（cron / Airflow ジョブの例）や、監視・アラート（Slack 通知連携）についての記述も追加できます。どの情報を詳しく追記したいか教えてください。