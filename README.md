# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやそれを支えるデータ基盤（ETL・DBスキーマ・品質チェック・監査ログ・ニュース収集など）を提供する Python パッケージです。主に以下を目的としています。

- J-Quants API から株価・財務・カレンダー等のマーケットデータを安全に取得・保存
- DuckDB を用いた3層（Raw / Processed / Feature）データスキーマの提供
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 発注・約定の監査ログスキーマ（トレーサビリティ保持）
- 各所での冪等保存、リトライ、レートリミットや SSRF 対策などの安全設計

---

## 主な機能一覧

- 環境設定読み込み
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須値チェックとラッパ（kabusys.config.settings）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務、JPX カレンダーの取得
  - レートリミット遵守、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（ON CONFLICT …）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（DB の最終日から新規のみ取得）、バックフィル、品質チェック連携
  - 日次実行エントリ（run_daily_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、XML の安全パース（defusedxml）、URL 正規化・トラッキング除去
  - 記事ID を SHA-256 ハッシュで冪等化、DuckDB へのバルク挿入・銘柄紐付け
  - SSRF 対策（スキーム検証、プライベートIP 判定、リダイレクト検査）、レスポンスサイズ制限
- データスキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - インデックス、初期化ユーティリティ（init_schema）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間カレンダー更新ジョブ（calendar_update_job）
- 品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク（前日比）・日付不整合チェック。QualityIssue を返す
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用スキーマと初期化

---

## 動作要件

- Python 3.10 以上（型ヒントで | 演算子を使用）
- 主な依存パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン（例）:

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）:

   pip install duckdb defusedxml

   ※ 実際はプロジェクトの pyproject.toml / requirements.txt を参照してインストールしてください。

4. 環境変数を設定（.env をプロジェクトルートに置くのが推奨）

   - 必須（kabusys.config.Settings で require されるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

   - オプション:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live。デフォルト development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト INFO)

   例（.env）:

   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

   自動 .env ロードについて:
   - プロジェクトルート（.git または pyproject.toml を起点）で .env / .env.local を自動読み込みします。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

5. DuckDB スキーマ初期化（Python 実行例）:

   >>> from kabusys.data import schema
   >>> conn = schema.init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を使う場合:

   >>> from kabusys.data import audit
   >>> conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（基本例）

以下は主要な機能の使い方サンプルです。実際はアプリケーションコード側で例外処理やログ出力を行ってください。

- DuckDB スキーマ初期化:

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（当日分、品質チェックあり）:

  from kabusys.data import pipeline
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  戻り値は pipeline.ETLResult。fetched / saved 数、品質チェック結果、エラーなどを持つ。

- ニュース収集を実行（RSS から raw_news に保存、既知銘柄で紐付け）:

  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数, ...}

- 市場カレンダー夜間更新ジョブ:

  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)

- J-Quants から株価を取得して保存（直接呼び出す場合）:

  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved_count = jq.save_daily_quotes(conn, records)

- 品質チェックを個別に実行:

  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

---

## 環境変数（まとめ）

必須:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意／デフォルトあり:

- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効にする場合に "1" を設定

---

## 注意点 / 設計上のポイント

- J-Quants クライアントは 120 req/min のレート制限を守るように実装されています。大量取得時は制限を超えないよう注意してください。
- 各保存関数は冪等（ON CONFLICT で更新／スキップ）を基本としています。外部から DB を操作する場合は整合性を維持してください。
- news_collector は SSRF 対策や gzip 解凍後サイズチェックなどを行い、安全性に配慮しています。
- audit.init_audit_schema() はタイムゾーンを UTC に固定します（SET TimeZone='UTC' を実行）。
- TypeHints による挙動から Python 3.10 以降を想定しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存）
      - news_collector.py      -- RSS ニュース収集・保存・銘柄抽出
      - schema.py              -- DuckDB スキーマ定義・初期化
      - pipeline.py            -- ETL パイプライン（差分更新・日次ETL）
      - calendar_management.py -- マーケットカレンダー管理
      - audit.py               -- 監査ログスキーマ・初期化
      - quality.py             -- データ品質チェック
    - strategy/
      - __init__.py            -- 戦略層の入口（未実装: 実装を追加）
    - execution/
      - __init__.py            -- 発注 / 執行関連（未実装: 実装を追加）
    - monitoring/
      - __init__.py            -- 監視・メトリクス（未実装: 実装を追加）
- pyproject.toml (プロジェクトルートに存在する想定)
- .env / .env.local (プロジェクトルートに配置して環境変数を設定)

---

## 開発時のヒント

- テストや CI で自動 .env 読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- news_collector._urlopen はテスト用にモック可能です（外部ネットワーク依存を切るため）。
- jquants_client のトークン取得は get_id_token() を呼び、内部で自動リフレッシュを行います。テスト時は id_token 引数を注入すると再現性が向上します。
- DuckDB の ":memory:" を使えばインメモリ DB で素早く動作確認できます（schema.init_schema(":memory:")）。

---

この README はコードベースの公開・運用のための最小限の説明を目的としています。詳細な設計資料（DataPlatform.md、API仕様、運用ガイドなど）があれば併せて参照してください。追加のチュートリアルやコード例が必要であればお知らせください。