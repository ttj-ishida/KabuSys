# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータストアに、J-Quants API や RSS をデータソースとして想定し、ETL、データ品質チェック、特徴量生成、ニュース収集、監査ログ等を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの市場データ（OHLCV・財務・カレンダー）取得と DuckDB への保管（冪等）
- RSS ベースのニュース収集と記事→銘柄紐付け
- ETL（差分取得／バックフィル）パイプライン、品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算および特徴量探索（IC/forward returns 等）
- 監査ログ（シグナル／発注／約定トレーサビリティ）用スキーマ定義
- 研究用途に使える軽量な統計ユーティリティ

設計上、production の発注APIや外部トレード実行を直接行うコードとは分離されています（データ処理／分析中心）。DB への書き込みは ON CONFLICT 等で冪等性を確保しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、自動トークンリフレッシュ、ページネーション対応）
  - pipeline: 差分 ETL / 日次 ETL 実装（prices, financials, market calendar）
  - schema / audit: DuckDB スキーマ／監査ログ初期化ユーティリティ
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出（SSRF / XML 攻撃対策、サイズ制限）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats, features: Z-score 正規化等の統計ユーティリティ
  - calendar_management: JPX カレンダー管理・営業日計算ユーティリティ
- research/
  - factor_research: Momentum / Value / Volatility ファクター計算
  - feature_exploration: forward returns、IC（Spearman）や統計サマリー等
- settings/config: .env 自動ロード、環境変数管理（必須変数チェック）
- audit / execution / strategy / monitoring: スケルトン的なパッケージ構成（拡張用）

---

## 前提条件

- Python 3.10+
- 必要な Python パッケージ（最小）:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS）

必要なパッケージはプロジェクトの packaging / requirements に従ってインストールしてください。最小限の手動インストール例:

pip install duckdb defusedxml

（パッケージ配布形態に応じて pip install -e . 等で導入する想定です）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要な依存をインストールします（プロジェクトの requirements.txt / pyproject.toml があればそれを使用）。

   pip install duckdb defusedxml

   または（開発インストール）:

   pip install -e .

3. 環境変数を設定します。ルートに `.env` または `.env.local` を置くと自動的に読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを検出します）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用トークン（必須、使用しない場合でも None にしない設計）
   - SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）

   省略可能 / デフォルトあり
   - KABUSYS_ENV           : development / paper_trading / live （デフォルト development）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると自動 .env ロードを無効化
   - KABU_API_BASE_URL     : kabu API のベースURL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB のパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（monitoring 用）のパス（デフォルト data/monitoring.db）

   サンプル .env (概要)
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化します（初回のみ）。

   Python から:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を別に作る場合:

   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な例）

以下は代表的な利用例です。

- 日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")  # 初回は init_schema
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブを実行する

  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes に有効な銘柄コードセットを渡すと銘柄紐付けまで行います
  counts = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(counts)

- J-Quants から日足を直接取得して保存する

  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched={len(records)} saved={saved}")

- ファクター計算（研究用）

  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 1, 31)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

- Zスコア正規化ユーティリティ

  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])

注意点:
- jquants_client はレート制限やリトライ・401 リフレッシュ等を内包しています。id_token を直接渡してテスト可能です。
- news_collector は SSRF / XML Bomb 等の対策を実装しています。外部 URL 取得時は例外が発生することがあります（ログを確認してください）。

---

## 主要 API / モジュール一覧

- kabusys.config
  - settings: 環境変数を提供（自動 .env ロード、必須チェック）
- kabusys.data
  - jquants_client.py: fetch_* / save_*（daily_quotes, financials, market_calendar）
  - schema.py: init_schema(db_path) / get_connection(db_path)
  - pipeline.py: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - news_collector.py: fetch_rss, save_raw_news, run_news_collection
  - quality.py: run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - stats.py: zscore_normalize
  - calendar_management.py: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - audit.py: init_audit_schema, init_audit_db
- kabusys.research
  - factor_research.py: calc_momentum, calc_volatility, calc_value
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

パッケージ構成（概要）:

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - features.py
  - stats.py
  - calendar_management.py
  - audit.py
  - etl.py
  - quality.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
- execution/
- monitoring/

（README の下部に簡単な tree を付記しています）

---

## ディレクトリ構成（ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - stats.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
    - calendar_management.py
    - news_collector.py
  - monitoring/
    - __init__.py

---

## 運用上の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ初期化は冪等です。init_schema を複数回呼んでも安全です。
- ETL は Fail-Fast ではなく、できる限り全データを収集して品質チェックの結果を返す設計です。結果（ETLResult）内の quality_issues や errors を確認して運用判断してください。
- J-Quants API のレートは守る必要があります（実装内で基本制御あり）。大量の並列リクエストは避けてください。

---

## 追加情報・貢献

この README はコードベースから主要機能を抜粋して記載しています。機能追加やバグ修正、ドキュメント改善は歓迎します。Pull Request をお送りください。

---

以上。必要があれば「使い方」の具体的なサンプルや CI / テスト方法、requirements.txt のテンプレート等も追加で作成します。