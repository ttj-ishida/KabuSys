# KabuSys

日本株向けの自動売買基盤コンポーネント群。データ収集（J-Quants）、ETL、データ品質チェック、特徴量生成、リサーチ用ユーティリティ、ニュース収集、監査ログなどを備えたモジュール群です。本リポジトリはライブラリ形式で提供され、DuckDB をデータストアとして利用します。

## 概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API からの株価・財務・カレンダー等の取得（ページネーション・リトライ・トークン自動更新対応）
- DuckDB を用いた冪等的なデータ保存スキーマ（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と記事→銘柄紐付け処理（SSRF対策・トラッキング除去・受信サイズ制限）
- 研究/特徴量モジュール（モメンタム・ボラティリティ・バリュー等）と IC / 統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレースを可能にする監査テーブル群）
- 設定管理（.env 自動読み込み、必須環境変数チェック）

設計方針としては「本番の発注 API・口座にはアクセスしない」リサーチ／データ基盤としての安全性と冪等性、及び外部攻撃対策（SSRF、XML Bomb 等）を重視しています。

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レート制御、リトライ、401 時トークン自動リフレッシュ、ページネーション）
  - fetch / save の冪等関数（raw_prices / raw_financials / market_calendar）
- data/schema.py
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) で初期化
- data/pipeline.py
  - 日次 ETL（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）
  - 差分取得、バックフィル、品質チェック組み込み
- data/quality.py
  - 欠損・スパイク・重複・日付整合性チェック（QualityIssue を返す）
- data/news_collector.py
  - RSS からのニュース収集、正規化、SSRF対策、raw_news 保存、銘柄抽出と紐付け
- data/calendar_management.py
  - market_calendar の管理、営業日判定ユーティリティ（is_trading_day / next_trading_day 等）
- data/audit.py
  - 監査テーブル群（signal_events / order_requests / executions）初期化ユーティリティ
- research/
  - factor_research.py：mom/volatility/value ファクター計算（DuckDB を参照）
  - feature_exploration.py：将来リターン計算、IC（Spearman）計算、統計サマリ
- data/stats.py
  - zscore_normalize（クロスセクションでの Z スコア正規化）
- config.py
  - .env 自動読み込み（プロジェクトルート判定）、必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の検証

## 要件（推奨）

- Python 3.10 以上（typing の | 演算子や型注釈に依存）
- 必要な Python パッケージ:
  - duckdb
  - defusedxml

（プロジェクトに requirements ファイルが無い場合は最低限上記をインストールしてください）

例:
pip install duckdb defusedxml

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを配置）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他のパッケージを追加）
4. 環境変数設定（.env ファイル）
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` または `.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使用する場合（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携時）
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
     - KABUSYS_ENV — 開発/ペーパー/本番: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）

サンプル .env（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABU_API_PASSWORD="your_kabu_password"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO

.env のパースはシェルライクな記法（export にも対応）を採用しています。クォートやエスケープにも配慮されています。

## 使い方（主要な例）

※ 以下は Python スクリプト内での利用例です。ログ設定や例外処理は適宜追加してください。

- DuckDB スキーマ初期化（最初に一度だけ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行する（J-Quants からの取得→保存→品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ（RSS → raw_news 保存 + 銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # 各ソースの新規保存件数
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 31))
# records は [{"date": ..., "code": "7203", "mom_1m": ..., ...}, ...]
```

- 将来リターンと IC（Information Coefficient）
```python
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
# factor_records は別途 calc_momentum 等で得たもの
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("Spearman IC:", ic)
```

- Z スコア正規化（クロスセクション）
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

- J-Quants のトークンを明示的に取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して ID token を POST で取得
```

## 設定管理のポイント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を起点に行われます。CWD に依存しません。
- 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで利用）。
- settings（kabusys.config.settings）オブジェクトから各種設定にアクセスできます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live）。

## 開発・テストのヒント

- DuckDB のテストには ":memory:" を指定してインメモリ DB を使用可能です。
- news_collector の外部ネットワーク（URLopen）部分はモック可能に設計されています（_urlopen を差し替え）。
- ETL の差分取得は DB の最終取得日を基に自動計算され、backfill_days による再取得を行います。

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - features.py
    - stats.py
    - calendar_management.py
    - audit.py
    - quality.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールは役割ごとに整理されています（data: データ取得/保存/ETL/品質、research: 特徴量計算・分析、audit: 監査ログ定義、config: 環境変数管理）。

## 注意点 / 補足

- J-Quants API のレート制限（120 req/min）を尊重するため、クライアントに固定間隔のレートリミッタが組み込まれています。これを迂回しないでください。
- jquants_client 内では 401 を検知した場合にリフレッシュトークンを使って ID トークンを自動更新するロジックがあります（1 回限りのリトライ）。
- news_collector は外部データ取り込みに関するセキュリティ対策（SSRF / XML Bomb / レスポンスサイズ制限）を実装しています。これらの安全策は簡略化せずに運用してください。
- DuckDB の SQL による DDL / INDEX 作成は冪等（IF NOT EXISTS）になっています。init_schema は必要な親ディレクトリを自動作成します。

---

さらに詳しい使用法や API（個々の関数の引数・戻り値等）はソースコード内の docstring を参照してください。質問や追加で欲しい README 内容（例: CI/デプロイ手順、より詳細なサンプル）あれば教えてください。