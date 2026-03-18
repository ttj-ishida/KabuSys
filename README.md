# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants からの市場データ収集、DuckDB によるデータ格納・スキーマ管理、特徴量計算（ファクター）、ETL パイプライン、ニュース収集、品質チェック、監査ログなどを含む一連の機能を提供します。

主な設計方針:
- DuckDB を中核として「Raw / Processed / Feature / Execution」の多層スキーマを提供
- J-Quants API のレート制限とリトライを考慮したクライアント実装
- ETL は差分更新・バックフィル対応で冪等に保存
- ニュース収集はセキュリティ（SSRF 対策）・メモリ DoS 対策を考慮
- 研究用（research）モジュールは外部 API にアクセスせず、DuckDB の prices_daily 等のみ参照

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - 冪等的に DuckDB テーブルへ保存する save_* 関数
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル・カレンダー先読み
  - run_daily_etl による統合実行
- スキーマ管理
  - DuckDB スキーマ初期化（init_schema / init_audit_schema）
  - Raw / Processed / Feature / Execution / Audit 層のDDLを定義
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（quality.run_all_checks）
- ニュース収集
  - RSS フィードの収集、前処理、記事ID生成、raw_news 保存、銘柄抽出・紐付け
  - SSRF ブロッキング、gzip 上限、XML パース安全化
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、Z スコア正規化
- 監査ログ
  - signal_events / order_requests / executions などを含む監査用スキーマ
- 設定管理
  - 環境変数および .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示（例: JQUANTS_REFRESH_TOKEN）

---

## セットアップ手順

前提:
- Python 3.9+（コードは typing の Union 用法などを利用）
- DuckDB を利用可能な環境

1. リポジトリをクローン（またはプロジェクトルートへ移動）
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （開発向けやパッケージ化されている場合は requirements.txt や pyproject.toml があればそちらを使用してください。）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB：デフォルト: data/monitoring.db）

   例 `.env`（サンプル）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. スキーマ初期化
   Python REPL やスクリプトで DuckDB スキーマを作成します（デフォルトの DB パスは環境変数 DUCKDB_PATH）。
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

---

## 使い方（主要な呼び出し例）

以下はライブラリの主要な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取るため、conn を共有して作業します。

- スキーマ初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- ETL（日次）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # デフォルトで本日を対象に ETL を実行
  print(result.to_dict())

- J-Quants から日足取得と保存（個別呼び出し）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved_count = jq.save_daily_quotes(conn, records)

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  mom = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  val = calc_value(conn, target_date)
  fwd = calc_forward_returns(conn, target_date, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])

- 品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=target_date)
  for i in issues:
      print(i)

- 監査スキーマ初期化（audit 用 DB）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意:
- jquants_client は内部で設定 settings.jquants_refresh_token を参照します。get_id_token の引数でトークンを注入することも可能です（テスト用途）。
- ニュース収集は外部ネットワークにアクセスします。SSRF／サイズ上限／XML パースの安全化等に配慮しています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — 必須：J-Quants リフレッシュトークン
- KABU_API_PASSWORD — 必須：kabu API のパスワード
- KABU_API_BASE_URL — 任意：kabu API ベース URL（デフォルト localhost）
- SLACK_BOT_TOKEN — 必須：Slack Bot トークン
- SLACK_CHANNEL_ID — 必須：Slack 通知先チャンネル ID
- DUCKDB_PATH — 任意：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 任意：監視用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 任意：development | paper_trading | live（デフォルト development）
- LOG_LEVEL — 任意：DEBUG/INFO/…（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 任意：1 を設定すると .env 自動ロードを無効化

settings は kabusys.config.settings オブジェクトとして利用できます（型安全なプロパティを提供）。

---

## ディレクトリ構成

（プロジェクトの主要ファイル・モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・レート制御・リトライ）
    - news_collector.py
      - RSS 取得、前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
      - init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - 差分 ETL / run_daily_etl
    - features.py
      - data.stats の再エクスポート
    - calendar_management.py
      - market_calendar 更新・営業日ロジック
    - etl.py
      - ETLResult の公開インターフェース
    - quality.py
      - データ品質チェック群
    - audit.py
      - 監査ログ用スキーマ初期化
  - research/
    - __init__.py
      - 研究用 API のエクスポート
    - feature_exploration.py
      - 将来リターン計算、IC、ファクター統計サマリ
    - factor_research.py
      - momentum / value / volatility ファクター計算
  - strategy/
    - __init__.py
    - （戦略関連の実装を置く場所）
  - execution/
    - __init__.py
    - （発注・ブローカー連携の実装を置く場所）
  - monitoring/
    - __init__.py
    - （監視・アラート関連）

---

## 注意事項 / 補足

- 自動環境読込はプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に行います。CI 等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）を尊重するよう実装済みですが、運用時はさらに上位のスロットリングやバッチ設計を検討してください。
- DuckDB の SQL を直接実行するため、パラメータバインド（?）を用いてインジェクション対策を行っています。DDL / スキーマ変更は慎重に。
- research モジュールの関数は本番発注や外部 API へアクセスしない設計です（安全にバックテスト/解析可能）。

---

もし README に追加したい具体的な使用例（CI での ETL 実行スクリプト、Dockerfile、requirements.txt、.env.example の完全なテンプレートなど）があれば、提供します。