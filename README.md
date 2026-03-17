# KabuSys

日本株向け自動売買インフラ／データプラットフォームライブラリ（KabuSys）の README。  
このリポジトリはデータ収集・ETL・品質チェック・監査ログなど、自動売買システムの基盤機能を提供します。

> 現状の実装は主に data パッケージに機能実装が集中しています（J-Quants クライアント、RSS ニュース収集、DuckDB スキーマ/ETL/品質チェック、カレンダー管理、監査ログなど）。strategy、execution、monitoring パッケージは骨組みを用意しています。

---

## 主な機能（概要）

- J-Quants API クライアント（認証、ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - 取得日時（fetched_at）を UTC で保持し Look-ahead Bias を防止
  - DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）

- ニュース収集モジュール（RSS）
  - RSS フィードを取得して正規化・前処理し raw_news テーブルへ保存
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip サイズ制限、XML の安全パース（defusedxml）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で冪等性確保
  - 記事と銘柄コードの紐付け（ニュース内の 4 桁銘柄コード抽出）

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、監査ログ用スキーマ初期化機能

- ETL パイプライン
  - 日次 ETL（run_daily_etl）：市場カレンダー取得 → 株価差分取得（バックフィル）→ 財務データ取得 → 品質チェック
  - 差分更新ロジック（最終取得日基準、backfill）、品質チェックの実行

- データ品質チェック
  - 欠損（OHLC 欠損）、スパイク（前日比閾値）、重複、日付不整合（未来日付／非営業日のデータ）を検出
  - QualityIssue オブジェクトで問題を集約

- マーケットカレンダー管理
  - 営業日/半日/SQ判定、前後営業日の取得、範囲の営業日列挙、夜間カレンダー更新ジョブ

- 監査ログ（audit）
  - シグナル → 発注要求 → 約定のトレーサビリティを保持するテーブル群（UUID による連鎖）
  - 監査 DB 初期化（UTC タイムゾーン固定）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（Union 型記法などを使用）
- 主要依存:
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）を利用

（実際のパッケージの requirements.txt / pyproject.toml をプロジェクトに合わせて用意してください）

---

## 環境変数 / 設定

このプロジェクトは .env/.env.local（プロジェクトルート）および OS 環境変数から設定を読み込みます。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。自動ロードは .git または pyproject.toml を基準にプロジェクトルートを探索します。

必須環境変数（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

任意（デフォルトあり）
- KABUSYS_ENV : 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）。デフォルト: INFO
- DUCKDB_PATH : DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH : SQLite パス（モニタリング用）。デフォルト: data/monitoring.db

.env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存関係のインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml/requirements.txt がある場合はそれに従う）

4. 環境変数の設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で必須キーを設定

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ自動作成
     conn.close()
     ```
   - 監査ログ専用 DB を使う場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     audit_conn.close()
     ```

---

## 使い方（主要な操作例）

以下はライブラリ API を直接使う例です。運用時はラッパースクリプトやジョブスケジューラ（cron、systemd timer、Airflow 等）から呼び出してください。

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```python
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  # スキーマ初期化（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # 日次ETL 実行（target_date を指定しなければ本日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  conn.close()
  ```

- 個別 ETL（株価のみ・範囲指定）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.data.pipeline import run_prices_etl

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 17))
  ```

- RSS ニュース収集ジョブ
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄抽出で使う有効コードの集合（例: 事前に取得した上場銘柄コード）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  conn.close()
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- J-Quants トークン取得 / API 呼び出し
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックを個別実行
  ```python
  from kabusys.data.quality import run_all_checks
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

ログ出力は settings.log_level の設定を参照します。必要に応じて logging.basicConfig などでルートロガーを設定してください。

---

## 自動環境変数ロードの挙動

- 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準として `.env` と `.env.local` を自動で読み込みます。
- 読み込み順序・優先度:
  - OS 環境変数 > .env.local > .env
  - .env.local は上書き（override=True）で読み込まれます
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

.env のパースルールはシェル形式に準拠し、'export KEY=val' 形式もサポートします。クォートや # コメントの扱いは実装に基づき適切に処理されます。

---

## ディレクトリ構成

主要なファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py          -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - pipeline.py                -- ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py     -- マーケットカレンダー管理と夜間更新ジョブ
    - audit.py                   -- 監査ログ（シグナル→発注→約定トレーサビリティ）
    - quality.py                 -- データ品質チェック
  - strategy/
    - __init__.py                -- 戦略層（拡張用）
  - execution/
    - __init__.py                -- 発注実行層（拡張用）
  - monitoring/
    - __init__.py                -- 監視・アラート（拡張用）

---

## 運用上の注意点 / 設計ポリシー（抜粋）

- API レート制限を守るため固定間隔の RateLimiter を使っています（J-Quants: 120 req/min）。
- ネットワーク障害や一時的エラーに対しては指数バックオフを伴うリトライ実装があります（特定ステータスコードでリトライ）。
- 401 は自動でリフレッシュトークンにより ID トークンを更新して一度のみ再試行します。
- DuckDB 側は可能な限り冪等な INSERT（ON CONFLICT）を用いて再実行耐性を高めています。
- ニュース RSS は SSRF、XML Bomb、巨大レスポンス等の攻撃を想定した対策を実装しています。
- 監査ログはタイムゾーンを UTC に固定してトレーサビリティを保証します。

---

## 参考・今後の拡張

- strategy、execution、monitoring パッケージはフレームワーク用の土台を提供しています。実際の取引戦略やブローカー連携はここに実装してください。
- 実運用ではジョブスケジューラ（cron / systemd / Airflow / Prefect 等）で ETL とカレンダー更新、ニュース収集、発注ワーカーを定期実行することを想定しています。
- セキュリティに関わる設定（トークン、パスワード）は CI/CD・運用環境のシークレットストアで管理することを推奨します。

---

必要であれば README に含める具体的なサンプル .env.example、Dockerfile、systemd/cron の設定例、または CLI ラッパーのサンプルを追加します。どれを追加しますか？