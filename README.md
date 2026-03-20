# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
市場データの取得（J-Quants）、DuckDB ベースのデータスキーマ、特徴量計算、シグナル生成、ニュース収集、ETL パイプライン、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダー情報を安全に取得・保存
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の初期化
- 研究成果（research）で作成したファクターを正規化して特徴量を構築
- 特徴量＋AIスコアを統合して売買シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 発注・約定・ポジションの監査ログ管理（トレーサビリティ）

設計方針として、ルックアヘッドバイアス防止、冪等性（DB 保存は ON CONFLICT / DO UPDATE を利用）、およびネットワーク／XML セキュリティ（SSRF 対策、defusedxml）に配慮しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- スキーマ管理
  - DuckDB スキーマ初期化：kabusys.data.schema.init_schema()
- ETL
  - 日次 ETL（一括）：kabusys.data.pipeline.run_daily_etl()
  - 個別 ETL ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
- 研究・特徴量
  - ファクター計算：calc_momentum / calc_volatility / calc_value
  - Z スコア正規化ユーティリティ
  - 特徴量構築：strategy.feature_engineering.build_features()
- シグナル生成
  - strategy.signal_generator.generate_signals()
  - BUY/SELL のルール、Bear レジーム判定、エグジット（ストップロス等）
- ニュース収集
  - RSS 取得と前処理（SSRF 対策、URL 正規化）
  - raw_news 保存、news_symbols 紐付け
- 監査 / 発注ログ
  - signal_events / order_requests / executions 等の監査テーブル定義
- 設定管理
  - 環境変数ベースの Settings（自動 .env ロード機能）

---

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   最低限必要なパッケージ（例）
   ```
   pip install duckdb defusedxml
   ```
   パッケージ化されている場合は：
   ```
   pip install -e .
   ```

4. 環境変数（.env）を設定  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi    # 任意
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   設定値は `kabusys.config.settings` 経由で参照できます。

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```
   これにより必要なテーブル・インデックスが作成されます。

---

## 使い方（簡単な例）

以下は主要なワークフローのサンプルです。実運用ではログ出力・エラーハンドリング・スケジューラを組み合わせて使用します。

- 日次 ETL を実行してデータを取得・保存する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を構築する
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2026, 1, 31))
  print(f"built features for {count} symbols")
  ```

- シグナルを生成する
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  signals_count = generate_signals(conn, target_date=date(2026, 1, 31), threshold=0.6)
  print(f"generated {signals_count} signals")
  ```

- ニュース収集を実行する
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- J-Quants からデータを直接フェッチして保存する例
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

---

## 設定・挙動に関する補足

- 環境変数は `kabusys.config.Settings` 経由で取得されます。 `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかで、`LOG_LEVEL` は標準的なロギングレベルを指定します。
- .env の自動読み込み順序は OS 環境変数 > .env.local > .env（.env.local が .env を上書きする）。
- DuckDB はファイルベースの軽量 OLAP DB で、KabuSys の内部データストアとして採用しています。初期化は `init_schema()` を使用してください。
- J-Quants API 呼び出しはレートリミット・リトライ（指数バックオフ）・401 リフレッシュに対応しています。
- RSS ニュース収集は SSRF 対策（リダイレクト先の検証、プライベートアドレス拒否）、gzip 上限、XML 注入対策（defusedxml）などの安全対策を行っています。

---

## ディレクトリ構成（主要ファイル）

（パッケージのルートは `src/kabusys`）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込み / Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + 保存）
    - news_collector.py — RSS ニュース収集・前処理・保存
    - schema.py — DuckDB スキーマ定義と init_schema()
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - features.py — features に関するユーティリティ（再エクスポート）
    - calendar_management.py — 市場カレンダー管理 / 営業日ユーティリティ
    - audit.py — 監査ログ用テーブル定義
    - (その他: quality.py 等が想定される)
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量構築 pipeline（build_features）
    - signal_generator.py — シグナル生成ロジック（generate_signals）
  - execution/ — 発注 / 約定関連（パッケージ化の想定）
  - monitoring/ — 監視・メトリクス用（想定）

---

## 開発・運用上の注意

- DB 初期化は一度だけ行えば良く、既存テーブルはスキップされるため安全です（冪等）。
- ETL は個別ジョブ（prices / financials / calendar）を個別に呼べるため、ジョブスケジューラに組み込みやすくなっています。
- シグナル生成ロジックは外部依存を持たない（DB 上の features / ai_scores を参照）ため、MLOps や別プロセスでの ai_scores 更新と組み合わせ可能です。
- 実際の発注（証券会社 API）や execution 層の実装はこのコードベースの外側で行い、監査ログに書き込む設計です。
- 本番運用時は KABUSYS_ENV を `live` に設定し、設定値（API トークン等）を安全なシークレット管理で管理してください。

---

## 参考（よく使う API / 関数一覧）

- 設定
  - kabusys.config.settings (Settings インスタンス)
- DB スキーマ
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)
- ETL
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- データ取得 / 保存
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
- 研究 / ファクター
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
- 特徴量 / シグナル
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
- ニュース
  - kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - kabusys.data.news_collector.extract_stock_codes(text, known_codes)

---

## ライセンス / コントリビューション

README に含めるべきライセンスやコントリビューションガイドはリポジトリに合わせて追加してください。

---

README に記載されていない細かい仕様や運用ルールは、コード内の docstring（各モジュール冒頭）を参照してください。必要であれば README をプロジェクト特有の運用手順（CI/CD、cron 設定、Secrets 管理）に合わせて追記できます。