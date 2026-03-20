# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義などを含むモジュール群をまとめています。

---

目次
- プロジェクト概要
- 主な機能
- 動作要件
- セットアップ手順
- 環境変数（.env）
- 使い方（主な API の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリセットです。

- J-Quants API からの株価・財務・カレンダー等の取得と DuckDB への永続化（冪等）
- データ品質チェック・ETL（差分更新・バックフィル対応）
- 研究（research）で作成した生ファクターを用いた特徴量作成（Z スコア正規化など）
- 特徴量＋AIスコアを統合したシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去等）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- DuckDB スキーマ定義・初期化、監査ログ用スキーマ等

設計上のポイント:
- ルックアヘッドバイアス回避のため、target_date 時点のデータのみを用いる実装
- 冪等性（ON CONFLICT / INSERT ... DO UPDATE / RETURNING 等）
- 外部 API 呼び出しのリトライ・レート制御・トークン自動リフレッシュ
- テスト容易性（id_token 注入や関数分割）

---

## 主な機能（機能一覧）

- データ取得 / 保存
  - J-Quants クライアント（kabusys.data.jquants_client）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - レートリミット、リトライ、トークン自動リフレッシュ対応
- データストレージ
  - DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- ETL / バッチ
  - 日次 ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- 特徴量・戦略
  - factor 計算（kabusys.research.factor_research）
  - Z スコア正規化（kabusys.data.stats.zscore_normalize）
  - 特徴量構築（kabusys.strategy.feature_engineering.build_features）
  - シグナル生成（kabusys.strategy.signal_generator.generate_signals）
- ニュース収集
  - RSS 取得・前処理・DB保存（kabusys.data.news_collector.run_news_collection）
  - URL 正規化／SSRF 対策／トラッキングパラメータ除去／記事ID は SHA-256 ベース
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）
- 監査ログ・監査スキーマ（audit モジュール）
- 環境変数管理（kabusys.config.Settings）と自動 .env 読み込み（プロジェクトルート検出）

---

## 動作要件

- Python 3.10 以上（型注釈に PEP 604 の `X | Y` を使用）
- 必要なパッケージ（最小）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, datetime, logging など）を使用

※ 実行環境によっては追加の依存がある場合があります（例: Slack 通知等）。プロジェクト配布パッケージに requirements.txt がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを入手）
   - 例: git clone ...

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .\.venv\Scripts\activate

3. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （もし setuptools に基づくパッケージ構成があれば）pip install -e .

4. データベース初期化（DuckDB）
   - 例: Python で init_schema を呼ぶ（下記参照）

5. 環境変数を設定（.env ファイルをプロジェクトルートに配置することで自動ロードされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

---

## 環境変数（.env）

kabusys.config.Settings で参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（例: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）

簡易 .env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- パーサは Bash ライクな .env をサポート（export キーワードやクォート等に対応）。
- プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

---

## 使い方（主要 API の例）

以下は簡単な Python スニペット例です。実際にはアプリケーション側でエラーハンドリングやログ出力を追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数から取得されます（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn は init_schema の戻り値
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ UPSERT）
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date(2025, 1, 10))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

# threshold や重みをカスタマイズ可能
total = generate_signals(conn, target_date=date(2025, 1, 10), threshold=0.6)
print(f"signals generated: {total}")
```

5) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄コードの集合（extract_stock_codes に利用）
known_codes = {"7203", "6758", "9984", ...}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新の夜間ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

7) J-Quants API を直接使ってデータを取得して保存する
```python
from kabusys.data import jquants_client as jq

records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 開発・テストに関するメモ

- 設定自動読み込みはデフォルトで有効です。ユニットテストなどで自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client や network を伴うモジュールは、ID トークン注入や _urlopen のモックによりテストが可能な設計になっています。
- DuckDB をインメモリで使いたい場合は db_path に ":memory:" を渡せます（init_schema(":memory:")）。

---

## ディレクトリ構成

src 配下の主なファイル・モジュール：

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - news_collector.py              — RSS ニュース収集・前処理・DB保存
    - schema.py                      — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         — マーケットカレンダー管理（営業日判定等）
    - audit.py                       — 監査ログ用スキーマ（signal_events, order_requests, executions）
    - features.py                    — features 用再エクスポート（zscore）
  - research/
    - __init__.py
    - factor_research.py             — momentum / volatility / value の計算
    - feature_exploration.py         — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py         — 特徴量作成 build_features
    - signal_generator.py            — シグナル生成 generate_signals
  - execution/                       — 発注・execution 層（空 __init__ が存在）
  - monitoring/                      — 監視系（未列挙の実装がある想定）

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに補助モジュールやドキュメントが含まれる可能性があります）

---

## ライセンス / 責任範囲

本リポジトリは自動売買ロジック・データパイプラインの基盤を提供しますが、実際の売買に利用する際は必ず十分な検証・リスク管理を行ってください。実運用時には証券会社側 API の仕様、法令、取引リスクに注意してください。

---

補足や README の拡張（具体的な運用手順、cron 設定例、Slack 通知の仕組み、監査ログのクエリ例など）をご希望であれば教えてください。必要に応じて追加セクションを作成します。