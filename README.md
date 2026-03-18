# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants からの市場データ取得、DuckDB でのスキーマ管理・ETL、ニュース収集、ファクター計算（リサーチ用）、監査ログや実行関連スキーマまでを包含するモジュール群を提供します。

主な用途:
- 市場データの差分取得・保存（株価・財務・市場カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース（RSS）収集と銘柄紐付け
- ファクター（Momentum / Value / Volatility 等）の計算および IC / 統計解析
- DuckDB ベースのスキーマ初期化と監査ログ（発注/約定トレース）

---

## 機能一覧（主な機能）

- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）、DuckDB への保存関数
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得、保存、品質チェック）の実行
  - news_collector: RSS 収集、前処理、DB 保存、銘柄抽出・紐付け（SSRF対策・gzip/サイズ制限等）
  - calendar_management: JPX カレンダー管理（営業日判定、次/前営業日の計算、バッチ更新）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査（signal/order/execution）スキーマ初期化
  - stats / features: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
- config: 環境変数読み込み・設定管理（.env 自動ロード、設定プロパティ）
- execution / strategy / monitoring: 発注・戦略・モニタリングの土台（パッケージ名として公開）

設計方針の特徴:
- DuckDB を中心としたローカルデータレイク設計（冪等性を重視：ON CONFLICT を活用）
- 本番口座や発注 API へ直接アクセスしないモジュール（データ取得・研究用と発注系を分離）
- 外部依存は最小限（ただし DuckDB や defusedxml 等が必要）
- セキュリティ考慮（RSS の SSRF 対策、XML の安全パーサー、HTTP レスポンスサイズ制限 等）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型記法や union 型を使用）
- 必須ライブラリ（少なくとも次をインストールしてください）:
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging, datetime, math など）を使用

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または requirements.txt を用意している場合:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化する
2. 依存パッケージをインストールする（duckdb, defusedxml 等）
3. 環境変数の設定（.env ファイルをプロジェクトルートに置くことを推奨）

.env 自動ロード挙動:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を探索し、`.env` → `.env.local` の順で自動ロードします。
- OS 環境変数は上書きされません（.env の override は .env.local のみ可能）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨する .env のキー（例）:
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<kabu_api_password>
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

必須環境変数（実行時に Settings が参照）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

---

## 使い方（簡単な例）

以下は代表的な操作のサンプルです。適宜 import パスを調整して実行してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB
```

2) 日次 ETL の実行（J-Quants トークンは settings が参照）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection, init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 市場カレンダー更新ジョブ（夜間バッチ等で実行）
```python
from kabusys.data.calendar_management import calendar_update_job
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

4) RSS ニュース収集と DB 保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 事前に有効コードセットを用意
results = run_news_collection(conn, sources=None, known_codes=known_codes, timeout=30)
print(results)
```

5) ファクター計算（リサーチ）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
momentum = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
value = calc_value(conn, target)

# 将来リターン算出（翌日・翌週・翌月）
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC を計算
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# 統計サマリー
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
print(summary)
```

6) Zスコア正規化（特徴量正規化）
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 主要 API（抜粋）

- kabusys.config.settings: アプリ設定（プロパティ経由で環境変数を取得）
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ作成・接続取得
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline.run_daily_etl: 日次 ETL 実行（品質チェック含む）
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.quality.run_all_checks: データ品質チェックの一括実行
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats.zscore_normalize

---

## 環境変数の詳細（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- KABUSYS_ENV : 実行環境 ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL : ログレベル（"DEBUG", "INFO", ...）。デフォルト "INFO"
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須) : Slack 通知に使用
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効にする（値が設定されていると無効）

注意: Settings の必須プロパティ参照時に未設定だと ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（fetch / save 実装）
    - news_collector.py        # RSS 収集・前処理・DB 保存
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # 市場カレンダー管理・ユーティリティ
    - stats.py                 # zscore_normalize 等の統計ユーティリティ
    - features.py              # features の公開インターフェース
    - audit.py                 # 監査ログ（signal/order/execution）スキーマ
    - etl.py                   # ETLResult の再エクスポート
    - quality.py               # データ品質チェック
  - research/
    - __init__.py
    - factor_research.py       # Momentum/Volatility/Value の計算
    - feature_exploration.py   # 将来リターン / IC / summary / rank
  - strategy/                   # 戦略層（パッケージプレースホルダ）
    - __init__.py
  - execution/                  # 発注/実行層（パッケージプレースホルダ）
    - __init__.py
  - monitoring/                 # 監視系（パッケージプレースホルダ）
    - __init__.py

---

## 開発・運用上の注意

- DuckDB の SQL はパラメータバインド（?）を使うことでインジェクションを避けていますが、外部から受け取る値の検証は行ってください。
- RSS 処理は外部ネットワークを扱うため、SSRF や大容量レスポンスなどに対する保護機構が組み込まれています（_SSRFBlockRedirectHandler、MAX_RESPONSE_BYTES、defusedxml 等）。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client は固定間隔スロットリングとリトライを実装しています。大量取得時は制限を守ること。
- 本プロジェクトには本番向けの発注実行ロジック（ブローカー接続）は含まれていないか限定的です。実際の送信コードを実装する際はリスク管理・冪等性を十分に検討してください。
- audit モジュールは監査ログのために UTC タイムゾーン固定やトランザクション制御を行います。監査テーブルは基本的に削除しない運用を想定しています。

---

必要に応じて README に追記・カスタマイズできます。特に実運用に使う場合は、依存パッケージリスト（requirements.txt / pyproject.toml）、CI / デプロイ手順、より詳細な運用チェックリストを追加することを推奨します。