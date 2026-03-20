# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、データ品質管理、特徴量エンジニアリング、シグナル生成、発注監査までの基盤的機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを備えた投資システム向けのツールキットです。

- Data layer: J-Quants API から株価 / 財務 / カレンダー / ニュースを取得し、DuckDB に保存
- Processed / Feature layer: prices_daily, features, ai_scores などの中間テーブルを管理
- Strategy layer: 特徴量の正規化・合成（feature_engineering）および最終スコアに基づくシグナル生成（signal_generator）
- Execution / Audit layer: シグナル→発注→約定の監査テーブル設計（schema / audit）
- Research utilities: ファクター計算・将来リターン・IC 等の解析ユーティリティ

設計上のポイント:

- DuckDB をローカル DB として採用し、SQL と純 Python で処理
- 冪等性（ON CONFLICT / upsert）とトランザクションを重視
- Look-ahead bias 回避のため、target_date 時点のデータのみを使用
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュを内包

---

## 機能一覧

主な公開 API / 機能（代表）:

- 環境設定
  - 自動 .env ロード（プロジェクトルートを基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクトから環境変数を取得（JQUANTS_REFRESH_TOKEN 等）

- Data / ETL
  - jquants_client: J-Quants への安全なリクエスト、ページネーション、save_* 関数（保存は冪等）
    - fetch_daily_quotes / save_daily_quotes
    - fetch_financial_statements / save_financial_statements
    - fetch_market_calendar / save_market_calendar
  - pipeline: 差分更新 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - schema: DuckDB スキーマ初期化（init_schema / get_connection）
  - news_collector: RSS 収集・前処理・DB 保存（fetch_rss, save_raw_news, run_news_collection）
  - calendar_management: 営業日判定・next_trading_day など
  - data.stats: zscore_normalize（クロスセクション正規化）

- Research / Strategy
  - research.factor_research: calc_momentum, calc_volatility, calc_value
  - research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - strategy.feature_engineering: build_features（features テーブル生成）
  - strategy.signal_generator: generate_signals（signals テーブル生成）

- Execution / Audit
  - schema に監査・発注関連テーブル定義（signal_events, order_requests, executions 等）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード 等）

依存パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください（本コードスニペットには requirements ファイルは含まれていません）。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（任意）:

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows (PowerShell)
```

2. 必要パッケージをインストール（例）:

```bash
pip install duckdb defusedxml
# またはプロジェクトに requirements があれば:
# pip install -r requirements.txt
```

3. パッケージを編集可能インストール（開発時）:

```bash
pip install -e .
```

4. 環境変数設定（.env 推奨）:
- プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必要な主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<kabu_api_password>
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- DUCKDB_PATH=data/kabusys.duckdb  (省略時のデフォルト)
- SQLITE_PATH=data/monitoring.db    (省略時のデフォルト)
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=INFO|DEBUG|... (デフォルト: INFO)

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（代表的な操作例）

以下は最小限の操作例です。実行は Python スクリプトや REPL から行います。

- DuckDB スキーマ初期化:

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# ":memory:" を渡すとインメモリ DB
```

- 日次 ETL 実行:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡して特定日を処理可能
print(result.to_dict())
```

- 特徴量作成（features テーブル生成）:

```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成:

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {count}")
```

- ニュース収集ジョブ（既知銘柄セットがある場合は紐付け可能）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
result = run_news_collection(conn, sources=None, known_codes=known_codes)
print(result)  # {source_name: saved_count, ...}
```

- J-Quants からのデータ取得は jquants_client 経由で行います（get_id_token / fetch_* / save_*）。

---

## 主要モジュール・関数一覧（抜粋）

- kabusys.config.settings: 環境変数の取得（必須キーは _require で検査）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.get_id_token / fetch_daily_quotes / save_daily_quotes
- kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.stats.zscore_normalize
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
- kabusys.strategy.build_features / generate_signals

詳細な引数・戻り値は各モジュールのドキュメンテーション文字列を参照してください。

---

## ディレクトリ構成

（本コードベースの主要ファイル配置を要約）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他: quality.py 等が想定される)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
      - (execution 層の実装ファイルは別途)
    - monitoring/
      - (監視・メトリクス用モジュール)
- pyproject.toml / setup.cfg / requirements.txt (プロジェクト次第)

---

## 設計上の注意点・運用メモ

- 環境変数は .env / OS 環境変数の順で読み込まれ、.env.local が .env を上書きします。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。
- J-Quants API に対するレート制限（デフォルト 120 req/min）を内部で尊重します。大量取得時は時間分散を考慮してください。
- ETL / DB 書き込みは基本的にトランザクションでまとめ、冪等性を保つように設計されています。
- features / signals の処理は target_date 時点のデータのみを使用することで look-ahead bias を防いでいます。
- DuckDB のバージョンや SQL 機能差に注意（外部キーや ON DELETE の挙動は DuckDB のバージョンに依存）。
- RSS の取得では SSRF 防止・XML 攻撃対策（defusedxml）・サイズ制限を実装しています。

---

## テスト・開発

- モジュールは関数単位で依存注入（id_token, conn 等）できるように設計されているため、ユニットテストで簡単にモックできます。
- ETL の単体テストは DuckDB の ":memory:" を使うと便利です。

---

## 貢献

バグ報告・プルリクエスト歓迎です。設計方針（冪等性・トレース可能性・Look-ahead Bias 回避）を尊重した実装にしてください。ドキュメント文字列とロギングメッセージの充実を重視します。

---

README に書かれている各 API の詳細（引数・戻り値・挙動）については、該当ソースファイルの docstring を参照してください。必要であれば、利用ケース別の具体的なサンプルや運用手順（cron/airflow での日次実行例、監視アラート設定等）も作成します。必要なら指示してください。