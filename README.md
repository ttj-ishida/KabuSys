# KabuSys

日本株自動売買システムのライブラリ群（データ基盤・ファクター計算・ETL・監査ログ等）。  
このリポジトリは DuckDB を中心としたデータプラットフォームと、J-Quants API / RSS ベースのニュース収集、研究用ファクター計算、ETL パイプライン、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

## 概要
- DuckDB をデータベースとして、Raw / Processed / Feature / Execution 層のスキーマを提供します。
- J-Quants API から株価・財務・マーケットカレンダーを取得し、冪等に保存するクライアント（リトライ・レート制御・トークン自動リフレッシュ対応）。
- RSS フィードからニュースを安全に収集し、記事と銘柄コードの紐付けを行うニュースコレクタ。
- ETL の差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）を行うパイプライン。
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）・特徴量探索（将来リターン計算、IC 計算、統計サマリー）と正規化ユーティリティ。
- 監査（audit）スキーマにより、シグナル→発注→約定のトレーサビリティを確保。

## 主な機能一覧
- データ取得 / 保存
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar
- ETL
  - run_daily_etl（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめて実行）
- ニュース収集
  - fetch_rss（SSRF 対策・サイズ制限・gzip 対応）
  - save_raw_news / save_news_symbols（冪等保存）
  - extract_stock_codes（本文から銘柄コード抽出）
- スキーマ管理
  - init_schema(db_path)（DuckDB に全テーブル・インデックスを作成）
  - init_audit_db / init_audit_schema（監査ログ用の初期化）
- 研究・特徴量
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（Zスコア正規化）
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）と Settings API

## 必須環境変数
少なくとも以下を設定してください（.env ファイルで管理可能）。

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（省略時: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（省略時: INFO）

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セットアップ手順（ローカル開発向け）
前提:
- Python 3.10 以上（PEP 604 の union 型記法などを使用しているため）
- pip が使用可能

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ...
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じてテスト・リンター等を追加）
   - もしパッケージ配布設定があれば: pip install -e .
4. .env を作成
   - プロジェクトルートに .env を置くと自動読み込みされます。例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. DuckDB スキーマ初期化
   - Python REPL / スクリプトから init_schema を呼び出します（下記参照）。

## 使い方（主要な例）

1) DuckDB スキーマを初期化する
- Python で:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

  -> これで必要なテーブル・インデックスが作成され、DuckDB 接続が返ります。

2) 日次 ETL を実行する
- 取得・保存・品質チェックまで一括実行:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

  主なオプション:
  - target_date: ETL 対象日（省略時は今日）
  - id_token: J-Quants トークンを注入可能（テスト時に便利）
  - run_quality_checks: 品質チェックを実行するか

3) ニュース収集ジョブを実行する
- RSS から収集して保存:
  from kabusys.data.news_collector import run_news_collection
  stats = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(stats)  # {source_name: saved_count, ...}

4) J-Quants API を直接呼びたい場合
- トークン取得:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()

- データ取得（ページネーション対応）:
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=..., date_to=...)
  financials = fetch_financial_statements(date_from=..., date_to=...)

5) 研究用ファクター計算（Research）
- 例: モメンタム計算
  from kabusys.research import calc_momentum, zscore_normalize
  rows = calc_momentum(conn, target_date)
  normed = zscore_normalize(rows, ["mom_1m", "mom_3m", "mom_6m"])

- 将来リターン・IC 計算:
  from kabusys.research import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, target_date)
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")

6) 品質チェックを個別に実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=target_date)
  for i in issues:
      print(i)

## 注意点 / 実運用向けのメモ
- J-Quants のレート制限（120 req/min）に合わせた内部レートリミッタとリトライロジックを実装済みです。
- get_id_token は 401 を検出した際に自動でリフレッシュする仕組みを持ちます（モジュール内キャッシュで共有）。
- NewsCollector は SSRF・XML Bomb・過大レスポンス防御などを考慮して実装されています。
- DuckDB の ON CONFLICT 系を用いた冪等保存を行っているため、ETL の再実行は安全です。
- audit スキーマは UTC タイムゾーンでの運用を前提にしています（init_audit_schema で TimeZone を UTC に設定）。

## ディレクトリ構成
- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数・設定読み込み（Settings）
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント（取得・保存）
    - news_collector.py                  — RSS ニュース収集 / 保存
    - schema.py                          — DuckDB スキーマ定義・初期化
    - stats.py                           — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - features.py                        — 特徴量ユーティリティ（公開インターフェース）
    - calendar_management.py             — マーケットカレンダー管理・ジョブ
    - etl.py                             — ETL 関連の公開型（ETLResult）
    - audit.py                           — 監査ログ（signal / order / execution）初期化
    - quality.py                         — データ品質チェック
  - research/
    - __init__.py                        — 研究用 API の再エクスポート
    - feature_exploration.py             — 将来リターン・IC・統計サマリ
    - factor_research.py                 — momentum / volatility / value 計算
  - strategy/                             — 戦略関連（モジュールプレースホルダ）
  - execution/                            — 発注関連（モジュールプレースホルダ）
  - monitoring/                           — 監視/モニタリング（プレースホルダ）

## 簡易 .env 例
JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
KABU_API_PASSWORD=<your_kabu_api_password>
SLACK_BOT_TOKEN=<your_slack_bot_token>
SLACK_CHANNEL_ID=<your_slack_channel_id>
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## 開発・貢献
- コードスタイル・テストの追加、API 呼び出しのモック化（テスト容易性向上）など歓迎します。
- 重大な変更（データスキーマ・主要 API の挙動）を行う場合はメジャーアップデートとして注意深くレビューしてください。

---

質問があれば、特定の機能の利用例（ETL 実行スクリプト、ニュース収集ジョブの Cron 設定、ファクター計算のサンプルなど）について具体的なサンプルを追加で作成します。どの部分をもっと詳しく記載したいか教えてください。