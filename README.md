KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリです。  
データ取得（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター計算（研究用）、監査ログ用スキーマなどを備え、戦略実行層との連携を想定した設計になっています。

主な特長
--------
- J-Quants API クライアント（認証・ページネーション・レート制御・リトライ対応）
- DuckDB を用いた 3 層データスキーマ（Raw / Processed / Feature）と監査ログスキーマ
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・重複排除）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と IC / 統計サマリー
- Z スコア正規化など共通統計ユーティリティ
- 設定は環境変数 / .env ファイルで管理（自動ローディングあり）

機能一覧
--------
- 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証
- データ取得（kabusys.data.jquants_client）
  - 日足・財務・マーケットカレンダーなどの取得、ページネーション対応
  - レートリミット（120 req/min）とリトライ、401 → トークン自動更新
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）
- データスキーマ初期化（kabusys.data.schema）
  - DuckDB のテーブル / インデックス作成（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日 + backfill）、カレンダー先読み、品質チェック
- 品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue オブジェクトで返却）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・ID 生成（URL 正規化 + SHA-256）・DuckDB への冪等保存
  - 銘柄コード抽出と news_symbols の紐付け
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- 研究用ファクター（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - DuckDB の prices_daily / raw_financials を参照する設計（本番取引 API にはアクセスしない）
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクションの Z スコア正規化）
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査用テーブルと初期化関数
- （拡張予定）strategy / execution / monitoring の基本パッケージ構造

セットアップ手順
-------------
1. Python 環境準備（推奨: venv）
   - Python 3.9+ を想定（実装は typing/構文を使用しているためバージョンを合わせてください）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要ライブラリをインストール
   - 本リポジトリに requirements.txt がない場合は最低限以下を入れてください:
     pip install duckdb defusedxml
   - 実プロジェクトでは追加で requests 等を使う場合があります。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB 等の SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで schema.init_schema() を呼びます（ファイルパスは settings.duckdb_path を使うと便利）。
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を別に作る場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（よく使う操作例）
-----------------------

- 日次 ETL を実行する（簡単なサンプル）:
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  # DB 初期化（初回のみ）
  conn = schema.init_schema("data/kabusys.duckdb")

  # ETL 実行（今日のデータを取得して品質チェックも行う）
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- J-Quants から日足を直接取得して保存する:
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)

- ニュース収集を実行して銘柄紐付けまで行う:
  from kabusys.data import news_collector as nc
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  res = nc.run_news_collection(conn, sources=None, known_codes=known_codes)
  print(res)

- 研究用ファクター計算（例: モメンタム）:
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024,1,31))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

- IC（Information Coefficient）を計算する:
  from kabusys.research import calc_forward_returns, calc_ic
  forward = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
  ic = calc_ic(factor_records=records, forward_records=forward, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

- 監査ログスキーマの初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

設定の自動読み込みについて
-------------------------
- kabusys.config モジュールは、実行時にプロジェクトルートを探して .env → .env.local を順に読み込みます（OS 環境変数を保護）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで有用）。
- 必須のキーが足りない場合は Settings のプロパティアクセス時に ValueError を投げます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                     -- 環境設定・自動 .env 読み込み
- data/
  - __init__.py
  - jquants_client.py           -- J-Quants API クライアント + 保存関数
  - news_collector.py           -- RSS 収集・前処理・DB 保存
  - schema.py                   -- DuckDB スキーマ定義と init_schema
  - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
  - quality.py                  -- データ品質チェック
  - calendar_management.py      -- 市場カレンダー管理・ヘルパ
  - etl.py                      -- ETL 用公開型再エクスポート
  - features.py                 -- 特徴量ユーティリティ（再エクスポート）
  - stats.py                    -- 統計ユーティリティ（zscore_normalize）
  - audit.py                    -- 監査ログテーブル定義と初期化
- research/
  - __init__.py
  - feature_exploration.py      -- forward returns / IC / summary / rank
  - factor_research.py          -- momentum / volatility / value 計算
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

設計方針・注意点
----------------
- DuckDB をデータレイクの中心に据え、SQL ウィンドウ関数を多用して高速に集計・特徴量算出を行います。
- ETL やデータ更新は冪等（ON CONFLICT）を意識して設計されています。
- 研究用関数は本番発注 API にはアクセスしないこと（Look-ahead bias や安全性の観点）。
- news_collector は SSRF 対策・XML 脆弱性対策を行っています（defusedxml、リダイレクト検査、ホスト判定など）。
- 本リポジトリはモジュール群の骨格を提供します。実運用するには各種環境変数の設定、ジョブスケジューラ、取引ブローカー向け実装等が必要です。

貢献・開発
----------
- 開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境を明示的に用意すると便利です。
- DuckDB を使った単体テストは ":memory:" を渡してインメモリ DB を使用可能です（schema.init_schema(":memory:")）。

お問い合わせ
------------
実装に関する問い合わせや改善提案は PR / Issue でご連絡ください。