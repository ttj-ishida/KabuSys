# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、特徴量計算（リサーチ用）、監査ログなどを備えています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するためのモジュール群です。主な責務:

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ定義と冪等保存（ON CONFLICT 対応）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー、IC 計算 等）
- 監査ログ（シグナル → 発注 → 約定 のトレース用スキーマ）
- マーケットカレンダー管理（営業日判定 / next/prev / 範囲取得）

設計上、本番の発注 API には直接アクセスしないモジュール（data/research 等）と、発注/実行を扱うレイヤーを分離しています。

---

## 主な機能一覧

- data/jquants_client
  - 株価日足 / 財務データ / JPX カレンダーの取得（ページネーション対応）
  - レートリミット（120 req/min）対応、指数バックオフリトライ、401 時のトークン自動更新
  - DuckDB への冪等保存ユーティリティ（raw_prices, raw_financials, market_calendar など）
- data/schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() による初期化
- data/pipeline
  - 日次 ETL（差分取得・バックフィル・品質チェック）実行関数 run_daily_etl
- data/news_collector
  - RSS 取得（SSRF 対策、gzip 対応、XML パース防御）
  - raw_news / news_symbols への保存（冪等、チャンク挿入）
  - 銘柄コード抽出（4 桁コード）
- data/quality
  - 欠損/スパイク/重複/日付不整合 のチェック
- research
  - calc_momentum, calc_volatility, calc_value（DuckDB の prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・IC 計算等）
  - zscore_normalize（data.stats）
- audit
  - 監査テーブルの初期化 (init_audit_schema / init_audit_db)
- config
  - .env / 環境変数読み込み、自動ロードロジック（プロジェクトルート探索により .env/.env.local を読み込む）
  - 必須設定取得 helper（未設定時は ValueError）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈の union 型等を使用）
- DuckDB, defusedxml 等の依存パッケージ

1. リポジトリをクローン（または既存ソースを配置）
2. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install -U pip
   - pip install duckdb defusedxml
   - pip install -e .   # パッケージ配布設定があれば開発インストール
   なお、プロダクションでは requirements.txt / poetry 等で依存管理してください。

4. 環境変数（.env）を準備  
   プロジェクトルート（.git または pyproject.toml があるフォルダ）を基準に自動で .env / .env.local を読み込みます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な環境変数（config.Settings が要求するもの）:
   - JQUANTS_REFRESH_TOKEN  （J-Quants の refresh token）
   - KABU_API_PASSWORD      （kabuステーション API のパスワード）
   - SLACK_BOT_TOKEN        （Slack 通知用ボットトークン）
   - SLACK_CHANNEL_ID       （通知先チャンネル ID）

   任意 / デフォルト指定付き:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   例 (.env の最低例):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は Python スクリプトや REPL での利用例です。各例は最小の実行方法を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 単発で株価データを取得して保存（jquants_client を直接使用）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

  # id_token を省略するとモジュール内キャッシュを使用、401 時は自動で refresh を試行
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

  # known_codes に有効銘柄コードのセットを渡すと記事と銘柄の紐付けを行う
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(stats)
  ```

- 研究（リサーチ）用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2025, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target)
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- カレンダー管理ユーティリティ
  ```python
  from kabusys.data.calendar_management import next_trading_day, is_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date.today()))
  print(next_trading_day(conn, date.today()))
  ```

- 品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for issue in issues:
      print(issue)
  ```

注意:
- J-Quants の API レート制限を考慮して、jquants_client 内部でスロットリングを行います。
- id_token の自動リフレッシュは 401 を受けた場合に 1 回だけ試行します。
- ETL や保存処理は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を前提としています。

---

## 環境変数と設定

主な設定項目（環境変数名）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ('development'|'paper_trading'|'live')（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にするには 1 を設定

config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env を自動読み込みします。

---

## ディレクトリ構成

主要なファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py      — RSS ニュース収集と保存
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — 特徴量インターフェース（再エクスポート）
    - calendar_management.py — カレンダー更新・営業日ユーティリティ
    - audit.py               — 監査ログ用スキーマ / 初期化
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - factor_research.py     — モメンタム/ボラ/バリュー計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記はコードベースの要旨であり、実際のリポジトリには README 生成時点でのファイルが含まれます）

---

## 運用上の注意 / ベストプラクティス

- 本リポジトリはデータ取得・計算に関する機能を多く含みますが、実際の発注・ブローカー接続は別レイヤーで慎重に扱ってください。特に本番口座（live）では事前に十分なテストを行ってください。
- 環境変数は機密情報を含むため、CI/CD やデプロイ時は Secrets 管理を利用してください。
- DuckDB ファイルはバイナリサイズが大きくなる可能性があります。定期的なバックアップやパージ戦略を検討してください。
- ニュースの RSS 取得では SSRF・XML BOM/EXPLOIT を防ぐための対策を実装していますが、外部フィードの取り扱いには注意してください。
- ETL の品質チェックでエラーがあった場合はログを確認し、人手での対応方針を決定してください（run_daily_etl は Fail-Fast ではなく問題を収集して報告します）。

---

## 貢献 / 変更履歴

本 README は現行コードベースを基に自動生成した概要ドキュメントです。実装の拡張や API 変更があった場合は README を更新してください。

ご質問や改善提案があればお知らせください。