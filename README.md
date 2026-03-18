# KabuSys

日本株自動売買プラットフォームのライブラリ群（KabuSys）。  
データ取得（J-Quants）、DuckDBベースのデータスキーマ、ETLパイプライン、ニュース収集、ファクター計算（リサーチ）および監査/実行層を想定したユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に必要な共通処理を提供するモジュール群です。主な役割は以下のとおりです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に蓄積する ETL パイプライン
- RSS からニュースを収集して前処理・銘柄紐付けを行うニュースコレクタ
- DuckDB に対するスキーマ定義・初期化ユーティリティ（Raw / Processed / Feature / Execution 層）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- リサーチ用のファクター計算（モメンタム・バリュー・ボラティリティ等）と評価指標（IC 等）
- 発注・監査ログ用の監査テーブル初期化ユーティリティ

設計上のポイント:
- DuckDB を中心に冪等（ON CONFLICT）でデータ保存
- J-Quants へのリクエストはレート制限・リトライ・トークン自動リフレッシュに対応
- 本番発注 API には直接触れない（データ処理／研究／監査／ETL を提供）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 取得・保存（stock OHLCV、財務、カレンダー）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution）
  - pipeline / etl: 差分 ETL（market calendar / prices / financials）と ETL 結果オブジェクト
  - news_collector: RSS 取得、前処理、DB への冪等保存、銘柄抽出
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 発注〜約定の監査スキーマ初期化ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- research/
  - factor_research: momentum, volatility, value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計
- config:
  - Settings: 環境変数ベースの設定取得（自動でプロジェクトルートの .env/.env.local を読み込み）

---

## 動作要件

- Python >= 3.10（型注釈に | を使用）
- 必須パッケージ:
  - duckdb
  - defusedxml

（J-Quants API 連携や実際の発注連携を行う場合、ネットワーク接続および該当サービスの認証情報が必要）

インストール例（仮）:
pip install duckdb defusedxml
（パッケージ配布用の setup がある場合は pip install -e . などを利用）

---

## 環境変数 / 設定

Settings（kabusys.config.settings）が環境変数を参照します。プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) - kabuステーション API パスワード
- KABU_API_BASE_URL (任意) - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) - Slack ボットトークン（通知用途）
- SLACK_CHANNEL_ID (必須) - 通知先 Slack チャンネル ID
- DUCKDB_PATH (任意) - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) - SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) - 実行環境 ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL (任意) - ログレベル ("DEBUG","INFO",...）

例 .env（テンプレート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール
   pip install duckdb defusedxml
   （必要に応じて他パッケージを追加）
4. プロジェクトルートに .env を作成して環境変数を設定
5. DuckDB スキーマを初期化
   - Python REPL かスクリプトから:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - 監査ログ用 DB を別ファイルで初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（基本例）

以下は主要なユースケースごとのコード例（最小限）です。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 市場カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードの set（抽出に使用）
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)

- J-Quants データフェッチ（個別）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)

- リサーチ / ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  from datetime import date
  momentum = calc_momentum(conn, date(2025, 1, 31))
  volatility = calc_volatility(conn, date(2025, 1, 31))
  value = calc_value(conn, date(2025, 1, 31))
  forward = calc_forward_returns(conn, date(2025,1,31))
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
  summary = factor_summary(momentum, ["mom_1m","mom_3m","ma200_dev"])
  normalized = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m","ma200_dev"])

- データ品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

注意点:
- J-Quants API はレート制限（120 req/min）があります。jquants_client はレートリミットとリトライを内蔵していますが、利用時にも配慮してください。
- ID トークンの自動リフレッシュ機能が実装されています（401 受信時にリフレッシュして再試行）。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数読み込み・Settings（自動 .env ロード、必須値チェック）

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（fetch/save 関数、レート制御、リトライ、トークン管理）
- news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
- schema.py — DuckDB スキーマ定義と init_schema / get_connection
- pipeline.py — ETL パイプライン（run_daily_etl 等）
- etl.py — ETLResult の公開インターフェース
- stats.py — zscore_normalize 等の統計ユーティリティ
- features.py — features インターフェース（再エクスポート）
- calendar_management.py — market_calendar 管理、営業日判定、calendar_update_job
- quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
- audit.py — 監査ログ（signal/events/order_requests/executions）のスキーマ初期化
- pipeline.py — ETL の差分処理、バックフィルや品質チェックをまとめた処理

src/kabusys/research/
- __init__.py — 研究用関数の re-export（calc_momentum 等）
- feature_exploration.py — 将来リターン calc_forward_returns, IC calc_ic, factor_summary, rank
- factor_research.py — calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials に依存）

src/kabusys/strategy/, src/kabusys/execution/, src/kabusys/monitoring/
- パッケージのエントリ（空の __init__、今後の戦略・発注・監視機能を想定）

---

## 開発者向けメモ / トラブルシューティング

- .env 読み込み:
  - 自動でプロジェクトルートを探索して `.env` / `.env.local` をロードします（.git または pyproject.toml を基準）。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB:
  - init_schema は親ディレクトリを自動作成します。
  - :memory: を指定するとインメモリ DB を使えます（テストに便利）。
- ニュース収集:
  - RSS のサイズ上限や gzip bomb、SSRF 対策（リダイレクト先の検査）に対する保護が実装されています。
- J-Quants:
  - fetch_* 関数はページネーションに対応しています。大量データ取得時は API 制限に注意してください。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献方法を記載してください。リポジトリに LICENSE ファイルがあればその内容を参照してください。）

---

README は以上です。必要であれば「設定ファイルのサンプル .env.example」や「よく使う CLI / cron ジョブの例」「ユニットテストの実行方法」などの追記も作成します。どの部分を拡充しますか？