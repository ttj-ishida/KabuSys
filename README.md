# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
DuckDB を用いたデータレイヤ、J-Quants API クライアント、RSS ニュース収集、特徴量計算（リサーチ）や ETL パイプライン、監査ログスキーマなどを含んでいます。

## 特徴（概要）
- DuckDB ベースの3層データスキーマ（Raw / Processed / Feature / Execution）
- J-Quants API クライアント（レート制限・リトライ・トークン自動更新対応）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・冪等保存）
- ファクター / リサーチユーティリティ（モメンタム・ボラティリティ・バリュー等）
- 監査ログスキーマ（シグナル→発注→約定までのトレーサビリティ）
- 環境変数ベースの設定管理（.env, .env.local 自動ロード、無効化オプションあり）

## 主な機能一覧
- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
- data/schema.py
  - init_schema(db_path) : DuckDB にスキーマ（テーブル・インデックス）を作成
  - get_connection(db_path)
- data/pipeline.py
  - run_daily_etl(conn, ...) : 日次 ETL（カレンダー・株価・財務・品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL
- data/news_collector.py
  - fetch_rss(url, source) : RSS 取得（SSRF/サイズ/圧縮対策）
  - save_raw_news / save_news_symbols / run_news_collection
  - extract_stock_codes（本文から4桁の銘柄コード抽出）
- data/quality.py
  - 各種品質チェック（欠損・スパイク・重複・日付不整合）と run_all_checks
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data/audit.py
  - 監査ログテーブル初期化（init_audit_schema, init_audit_db）
- research/*.py
  - calc_momentum, calc_volatility, calc_value（ファクター算出）
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（探索・評価）
- config.py
  - Settings クラス（環境変数読み込み、自動 .env 読み込み、必須チェック）

## 前提（Requirements）
- Python 3.10+
  - 型注釈に | 演算子を使用しているため 3.10 以上が必要です
- 推奨パッケージ
  - duckdb
  - defusedxml
- （標準ライブラリのみで動くユーティリティもありますが、ETL / DB / XML 処理に上記が必要）

例:
pip install duckdb defusedxml

## セットアップ手順

1. リポジトリをチェックアウト

2. Python 環境を用意（推奨: venv / pyenv）
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（Settings により参照）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャネル ID（必須）
   任意 / デフォルトあり:
   - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視 DB（デフォルト: data/monitoring.db）

4. DuckDB スキーマ初期化
   - ライブラリをインポートしてスキーマを初期化します（親ディレクトリが存在しない場合は自動作成されます）。

   例:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

5. 監査ログ（別 DB に分離して使う場合）
   例:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

## 使い方（主要操作例）

- 日次 ETL（市場カレンダー→株価→財務→品質チェック）
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルト: today を対象に ETL を実行
  print(result.to_dict())

- 個別 ETL（株価差分取得）
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 1, 31))

- J-Quants から日足を直接取得して保存
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()
  records = jq.fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)

- RSS ニュース収集（既知銘柄セットを指定して紐付けまで行う）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}

- ファクター計算（Research）
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
  res_mom = calc_momentum(conn, target_date=date(2026,1,31))
  res_vol = calc_volatility(conn, target_date=date(2026,1,31))
  res_val = calc_value(conn, target_date=date(2026,1,31))
  # Z スコア正規化
  normed = zscore_normalize(res_mom, ["mom_1m", "mom_3m", "mom_6m"])

- 情報係数（IC）評価、将来リターン計算
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  fwd = calc_forward_returns(conn, target_date=date(2026,1,31))
  ic = calc_ic(factor_records=res_mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(res_mom, ["mom_1m", "ma200_dev"])

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

## 設計上の注意 / セキュリティ
- J-Quants API 呼び出しはモジュール内でレート制限（120 req/min）とリトライを実装しています。大量リクエスト時は設定やバックオフ方針を確認してください。
- news_collector は SSRF 対策、受信サイズ上限、gzip 解凍上限、トラッキングパラメータ除去、XML の安全パーサ（defusedxml）を用いています。
- DuckDB への保存は多くが ON CONFLICT を用いた冪等実装です。
- 環境変数は OS 環境 > .env.local > .env の優先順位で読み込まれます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制できます。
- 監査ログは UTC タイムスタンプで記録する設計です（init_audit_schema は TimeZone を UTC に固定します）。

## ディレクトリ構成（概要）
以下は主要ファイルの一覧（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                          : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 : J-Quants API クライアント + 保存ロジック
    - news_collector.py                 : RSS ニュース収集・保存・銘柄抽出
    - schema.py                         : DuckDB スキーマ定義 & init_schema
    - stats.py                          : 統計ユーティリティ（zscore_normalize）
    - pipeline.py                       : ETL パイプライン（run_daily_etl 等）
    - features.py                       : 特徴量インターフェース再エクスポート
    - calendar_management.py            : カレンダー管理 / 更新ジョブ
    - audit.py                          : 監査ログスキーマの初期化
    - etl.py                            : ETLResult の公開インターフェース
    - quality.py                        : データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py            : 将来リターン計算 / IC / summary / rank
    - factor_research.py                : momentum / volatility / value 計算
  - strategy/                            : （空のパッケージ。戦略実装を配置）
    - __init__.py
  - execution/                           : （空のパッケージ。発注/実行ロジックを配置）
    - __init__.py
  - monitoring/                          : 監視関連（空のパッケージ）

（README 用簡易ツリー。実際のファイルはリポジトリを参照してください）

## 開発メモ
- Python 型注釈や設計コメントが豊富に含まれているため、テストや拡張がしやすい構造です。
- research モジュールは外部ライブラリ（pandas など）に依存しない設計です。大量データを扱う場合はパフォーマンス評価を行ってください。
- DuckDB のバージョンによっては一部の制約・挙動が異なるため（例: ON DELETE / UNIQUE の NULL 扱い等）、データ移行や外部接続時は注意してください。

---

何か追加したい利用例や、README に含める具体的なコマンド（CI / systemd / cron の例 など）があれば教えてください。必要に応じてサンプル .env.example や簡易起動スクリプトも作成できます。