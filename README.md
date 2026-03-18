# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤の骨格を提供する Python ライブラリです。DuckDB をデータ層に用いて、データ取得（J-Quants）、ETL、品質チェック、特徴量生成、ニュース収集、監査ログなどをモジュール化して実装しています。発注や本番接続部分は分離されており、研究（Research）用途と本番（Execution）用途の両方を想定した設計になっています。

主な使いどころ:
- J-Quants からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB によるスキーマ初期化・保存（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算、IC・サマリ解析

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション（KABUSYS_ENV / LOG_LEVEL 等）
- データ取得
  - J-Quants API クライアント（リトライ・レート制御・トークン自動更新）
  - 市場カレンダー、日足、財務データのページネーション対応取得
- データ永続化（DuckDB）
  - raw_prices / raw_financials / market_calendar / などの冪等保存（ON CONFLICT）
  - スキーマ初期化ユーティリティ（init_schema / init_audit_db）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合検出
- ニュース収集
  - RSS フィード取得、URL 正規化、記事ID生成（SHA-256）、raw_news 保存、銘柄抽出
  - SSRF / XML Bomb / GZip 大きさ制限 等の防御を実装
- 研究用ユーティリティ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計サマリ
  - クロスセクション Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化

---

## 前提・依存関係

最小限の実行に必要なパッケージ（例）
- Python 3.9+（typing の一部書式を使用）
- duckdb
- defusedxml

インストール例（pip）:
pip install duckdb defusedxml

※ 実運用ではネットワーク接続、J-Quants API トークン、kabuステーション等の設定が必要です。

---

## 環境変数（必須 / 主要）

主に以下の環境変数が参照されます（README では主要なものを抜粋）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV: 実行環境。development / paper_trading / live のいずれか（デフォルト: development）
- LOG_LEVEL: ログレベル。DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

.env の自動読み込み:
- プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して検出します。
- 読み込み順: OS 環境 > .env.local > .env

例 .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. リポジトリをクローン／配置する

2. 依存パッケージをインストール
   pip install duckdb defusedxml

3. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を作成し、上記の必須値を設定します。
   - 自動読み込みを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから以下を実行してデータベースとテーブルを作成します。

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" でも可

   監査ログ用 DB を別ファイルで初期化する場合:
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")

5. （任意）監視用 SQLite 等の準備や Slack 設定

---

## 使い方（主要ユースケース）

以下はライブラリの主要機能の使い方例です。各機能は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ることが多く、テスト時は ":memory:" を使うと便利です。

- スキーマ初期化（再掲）
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL の実行
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を済ませる
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

  - run_daily_etl は市場カレンダー→株価→財務→品質チェックの順に処理します。
  - J-Quants API トークンは settings.jquants_refresh_token（環境変数）を使って取得します。
  - エラー・品質問題は ETLResult に集約されます。

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}

- J-Quants からの日足取得（低レベル API）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

- 研究用（ファクター計算 / IC / サマリ）
  from kabusys.research import (
      calc_momentum, calc_volatility, calc_value,
      calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
  )
  conn = schema.get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])

- Z スコア正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])

- カレンダー管理（営業日判定）
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  is_trading = is_trading_day(conn, date(2024,1,2))
  next_td = next_trading_day(conn, date(2024,1,1))
  days = get_trading_days(conn, date(2024,1,1), date(2024,1,31))

---

## ディレクトリ構成

主要なソース配置（src/kabusys 以下）:

- kabusys/
  - __init__.py                  -- パッケージ定義（__version__）
  - config.py                    -- 環境変数 / 設定読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得・保存）
    - news_collector.py          -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - stats.py                   -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - features.py                -- 特徴量公開インターフェース
    - calendar_management.py     -- market_calendar 管理ユーティリティ
    - audit.py                   -- 監査ログテーブル定義・初期化
    - etl.py                     -- ETL ユーティリティの公開（ETLResult）
    - quality.py                 -- データ品質チェック
  - research/
    - __init__.py                -- 研究用 API エクスポート
    - factor_research.py         -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py     -- 将来リターン / IC / サマリ等
  - strategy/
    - __init__.py                -- 戦略層（未実装の拡張ポイント）
  - execution/
    - __init__.py                -- 発注実行層（未実装の拡張ポイント）
  - monitoring/
    - __init__.py                -- 監視 / モニタリング用（拡張ポイント）

詳細（ファイル毎の責務）は各モジュールの docstring を参照してください。

---

## 設計上の注意点 / トラブルシューティング

- 環境変数が不足すると Settings のプロパティが ValueError を投げます（必須設定を確認してください）。
- .env の自動ロードはプロジェクトルートの探索に依存するため、開発環境で .env が読み込まれない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をチェックしてください。
- J-Quants API 呼び出しはレート制限（120 req/min）に従い内部でスロットリングしています。大量バックフィル時は時間がかかります。
- DuckDB の ON CONFLICT を使った保存設計により ETL は冪等です（同じデータを複数回処理しても上書きで整合性が保たれます）。
- NewsCollector は RSS の XML パースや外部 URL を扱うため、defusedxml による保護と SSRF 防止ロジックを実装しています。外部ネットワークの制約（プロキシやファイアウォール）に注意してください。
- テスト時は大量の外部 API 依存を切り離すため、関数に id_token を注入したり、ネットワーク層をモックすることが推奨されます。

---

## 貢献 / 拡張ポイント

- strategy と execution パッケージは発注ロジックやブローカー接続の実装場所として用意しています。ここにポートフォリオ最適化・リスク管理・ブローカードライバを追加してください。
- 研究用モジュールは軽量実装（標準ライブラリのみ）で提供しています。より大規模な解析では pandas / numpy / scipy での実装を橋渡しするユーティリティを追加すると便利です。
- モニタリング、アラート（Slack 投稿等）、運用用 CLI / Docker 化は今後の拡張候補です。

---

必要であれば、README に実行可能なサンプルスクリプト（ETL cron 用やデバッグ用）や、CI テスト手順、Dockerfile / compose の例も追加できます。どの情報を優先的に追記しますか？