# KabuSys

日本株自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ収集（J-Quants / RSS）、DuckDB ベースのデータ基盤、ファクター計算、特徴量生成、シグナル生成、監査・実行レイヤーのスキーマ・ユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発に必要な以下のレイヤーを提供する Python パッケージです。

- データ取得（J-Quants API）と保存（DuckDB）
- ニュース収集（RSS）と記事→銘柄紐付け
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Z スコア正規化等）
- シグナル生成（BUY/SELL ロジック、Bear レジーム抑制、エグジット判定）
- スキーマ初期化・ETL パイプライン・カレンダー管理・監査ログ用テーブル

設計上のポイント：
- ルックアヘッドバイアスを避けるため、target_date 時点で利用可能なデータのみを使用
- DuckDB を永続ストレージとして使用し、SQL+Python の組合せで処理
- 冪等性（ON CONFLICT / INSERT DO NOTHING 等）とトランザクションで整合性を保つ
- ネットワーク処理での安全対策（SSRF対策、XML攻撃対策、レスポンスサイズ制限等）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン取得、自動リフレッシュ、ページネーション、レート制御、retry）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）

- data/news_collector.py
  - RSS 取得（SSRF・gzip・XML 安全対策）
  - 記事正規化・ID生成（URL 正規化→SHA256）
  - raw_news 保存、news_symbols（記事⇄銘柄紐付け）
  - extract_stock_codes（記事から 4 桁コード抽出）

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema()：データベース初期化（テーブル・インデックス作成）

- data/pipeline.py
  - 日次 ETL（run_daily_etl）
  - 差分更新（prices / financials / calendar）、品質チェック呼び出し

- data/calendar_management.py
  - market_calendar の更新ジョブ、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）

- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）

- research/*
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算 / IC（Spearman） / ファクター統計サマリ

- strategy/*
  - feature_engineering.build_features（raw factor を正規化して features テーブルへ保存）
  - signal_generator.generate_signals（features + ai_scores を統合して signals を作成）

- config.py
  - 環境変数管理（.env 自動読み込み、必須変数チェック、settings オブジェクト経由でアクセス）

---

## セットアップ手順

必要条件
- Python 3.10 以上（コード中で | 型演算子等を使用）
- DuckDB（Python パッケージ）
- defusedxml（ニュース収集の XML パース保護）

推奨: 仮想環境を利用

例（UNIX 系）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

リポジトリルートに `.env` を作成してください。config.Settings が自動で .env を読み込みます（.git または pyproject.toml があるディレクトリをプロジェクトルートとして探索）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨する .env の例（実運用では機密情報を適切に管理してください）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

データベース初期化:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

---

## 使い方（主要な利用例）

1) DB 初期化（1回）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリも自動作成
```

2）日次 ETL 実行（市場カレンダー・株価・財務の差分取得と保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3）特徴量ビルド（features テーブルへ）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, date.today())
print(f"features updated: {count}")
```

4）シグナル生成（signals テーブルへ）
```python
from datetime import date
from kabusys.strategy import generate_signals

num = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals generated: {num}")
```

5）ニュース収集（RSS → raw_news & news_symbols）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出で利用する有効コード集合（省略可）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)
```

6）J-Quants から直接データを取得して保存する（テストやバックフィル）
```python
from kabusys.data import jquants_client as jq
from datetime import date

records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
```

ログレベルは環境変数 `LOG_LEVEL` で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

注意点:
- run_daily_etl 等の関数は例外管理を行いますが、実運用では例外ログや監視（Slack 通知等）を組み合わせてください。
- generate_signals は AI スコア（ai_scores テーブル）と組み合わせて動作します。ai_scores がない場合は中立値で補完されます。
- build_features / generate_signals はそれぞれ target_date に対して日付単位の置換（DELETE -> INSERT）で冪等に設計されています。

---

## 環境変数（settings で参照される主要キー）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知対象チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL (任意) — ログレベル（デフォルト "INFO"）

config.Settings は未設定の必須変数にアクセスすると ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュール構成（src/kabusys 以下）です。実際のファイル数は開発中に増える可能性があります。

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
    - (その他 data 関連モジュール)
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
  - monitoring/ (パッケージとして定義済みだが詳細は実装に依存)

主要なエントリポイント:
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.strategy.build_features(...)
- kabusys.strategy.generate_signals(...)

---

## 開発・運用上の注意

- Python の型記法（|）や typing の利用から Python 3.10 以上を想定しています。
- DuckDB のバージョンによっては外部キーや ON DELETE の挙動が限定的なため、DDL にコメントでフォールバック方法が記載されています。DuckDB の挙動に合わせて運用ルール（削除順序など）を定めてください。
- J-Quants API のレート制御・リトライは組み込まれていますが、運用時は API 利用制限やトークン管理に注意してください。
- ニュース収集では外部ネットワークを扱うため SSRF 対策や XML パースの保護（defusedxml）を導入しています。カスタム RSS を追加する際も検証を行ってください。

---

## 参考（よく使うコードスニペット）

DB 初期化 + 日次 ETL + 特徴量 + シグナル生成のワンライナー（運用スクリプトの例）:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

conn = init_schema(settings.duckdb_path)
etl_res = run_daily_etl(conn)
trading_day = etl_res.target_date
build_features(conn, trading_day)
generate_signals(conn, trading_day)
```

---

README はここまでです。必要であれば以下を追加できます：
- requirements.txt / Poetry 設定例
- .env.example のテンプレートファイル
- よくあるトラブルシュート（DB ロック、API エラー、news_collector の XML 例外対応など）
- CI / 自動バックフィルジョブのサンプル systemd / cron 設定

追加してほしいセクションがあれば教えてください。