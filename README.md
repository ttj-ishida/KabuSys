# KabuSys

日本株向けの自動売買データ基盤＋戦略ライブラリです。  
DuckDB をデータストアとして用い、J-Quants API / RSS ニュース等からデータを取得・保存し、研究（research）で定義したファクターを計算して特徴量・シグナル生成までの基本的なワークフローを提供します。

この README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python モジュール群です。

- J-Quants API から株価（日足）・財務・市場カレンダーを取得して DuckDB に保存する ETL（差分更新／冪等保存）
- RSS からニュースを収集して原データ（raw_news）に保存し、銘柄紐付けを行う
- 研究用ファクター（モメンタム、ボラティリティ、バリュー等）を計算する research モジュール
- ファクター正規化 → features テーブルへ保存する strategy.feature_engineering
- features と AI スコアを統合して売買シグナル（BUY/SELL）を生成する strategy.signal_generator
- DuckDB スキーマ定義・初期化ユーティリティ、マーケットカレンダー管理、ETL パイプラインなどのデータ基盤ユーティリティ

設計上のポイント：
- DuckDB を永続ストアとして使用（:memory: も可）
- 冪等性を重視（ON CONFLICT / トランザクションでの置換）
- ルックアヘッドバイアス回避のため「target_date 時点のデータのみ」を使用
- ネットワーク関連での堅牢性（レートリミット、リトライ、SSRF 対策など）

---

## 機能一覧

主要な機能（モジュール別）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）と環境変数管理
  - 必須設定の取得（J-Quants / Slack / DB パス等）

- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（株価、財務、カレンダー）
  - レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）

- kabusys.data.schema
  - DuckDB 用のスキーマ（raw / processed / feature / execution 層）の定義と init_schema()

- kabusys.data.pipeline
  - run_daily_etl: 市場カレンダー、株価、財務の差分ETL + 品質チェック実行
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）

- kabusys.data.news_collector
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出と紐付け
  - SSRF/サイズ制限/XML ハードニング対応

- kabusys.research
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 研究ユーティリティ: calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features: research の生ファクターを正規化・フィルタ・features テーブルへ保存
  - generate_signals: features + ai_scores から final_score を計算し signals テーブルへ保存（BUY/SELL）

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job によるカレンダー差分更新

- その他
  - 統計ユーティリティ（zscore_normalize）
  - 監査ログ（audit モジュール）や execution 層のテーブル定義

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（typing のユニオン記法等で 3.10+ 機能を使う場合があるため、実プロジェクトでは pyproject.toml を確認してください）
- DuckDB を使用（Python パッケージ duckdb が必要）
- defusedxml（RSS 用の XML パース安全化）

例: 仮想環境を作って依存をインストールする手順（プロジェクトに pyproject.toml / requirements がある前提）:

1. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに pyproject.toml または requirements.txt があればそれを用いてインストールしてください）

3. ソースをインストール（ローカル開発）
   ```
   pip install -e .
   ```
   または単に PYTHONPATH を通して import できるように配置してください。

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

5. 環境変数 (.env) を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（設定を自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意/デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)
     - KABUS_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は主要なユースケースの簡単な Python スニペット例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# これで全テーブルが作成されます
```

2) 日次 ETL 実行（J-Quants からの差分取得・保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ファクター計算 → features 作成
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（features + ai_scores → signals）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
signals_written = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {signals_written}")
```

5)ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードの集合（銘柄抽出に使用）
known_codes = {"7203", "6758", "9433"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注:
- これらの関数は DuckDB 接続を引数に取り、内部でトランザクションや冪等保存を行います。
- 実運用ではログ設定、監視、Slack 通知、スケジューラ（cron / Airflow 等）と連携してください。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env をプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動読み込みし、settings オブジェクト経由で各種設定を参照できます。
  - settings.jquants_refresh_token / settings.duckdb_path / settings.env など。

- kabusys.data.schema
  - init_schema(path) で DuckDB ファイルを初期化。:memory: も可。

- kabusys.data.jquants_client
  - fetch_* と save_* が対になっており、API から取得して DuckDB に安全に保存します。
  - 内部に RateLimiter と retry ロジックあり。401 の場合はリフレッシュトークンから自動再取得。

- kabusys.data.pipeline
  - run_daily_etl はカレンダー→株価→財務→品質チェックのフローを実行し、ETLResult を返します。

- kabusys.research / kabusys.strategy
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いてファクター計算
  - build_features: ファクターを統合、ユニバースフィルタ、Z スコア正規化、features テーブルへ UPSERT
  - generate_signals: features と ai_scores を統合して final_score を計算し、BUY/SELL を signals テーブルへ保存（Bear レジーム抑制・ストップロス判定等を実装）

---

## ディレクトリ構成（主要ファイル）

（src/ を Python パッケージルートとして想定）

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
  - execution/ (発注実装を置く場所、現状空の __init__ 等)
  - monitoring/ (監視用 DB やログ連携を置く想定)

各モジュールは役割ごとに分離され、DuckDB の同一コネクションを受け渡して処理します。

---

## 注意点 / 運用メモ

- .env 自動読み込みはプロジェクトルート検出に依存します。テストや一部の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- DuckDB の初期化（init_schema）は一度で十分です。既存スキーマがあればスキップされ、DDL は冪等に設計されています。
- J-Quants API のレートリミットやトークン管理を守るため、直接大量リクエストを投げる用途では注意してください（jquants_client は 120 req/min を想定）。
- RSS フィード取得には SSRF 対策やサイズ制限が組み込まれていますが、外部フィードの追加時は信頼性とパフォーマンスを確認してください。
- マネージド運用時は監査テーブル（audit）や signal/event の永続化によりトレーサビリティを確保してください。

---

## ライセンス・貢献

（プロジェクトに LICENSE ファイルがあればその旨を記載してください。ここでは記載を省略します）

---

この README はコードベースの主要な使い方と構成を要約したものです。各モジュールの docstring に詳細な設計やパラメータ仕様があるため、実装や拡張を行う際は該当ファイルのコメントも参照してください。必要でしたら、この README を英語版に翻訳したり、運用ガイド（デプロイ／監視／バックテスト）を追記します。