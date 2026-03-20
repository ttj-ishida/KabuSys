# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB ベースのスキーマ・監査機構などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能をモジュール化した Python パッケージです。

- J-Quants API を使った株価 / 財務 / 市場カレンダーの取得（Rate limiting、リトライ、トークン自動更新を実装）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量正規化・合成（features テーブルへの UPSERT）
- シグナル生成（最終スコア計算、BUY / SELL 判定、冪等な signals 書き込み）
- ニュース収集（RSS 取得、SSRF/サイズ保護、銘柄抽出、raw_news / news_symbols への保存）
- カレンダー管理・営業日ユーティリティ・監査ログ等

設計方針として「ルックアヘッドバイアス回避」「冪等性」「外部 API に対する堅牢な補助（レート制御/リトライ）」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants への API 呼び出し、ページネーション対応、トークンリフレッシュ、保存用ユーティリティ（save_*）
- data/schema.py
  - DuckDB のスキーマ定義と初期化（init_schema）
- data/pipeline.py
  - 日次 ETL (run_daily_etl)、個別 ETL（株価 / 財務 / カレンダー）実装
- data/news_collector.py
  - RSS 収集・前処理・DB 保存・銘柄抽出
- data/calendar_management.py
  - 営業日判定 / next/prev_trading_day / calendar 更新ジョブ
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）
- research/*, strategy/*
  - 研究用ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）
- config.py
  - 環境変数 / .env 自動読み込み（.git / pyproject.toml を基準にプロジェクトルートを探索）
  - 必須設定の取得（Settings クラス）

---

## 必要環境 / 依存

- Python 3.9+（typing の Union | 等を使用しているため近年の Python を想定）
- duckdb
- defusedxml

インストール例（最低限）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発インストール（プロジェクトの setup.py/pyproject がある場合）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数（設定）

config.Settings で参照される主要な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注等に使用する場合）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
- 任意（デフォルトあり）
  - KABUSYS_ENV           : "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL             : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動で .env/.env.local をプロジェクトルートから読み込みます（OS 環境変数が優先）。
自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .   # または必要な依存を個別に pip install
   ```

2. 必要な環境変数を .env に設定（上記参照）

3. DuckDB スキーマを初期化

   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

   もしくは Python スクリプト内で:

   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema('data/kabusys.duckdb')
   ```

---

## 使い方（よく使う操作例）

以下は代表的な操作のサンプルです。実行前に .env を用意しておいてください。

- DuckDB 接続を取得・初期化

  ```py
  from kabusys.data.schema import init_schema, get_connection

  # 新規作成（テーブル作成）
  conn = init_schema('data/kabusys.duckdb')

  # 既存 DB へ接続（初回は init_schema を推奨）
  conn = get_connection('data/kabusys.duckdb')
  ```

- 日次 ETL を実行（J-Quants から差分取得→保存→品質チェック）

  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 研究側ファクター→特徴量作成→シグナル生成

  ```py
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features, generate_signals

  conn = get_connection('data/kabusys.duckdb')
  t = date.today()

  # 特徴量作成（features テーブルへ保存）
  n_features = build_features(conn, t)
  print("features built:", n_features)

  # シグナル生成（signals テーブルへ保存）
  n_signals = generate_signals(conn, t)
  print("signals:", n_signals)
  ```

- ニュース収集（RSS → raw_news, news_symbols）

  ```py
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  # known_codes に有効な銘柄コード集合を渡すと銘柄紐付けを行う
  results = run_news_collection(conn, known_codes={'7203', '6758', '9984'})
  print(results)  # ソースごとの新規保存件数
  ```

- J-Quants API を直接利用してデータ取得（トークンは Settings から）

  ```py
  from kabusys.data import jquants_client as jq

  # 全銘柄の株価を取得（ページネーション対応）
  daily_quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 主要 API / 公開関数（抜粋）

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（スキーマ作成）
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.research
  - calc_momentum(conn, date)
  - calc_volatility(conn, date)
  - calc_value(conn, date)
  - calc_forward_returns(...)
  - calc_ic(...)

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=None)

- kabusys.config
  - settings: Settings インスタンス（環境変数の参照）

---

## ロギング / 実行モード

- KABUSYS_ENV により実行モードを切り替え（development / paper_trading / live）
  - settings.is_dev / is_paper / is_live で判定可能
- LOG_LEVEL でログレベルを制御（デフォルト INFO）
- .env/.env.local はプロジェクトルート（.git または pyproject.toml を基準）で自動読み込みされます

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイル・モジュールの抜粋です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/          (発注処理等の実装を格納する想定ディレクトリ)
  - monitoring/         (監視・アラート関連)

（上記は現行コードベースの主要モジュールを示しています）

---

## 注意事項 / 実運用への留意点

- 実際に発注を行うモジュール（execution 層）や kabu ステーション連携は別実装／設定が必要です。実運用で使用する前に十分なペーパートレード検証を行ってください。
- 環境変数に含まれるシークレット（トークン等）は安全に管理してください。
- J-Quants のレート制限や API 利用規約を遵守してください。
- DuckDB のファイル配置・バックアップを運用で検討してください（データ破損対策）。
- 本ライブラリはルックアヘッドバイアス回避を設計目標にしていますが、呼び出し側で誤った日時を渡すとバイアスが入る場合があります。target_date の取り扱いに注意してください。

---

## 貢献 / 開発

- バグ報告・機能提案は Issue へお願いします。
- 新機能は既存のスキーマ設計・冪等性原則・トレーサビリティ方針と整合するよう実装してください。

---

必要であれば、README の Usage セクションに CLI 例、より具体的なサンプルスクリプト、あるいはテーブル定義（DataSchema.md 抜粋）の追加もできます。希望する場合はどの情報を深堀りするか教えてください。