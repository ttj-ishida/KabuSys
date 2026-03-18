# KabuSys

日本株向けの自動売買システム用ライブラリ群。データ収集（J-Quants／RSS）・DuckDBベースのデータプラットフォーム・品質チェック・特徴量計算・監査ログなど、バックエンドの共通処理を提供します。本リポジトリはライブラリとして戦略や発注ロジックを実装する土台を提供することを目的としています。

主な設計方針
- DuckDB を中心としたローカルデータプラットフォーム（冪等性重視）
- J-Quants API との連携（レートリミット・リトライ・トークンリフレッシュ対応）
- RSS ニュース収集（SSRF対策・サイズ制限・トラッキング除去）
- Data → Feature → Execution の多層スキーマ設計
- テスト容易性を考慮した設計（トークン注入、auto env load の無効化など）

---

## 機能一覧

- データ取得・保存
  - J-Quants からの株価（日足）・財務・マーケットカレンダー取得（pagination対応）
  - RSS フィードからのニュース収集と DuckDB 保存（記事ID生成・銘柄抽出）
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 冪等的な保存（INSERT ... ON CONFLICT / RETURNING を活用）

- ETL / データ品質
  - 差分更新（最終取得日に基づいた差分取得 + backfill）
  - 日次 ETL パイプライン（calendar -> prices -> financials -> 品質チェック）
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ

- インフラ・監査
  - 発注〜約定までをトレースする監査ログスキーマ（order_request_id による冪等性）
  - マーケットカレンダー補助関数（営業日判定・前後営業日の取得等）

- ユーティリティ
  - 環境変数 / .env の自動読み込み（パッケージルート検出、.env/.env.local 優先度）
  - 設定ラッパ（settings オブジェクト）

---

## セットアップ手順

前提
- Python 3.9+
- 必要な外部ライブラリ（主に duckdb, defusedxml）。以下は最低限の例。

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

3. 必要パッケージをインストール（例）
   pip install duckdb defusedxml

   - 開発パッケージや linters はプロジェクト依存なので適宜追加してください。
   - パッケージ化している場合は pip install -e . などでローカルインストールできます。

4. 環境変数の用意
   プロジェクトルートに .env を作成すると自動で読み込まれます（.env.local は優先して上書き）。
   自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（必須／任意）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack bot token（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用途）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development|paper_trading|live)（デフォルト: development）
   - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

   .env の例:
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで次を実行して DB を初期化します。

   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # または settings.duckdb_path

---

## 使い方（主要なユースケース）

以下は代表的な利用例（Python スニペット）。

- 設定の参照
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL ジョブ実行
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")

- RSS ニュース収集
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効銘柄コードセット（省略可能）
  res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(res)  # {source_name: 新規保存数}

- J-Quants API から生データを直接取得して保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, recs)

- 研究（ファクター計算）
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  mom = calc_momentum(conn, target_date=date.today())
  vol = calc_volatility(conn, target_date=date.today())
  val = calc_value(conn, target_date=date.today())
  fwd = calc_forward_returns(conn, target_date=date.today())
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])
  normalized = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])

- 自動環境ロードの制御
  テストなどで .env の自動ロードを無効にしたい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ログや例外については各モジュールが細かなログを出すため、ロギング設定を適切に行ってください（LOG_LEVEL 等）。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース内の主要ファイル一覧（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                     # 環境変数・設定管理 (.env 自動ロード、settings)
    data/
      __init__.py
      jquants_client.py           # J-Quants API クライアント（取得・保存）
      news_collector.py           # RSS ニュース収集・前処理・DB保存
      schema.py                   # DuckDB スキーマ定義・初期化
      stats.py                    # 統計ユーティリティ（z-score 等）
      pipeline.py                 # ETL パイプライン（差分取得・品質チェック等）
      features.py                 # 特徴量ユーティリティ再エクスポート
      calendar_management.py      # 市場カレンダー管理（営業日判定等）
      audit.py                    # 監査ログ（発注〜約定トレース）スキーマ
      etl.py                      # ETL 型の公開インターフェース
      quality.py                  # データ品質チェック
    research/
      __init__.py
      feature_exploration.py      # 将来リターン・IC・統計サマリー等
      factor_research.py          # モメンタム/ボラティリティ/バリュー等の計算
    strategy/
      __init__.py                 # 戦略関連モジュール配置場所（実装はここに追加）
    execution/
      __init__.py                 # 発注・ブローカ連携関連（実装はここに追加）
    monitoring/
      __init__.py                 # 監視・メトリクス関連（実装はここに追加）

---

## 注意事項 / 運用上のポイント

- セキュリティ
  - RSS 取得では SSRF 対策（リダイレクト検査・プライベートIP拒否）を組み込んでいますが、運用環境ではネットワークルールも併用してください。
  - トークンやパスワードは .env をプロダクションリポジトリにコミットしないでください。

- データ整合性
  - DuckDB スキーマは冪等に設計されていますが、外部ツールからの直接操作は想定していないため注意してください。
  - 品質チェック（quality.run_all_checks）は ETL 後に自動実行できます。重大な品質問題が検出された場合は運用ルールで対処してください。

- 実売買との距離
  - 本ライブラリの一部は「研究」「データ基盤」用途を想定しており、発注ロジック（kabuステーション連携等）や本番用のリスク管理は別途実装が必要です。KABUSYS_ENV を活用して paper_trading / live を厳格に管理してください。

---

## 貢献・拡張

- 戦略ロジック、ブローカ連携、モニタリング機能は各自拡張可能です。パッケージ内で一貫した settings / DuckDB 接続取得パターンを用いることでテストしやすく設計されています。
- 既存モジュール（news_collector, jquants_client, pipeline, research）をそのまま活用して新規ジョブやスケジューラ（Airflow / cron 等）と組み合わせることを想定しています。

---

必要に応じて README をプロジェクト固有の運用手順・CI/CD・監視ルールに合わせてカスタマイズします。追加で「CLI の使い方」「サンプルスクリプト」「.env.example」などを用意したい場合は指示してください。