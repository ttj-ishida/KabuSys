# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants など外部データソースから市場データを取得し、DuckDB に保存。ETL、データ品質チェック、特徴量計算、ニュース収集、ファクターリサーチなど、トレーディングシステムのデータ基盤とリサーチ機能を提供します。

主な設計方針は「冪等性」「Look-ahead bias 回避」「テストしやすさ」「外部ライブラリ依存の最小化（標準ライブラリでの実装を優先）」です。

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須設定チェック）
- J-Quants API クライアント
  - token リフレッシュ、自動再試行、レート制御、ページネーション
  - 株価日足・財務データ・マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT を使用）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン
  - 差分取得、バックフィル、カレンダー先読み
  - 品質チェックの実行（欠損・スパイク・重複・日付整合性）
- ニュース収集
  - RSS フィード取得、前処理（URL除去・正規化）、SSRF 対策、記事保存、銘柄抽出
- ファクター計算（Momentum / Volatility / Value 等）
- 研究用ユーティリティ
  - 将来リターン計算、IC（Spearman）算出、統計サマリー、Zスコア正規化
- 監査ログ（信号→発注→約定のトレーサビリティ）スキーマ
- カレンダー管理（営業日の判定、前後営業日の取得）

---

## 必要環境 / 依存パッケージ

- Python 3.9+（typing の構文や型ヒントを前提）
- 必須ライブラリ（少なくとも開発環境にはインストールしてください）
  - duckdb
  - defusedxml

例（pip）:
```bash
pip install duckdb defusedxml
```

（プロジェクト配布方法に依存して追加の依存関係がある場合は pyproject.toml や requirements.txt を参照してください。）

---

## 環境変数 / .env

プロジェクトはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV: development / paper_trading / live（デフォルト `development`）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト `INFO`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 必要な依存をインストール
   ```bash
   pip install duckdb defusedxml
   # 追加ツールやテスト用に他の依存があれば適宜インストール
   ```

3. 環境変数を設定（上記 .env をプロジェクトルートに配置するかエクスポート）

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成
   # or use in-memory
   # conn = init_schema(":memory:")
   ```

5. 監査ログ用スキーマ初期化（必要なら）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的な利用例）

1. 日次 ETL 実行（市場データの取得・保存・品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. J-Quants から株価を直接取得して保存
   ```python
   from kabusys.data import jquants_client as jq
   import duckdb

   conn = duckdb.connect("data/kabusys.duckdb")
   # トークンは環境設定から自動取得される
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved_count = jq.save_daily_quotes(conn, records)
   print("saved:", saved_count)
   ```

3. ファクター計算（モメンタム／ボラティリティ等）
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

   conn = duckdb.connect("data/kabusys.duckdb")
   d = date(2024, 3, 1)
   mom = calc_momentum(conn, d)
   vol = calc_volatility(conn, d)
   val = calc_value(conn, d)
   ```

4. 将来リターン・IC 計算
   ```python
   from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
   from kabusys.data.stats import zscore_normalize
   # forward returns
   fwd = calc_forward_returns(conn, date(2024,3,1), horizons=[1,5,21])
   # factor_records は例えば calc_momentum の戻り値を正規化した結果
   normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
   # IC（Spearman）
   ic = calc_ic(normalized, fwd, factor_col="mom_1m", return_col="fwd_1d")
   ```

5. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes は銘柄コード集合（抽出用）
   known_codes = {"7203", "6758", "6954", ...}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

---

## API の主要ポイント（簡易ドキュメント）

- kabusys.config.settings
  - 環境変数から各種設定を参照（例: settings.jquants_refresh_token）
  - .env / .env.local を自動で読み込み（プロジェクトルート検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（テーブル作成）
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - extract_stock_codes(text, known_codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)
  - zscore_normalize(records, columns) （kabusys.data.stats から再エクスポート）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境設定／.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - news_collector.py     — RSS ニュース収集、前処理、保存、銘柄抽出
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（差分取得・品質チェック）
    - features.py           — 特徴量ユーティリティ（再エクスポート）
    - stats.py              — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py— 市場カレンダー管理（営業日判定等）
    - audit.py              — 監査ログスキーマ（信号〜約定トレーサビリティ）
    - quality.py            — データ品質チェック
    - etl.py                — ETLResult 型の公開
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py           — 将来の戦略実装用パッケージ
  - execution/
    - __init__.py           — 発注・ブローカー連携用パッケージ
  - monitoring/
    - __init__.py           — 監視・メトリクス関連（空のエントリあり）

---

## 開発上の注意 / 補足

- DuckDB の SQL 実行はパラメータバインド（?）を使用しており、SQL インジェクション対策が施されています。
- ニュースの RSS 取得は SSRF 対策・レスポンスサイズ制約・gzip 解凍制御などセキュリティ考慮あり。
- J-Quants の API 呼び出しはレート制御（120 req/min）と再試行ロジックを内蔵しています。401 発生時のトークン自動リフレッシュもサポート。
- テストや CI では環境変数読み込みの自動化を無効にするために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- DuckDB のトランザクション管理については一部関数で明示的に BEGIN/COMMIT を使っているため、外部でトランザクションを開いている場合は注意してください（関数のドキュメント参照）。

---

README の内容はコードベースから抜粋した概要と使用例です。実際の運用や拡張を行う際は、個別モジュール（data/jquants_client.py, data/pipeline.py, research/* など）の docstring と例を参照してください。必要があれば具体的な使用例や運用手順（cron、バッチ化、監視フロー）について追記します。