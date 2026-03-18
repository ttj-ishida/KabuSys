# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB を用いたデータレイク、J-Quants からのデータ取得クライアント、ニュース収集、特徴量計算、ETL パイプライン、品質チェック、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の3つの大きな目的を持つコンポーネント群を含む Python パッケージです。

- データ収集（J-Quants API 経由の株価・財務・カレンダー、RSS ニュース収集）
- データ基盤（DuckDB スキーマ定義、ETL パイプライン、品質チェック、カレンダー管理）
- リサーチ／ストラテジー支援（特徴量計算、IC/相関解析、正規化ユーティリティ）

設計方針として、本番取引や発注 API へのアクセスとリサーチ処理を分離し、DuckDB を単一の真実（single source of truth）として扱います。ETL と保存処理は冪等（idempotent）に設計されており、品質チェックや監査ログを通じてトレーサビリティを確保します。

---

## 主な機能一覧

- 環境変数／設定の自動読み込みとバリデーション（.env / .env.local をサポート）
- J-Quants API クライアント
  - 株価日足（ページネーション対応、トークン自動リフレッシュ、レート制御・リトライ）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去
  - SSRF 対策（スキーム検証・プライベートアドレス検出・リダイレクト検査）
  - XML の安全パース（defusedxml）
  - DuckDB への冪等保存・銘柄抽出（4桁銘柄コード）
- DuckDB スキーマ管理・初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック統合）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算・IC（スピアマン）計算・統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（signal / order_request / executions 等）の初期化ユーティリティ

---

## 前提（推奨環境）

- Python 3.10 以上（PEP 604 の union 型記法 (|) 等を利用）
- pip が利用可能な環境
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

必要なパッケージはプロジェクトの要件に合わせて追加してください。

---

## セットアップ手順

1. リポジトリをクローンする

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb defusedxml

   （必要に応じて他のパッケージもインストールしてください）

4. 環境変数の設定

   プロジェクトルート（pyproject.toml または .git のある親）にある `.env` または `.env.local` を自動で読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される環境変数（例）:

   - JQUANTS_REFRESH_TOKEN=（必須）J-Quants リフレッシュトークン
   - KABU_API_PASSWORD=（必須）kabuステーション API パスワード（発注等が必要な場合）
   - KABU_API_BASE_URL=（任意）kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN=（必須）Slack 通知を使う場合
   - SLACK_CHANNEL_ID=（必須）Slack 通知先チャンネル
   - DUCKDB_PATH=data/kabusys.duckdb（任意）DuckDB ファイルパス（デフォルト）
   - SQLITE_PATH=data/monitoring.db（任意）
   - KABUSYS_ENV=development|paper_trading|live（任意、デフォルト development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL（任意、デフォルト INFO）

   例 .env（テンプレート）:

   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB スキーマ初期化（Python REPL やスクリプトから）

   Python からスキーマを初期化する例:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査ログ（audit）用スキーマを別 DB に初期化する場合:

   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要なユースケース）

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得＋品質チェック）:

  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")  # 既に初期化済みなら schema.get_connection でも可
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- J-Quants から株価を直接取得して保存する:

  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)

- RSS ニュースを収集して DuckDB に保存する（run_news_collection を利用）:

  from kabusys.data import news_collector
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
  res = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(res)

- リサーチ（ファクター計算・IC 計算）:

  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

- Zスコア正規化ユーティリティ:

  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])

---

## コンフィグ挙動の注意点

- settings（kabusys.config.Settings）は環境変数を参照し必須項目が未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN や SLACK_BOT_TOKEN）。
- .env のパースは Bash 形式の簡易互換を提供（export KEY=val、コメント、クォートの取り扱い等）。
- 自動で .env/.env.local を読み込みますが、テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイル抜粋）

src/
  kabusys/
    __init__.py
    config.py                      # 環境変数 / 設定管理
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント（fetch/save）
      news_collector.py            # RSS ニュース収集・保存
      schema.py                    # DuckDB スキーマ定義・初期化
      pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      quality.py                   # データ品質チェック
      stats.py                     # 統計ユーティリティ（zscore_normalize）
      features.py                  # 特徴量インターフェース
      calendar_management.py       # マーケットカレンダー管理
      audit.py                     # 監査ログ用スキーマ初期化
      etl.py                       # ETL 公開インターフェース (ETLResult)
    research/
      __init__.py
      feature_exploration.py       # 将来リターン・IC・summary 等
      factor_research.py           # momentum/value/volatility など
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

README.md（このファイル）

---

## 開発・貢献

- コーディング規約やテストはプロジェクトポリシーに従ってください。
- 新しい機能追加やスキーマ変更はスキーマ互換（既存データへの影響）を考慮して行ってください。
- DuckDB の SQL を直接扱う箇所が多いため、DDL/インデックスの変更は十分に検証してください。

---

## ライセンス

この README にはライセンス情報を含めていません。プロジェクトルートの LICENSE ファイルを参照してください。

---

必要であれば、README に具体的なコマンド例（systemd ジョブ、Airflow / Prefect などでの運用例）、CI スクリプト、もっと詳細な .env.example を追記できます。どの情報を優先して追加しましょうか？