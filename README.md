# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なデータ基盤と一部ユーティリティを提供する Python パッケージです。主に以下を扱います。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）
- RSS フィードからのニュース収集と銘柄抽出
- DuckDB を用いたデータスキーマ定義・初期化・永続化
- ETL（差分更新・バックフィル）パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー操作（営業日判定、前後営業日取得）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上、API レート制限・リトライ・冪等性・Look-ahead バイアス防止などに配慮しています。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 四半期財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - トークン自動リフレッシュ、レートリミッター、リトライ（指数バックオフ）
- ETL パイプライン
  - run_daily_etl：カレンダー→価格→財務→品質チェックの一連処理
  - 差分更新（最終取得日からの差分取得）とバックフィル
- ニュース収集
  - RSS 取得（gzip 対応、XML の安全パース）
  - URL 正規化・トラッキングパラメータ除去・記事ID の生成（SHA-256）
  - SSRF 対策（スキーム検証、プライベートIPブロック、リダイレクト検査）
  - DuckDB へ冪等保存（INSERT ... ON CONFLICT / RETURNING）
  - 記事に含まれる銘柄コード抽出（既知コードとの照合）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - カレンダー差分更新ジョブ（calendar_update_job）
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで結果を返す（エラー/警告区分）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル群
  - UUID を用いたトレーサビリティ、タイムゾーンは UTC 固定

---

## セットアップ手順

前提:
- Python 3.10 以上（コードで `X | Y` 型ヒントを使用）
- pip が利用可能

1. リポジトリをクローン（またはソースをプロジェクトに配置）

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 必要なパッケージをインストール

   pip install duckdb defusedxml

   （実際のプロジェクトでは requirements.txt や pyproject.toml を用意して pip install -e . 等でインストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須は README 内で明示）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト: development）
   - LOG_LEVEL (任意) — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

   例 `.env`（プロジェクトルート）:

   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=changeme
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマの初期化

   Python REPL やスクリプトから次を実行して DB を初期化します（親ディレクトリが自動作成されます）:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ（audit）を別 DB で初期化する場合:

   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な例）

以下は簡単な利用例です。実運用ではログ・例外処理・スケジューリング等を追加してください。

- ETL（デイリー処理）を実行する

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 今日分を処理
  print(result.to_dict())

  引数で target_date, id_token, run_quality_checks などを指定可能です。

- 市場カレンダーの夜間更新ジョブを実行する

  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"Saved {saved} calendar records")

- ニュース収集（RSS）を実行して DB に保存する

  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # sources を渡さないと DEFAULT_RSS_SOURCES が使われる
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count}

- J-Quants の日足を直接取得して保存する（テスト用途）

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

- データ品質チェックを単体で実行する

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)

注意:
- jquants_client は API のレート制限を守るため内部でスロットリングを行います。大量取得時は実行時間に注意してください。
- fetch 系関数は id_token を引数で注入可能です（テスト容易性）。

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（パッケージルート: src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定読み込み（.env 自動ロード機能）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py               — RSS ニュース収集・前処理・保存
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL（差分更新・日次パイプライン）
    - calendar_management.py          — マーケットカレンダーのユーティリティと更新ジョブ
    - audit.py                        — 監査ログテーブル/初期化
    - quality.py                      — データ品質チェック
  - strategy/
    - __init__.py                      — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                      — 発注・約定関連（拡張ポイント）
  - monitoring/
    - __init__.py                      — 監視・メトリクス関連（拡張ポイント）

この構成は拡張を想定しており、strategy / execution / monitoring は将来的な戦略実装やブローカー連携を追加するための拠点となります。

---

## 設計上の注意点 / 運用メモ

- 環境変数:
  - settings モジュールは自動的にプロジェクトルートの `.env` / `.env.local` を読む仕組みです（CWD に依存せず、__file__ を基準にルート探索）。
  - 自動ロードを無効にしたいテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB 初期化:
  - init_schema は冪等で、既存テーブルはそのまま残ります。初回だけ実行すれば OK。
- 時刻/タイムゾーン:
  - 監査ログ（audit）では `SET TimeZone='UTC'` を実行して UTC 保存を前提としています。raw データ等も fetched_at を UTC で記録します。
- セキュリティ:
  - news_collector は SSRF 対策や XML の安全パース（defusedxml）、受信サイズ制限等を実装していますが、外部フィードを扱う場合は運用での監視や制限を推奨します。
- 品質チェック:
  - run_daily_etl は品質チェックでエラーを検出しても ETL を途中で止めない（Fail-Fast ではない）設計です。呼び出し側で結果を評価してアラートなどのハンドリングを行ってください。

---

## 追加情報 / 開発

- strategy、execution、monitoring パッケージは拡張ポイントです。戦略実装、ポートフォリオ最適化、ブローカー API 連携、ジョブスケジューラとの統合はこのレイヤで実装します。
- テスト:
  - settings は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して自動ロードを抑制し、環境を分離してテスト可能です。
  - news_collector のネットワークアクセスは `_urlopen` をモックしてテストできます。

---

必要に応じて README を拡張して、具体的な CI/CD、デプロイ手順、外部サービス（Slack 通知の実装例、kabu ステーション連携手順）、サンプル .env.example を追加できます。追加の要望があれば教えてください。