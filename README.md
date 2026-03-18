# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB を用いたデータレイヤ、J-Quants からのデータ取得クライアント、RSS ニュース収集、特徴量計算、ETL パイプライン、データ品質チェック、監査ログなどを含みます。

---

## 概要

KabuSys は日本株の戦略開発・運用に必要なデータ基盤とユーティリティ群を提供するパッケージです。主な目的は以下です。

- J-Quants API を使った株価・財務・マーケットカレンダーの取得（ページネーション / レート制御 / トークン自動更新）
- RSS からのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去・メモリ制限）
- DuckDB ベースのスキーマ定義と冪等な保存ロジック
- ETL（差分更新・バックフィル・品質チェック）パイプライン
- 研究用：ファクター（モメンタム / ボラティリティ / バリュー）計算、将来リターン・IC 計算、Z スコア正規化
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ

設計上、本番口座や発注 API には直接アクセスしないモジュール（research / data 層）と、発注に関わるスキーマ（audit / execution 層）を分離しています。

---

## 主な機能一覧

- data/jquants_client：J-Quants API クライアント（取得・保存関数）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミット / リトライ / トークン自動更新 を備える
- data/news_collector：RSS 取得・正規化・DB 保存・銘柄抽出
  - fetch_rss, save_raw_news, run_news_collection
  - SSRF 対策、gzip 上限、XML 安全パースなどを実装
- data/schema：DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - init_schema, get_connection
- data/pipeline：ETL パイプライン
  - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
- data/quality：品質チェック（欠損・スパイク・重複・日付不整合）
  - run_all_checks と個別チェック関数
- data/calendar_management：市場カレンダー管理（営業日判定 / next/prev_trading_day 等）
- research/factor_research：モメンタム・ボラティリティ・バリュー計算
- research/feature_exploration：将来リターン計算・IC（Spearman）・統計サマリー
- data/stats：Z スコア正規化ユーティリティ
- audit：監査ログスキーマ（signal_events / order_requests / executions）と初期化関数

---

## 必要な環境変数

KabuSys は環境変数（またはプロジェクトルートの `.env` / `.env.local`）から設定を読み込みます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化できます。

最低限設定が必要な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

オプション（デフォルトあり）:

- KABUSYS_ENV : environment（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL : ログレベル (`INFO` 等)。デフォルト `INFO`
- KABUS_API_BASE_URL : kabu API の base URL（デフォルトはローカル）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト `data/monitoring.db`）

.env ファイルのパースは一般的な形式をサポートしており、`export KEY=val` やクォート付き値、インラインコメント処理が行われます。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン（例）
   - git clone <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject/requirements があればそちらを利用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要なキーを追加するか、CI/環境変数に設定します。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. 監査ログスキーマ（必要に応じて）
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（サンプル）

以下は典型的な操作の例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しない場合は今日を基準に実行
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes に上場銘柄コードの集合を渡すと記事と銘柄を紐付けます
  res = run_news_collection(conn, known_codes={"7203", "6758"})
  print(res)  # ソースごとの保存件数
  ```

- J-Quants から日足を取得して保存（テスト用途）
  ```python
  from kabusys.data import jquants_client as jq
  # id_token を直接渡すか、環境変数の refresh token を利用（自動取得）
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  mom = calc_momentum(conn, target_date=date(2024,1,31))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 将来リターン / IC 計算
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5])
  # factor_records は calc_momentum 等の出力
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

注意: 上の関数群は DuckDB の `prices_daily`, `raw_financials`, `market_calendar` 等のテーブルを参照します。事前に `init_schema()` を実行してスキーマを作成し、ETL でデータを投入してください。

---

## 実行オプション / テストヒント

- 自動で .env を読み込む機能はパッケージ読み込み時に有効です。テストで環境を明示的に制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効にできます。
- jquants_client の HTTP 通信や URL open 部分はユニットテストの際にモックしやすい設計（トークンキャッシュ、_urlopen の差し替えなど）になっています。
- DuckDB の接続は ":memory:" を使えばインメモリ DB に対するテストが可能です。

---

## ディレクトリ構成

パッケージのディレクトリ構成（主要ファイルのみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（取得・保存）
      - news_collector.py  — RSS ニュース収集/保存
      - schema.py          — DuckDB スキーマ定義 / init_schema
      - pipeline.py        — ETL パイプライン（run_daily_etl 等）
      - features.py        — 特徴量ユーティリティ公開インターフェース
      - calendar_management.py — カレンダー管理 / 営業日判定
      - stats.py           — zscore_normalize 等の統計ユーティリティ
      - quality.py         — データ品質チェック
      - etl.py             — ETL 型の公開インターフェース（ETLResult）
      - audit.py           — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/            — 戦略関連（パッケージプレースホルダ）
    - execution/           — 発注/ブローカー連携（パッケージプレースホルダ）
    - monitoring/          — 監視用コード（パッケージプレースホルダ）

---

## 依存ライブラリ

主な外部依存:

- duckdb
- defusedxml

これらは pip でインストールしてください。その他のロジックは標準ライブラリで記述されています。

---

## ライセンス / 注意事項

- 本リポジトリは自動売買ロジックや市場データを扱います。実運用前に十分なテストとリスク管理（paper_trading 環境の活用）を行ってください。
- J-Quants / kabu API の利用は、各サービスの利用規約・レート制限に従ってください。
- 本 README はコードベースの主要機能をまとめたものです。詳細は各モジュールの docstring を参照してください。

---

必要であれば、具体的なコマンド例（cron ジョブの設定例・Dockerfile・systemd ユニット等）や、`.env.example` の雛形も作成します。どの情報がさらに必要か教えてください。