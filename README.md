# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）です。  
データ取得（J‑Quants）、ETLパイプライン、DuckDBスキーマ、ニュース収集、監査ログなど、アルゴリズム取引に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を目的としたライブラリ群です。

- J‑Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた 3 層データスキーマ（Raw / Processed / Feature）と実行層および監査ログテーブルの初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け（SSRF 対策・サイズ制限・XML 防護）
- マーケットカレンダー管理（営業日判定 / next/prev / 範囲取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計上の特徴として、Idempotence（重複排除）を考慮した DB 操作、Look‑ahead Bias 回避のための fetched_at 記録、外部 API のレート・エラー制御、セキュリティ対策（XML の defusedxml、SSRF防護、受信サイズ制限）を備えます。

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_* 関数で DuckDB に冪等保存（ON CONFLICT）
  - レート制御（120 req/min）、リトライ、401 自動リフレッシュ
- data/schema.py
  - DuckDB の全テーブル定義と init_schema(db_path)
  - インデックス、外部キーを考慮した初期化
- data/pipeline.py
  - run_daily_etl(): 日次 ETL の統合エントリポイント（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル、品質チェック呼び出し
- data/news_collector.py
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化（トラッキングパラメータ除去）、記事ID = SHA256(正規化URL)[:32]
  - SSRF/内部アドレスチェック、gzip サイズ制限、defusedxml による XML 防護
- data/calendar_management.py
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- data/audit.py
  - 監査ログ（signal_events, order_requests, executions）用DDL と初期化（init_audit_db / init_audit_schema）
- data/quality.py
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()

- config.py
  - 環境変数管理（.env 自動読み込み。プロジェクトルートを .git / pyproject.toml で探索）
  - Settings クラスにより必要環境変数をプロパティで提供

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（実行環境に応じて追加パッケージが必要になる場合があります。プロジェクト用の requirements.txt / pyproject.toml を用意してください。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows (PowerShell など)

2. 依存パッケージをインストールします（例）:

   pip install duckdb defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を参照してください。

3. 環境変数を設定します（.env 推奨）。

   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動的に読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（config.Settings で参照されるもの）:

   - JQUANTS_REFRESH_TOKEN  — J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API パスワード
   - SLACK_BOT_TOKEN        — Slack Bot Token（通知などに使用する場合）
   - SLACK_CHANNEL_ID       — Slack Channel ID

   任意（デフォルトあり）:

   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（1）

   .env の例:

   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化

   Python からスキーマを初期化します（初回のみ）:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を別ファイルで初期化する場合:

   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主な API 例）

以下はライブラリを Python から利用する簡単な例です。

- DuckDB 初期化（schema を作成して接続を取得）:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- J‑Quants トークン取得 / データ取得:

  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  daily = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, daily)

- 日次 ETL 実行（統合）:

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  print(result.to_dict())

- ニュース収集ジョブ:

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  # results は {source_name: 新規保存件数}

- カレンダー操作例:

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_td = is_trading_day(conn, date(2024,1,4))
  next_td = next_trading_day(conn, date(2024,1,4))

- 品質チェック単体実行:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

---

## 動作上の注意点 / 設計上のポイント

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` を読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env（.env.local が .env を上書き）
  - 自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J‑Quants クライアント
  - レート上限 120 req/min に合わせて内部でスロットリングを行います。
  - 408/429/5xx に対して指数バックオフ付きで最大 3 回リトライ。
  - 401 受信時はリフレッシュトークンを使って ID トークンを更新し、1 回リトライします。

- ニュース収集のセキュリティ
  - defusedxml を使って XML Bomb 等を防止しています。
  - リダイレクト先のホストがプライベートアドレスの場合は拒否（SSRF 対策）。
  - レスポンスサイズは最大 10MB に制限し、gzip 解凍後もチェックします。

- DuckDB スキーマ
  - 多数のテーブルとインデックスを定義しています。init_schema は冪等（既存テーブルはスキップ）です。
  - 監査ログ（audit）機能は別途 init_audit_schema / init_audit_db で初期化できます。

- 日付・営業日ロジック
  - market_calendar が存在すれば DB の値を優先。未登録日は曜日ベース（平日＝営業日）でフォールバックします。
  - next_trading_day / prev_trading_day は最大探索日数を設け無限ループを防止します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント & DuckDB 保存
    - news_collector.py      — RSS → raw_news 収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログ用 DDL / 初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状のコードベースに基づく主要モジュール一覧です。strategy / execution / monitoring は将来的に拡張するためのパッケージ構成です。）

---

## よくある運用フロー（例）

1. 環境変数を設定（.env）
2. DuckDB を初期化（init_schema）
3. 夜間に run_daily_etl をスケジューラ（cron / Airflow 等）で実行
4. ETL 後に run_all_checks を参照し、重大な品質問題があればアラート
5. strategy 層でシグナル生成 → 実行層（execution）で発注 → auditテーブルへ保存

---

## サポート / 開発メモ

- テスト時や CI で .env の自動ロードを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の接続は軽量ですが、マルチスレッド／マルチプロセスでの共有には注意が必要です（適切に接続を分けてください）。
- API キー等は必ずプロダクション環境で安全に管理してください（秘密情報をレポジトリに含めない）。

---

以上がこのリポジトリの README です。必要であれば、セットアップ用の scripts、requirements ファイル、より詳細な運用ドキュメント（DataPlatform.md 参照）やサンプルワークフローを追記できます。どの部分を詳しく追加しますか？