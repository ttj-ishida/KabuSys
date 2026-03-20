# KabuSys

日本株自動売買システムのライブラリ群（ミニマム実装）。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、カレンダー管理、監査ログ用スキーマ等を含むモジュール群を提供します。

## 概要
KabuSys は以下の責務を分離して実装したモジュール群です。

- J-Quants API からのデータ取得（株価 / 財務 / カレンダー）
- DuckDB を用いたデータスキーマと永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得 + 品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量正規化（Z スコア）と features テーブルへの保存
- シグナル生成（重み付け統合・売買シグナルの BUY/SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定・次/前営業日検索）
- 監査ログ（signal → order → execution のトレース）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、すべて target_date 時点のデータのみを使用
- DuckDB へは冪等な保存（ON CONFLICT / トランザクション）を採用
- 外部ライブラリへの依存は最小限（DuckDB, defusedxml 等）

## 主な機能一覧
- data.jquants_client: J-Quants API クライアント（レート制御・再試行・自動トークンリフレッシュ）
- data.schema: DuckDB スキーマ定義と初期化（init_schema）
- data.pipeline: 日次 ETL 実行（run_daily_etl）, 個別 ETL ジョブ（run_prices_etl 等）
- data.news_collector: RSS 収集・保存・銘柄抽出（run_news_collection）
- data.calendar_management: JPX カレンダー管理（is_trading_day / next_trading_day 等）
- research.factor_research: momentum / volatility / value のファクター計算
- strategy.feature_engineering: ファクター統合・Zスコア正規化（build_features）
- strategy.signal_generator: final_score 計算と BUY/SELL シグナル生成（generate_signals）
- data.stats: zscore_normalize（クロスセクション正規化）
- config: 環境変数管理（.env 自動ロード、必須チェック、設定プロパティ）

## 必要条件
- Python 3.10 以上（モジュールは typing の新構文（|）を使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# または requirements.txt を用意して pip install -r requirements.txt
```

## 環境変数
config.py によりプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（CWD に依存せず、パッケージ配布後も正しく動作）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

オプション（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB データベースファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

設定取得例（Python）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path  # pathlib.Path
```

## セットアップ手順（ローカル）
1. Python 3.10+ をインストール
2. 依存パッケージをインストール
   - pip install duckdb defusedxml
3. リポジトリをクローンしてプロジェクトルートへ移動
4. .env を作成（.env.example を参考に必須変数を設定）
5. DuckDB スキーマを初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

## 使い方（主要な操作例）

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って ETL や戦略処理を実行
```

- 日次 ETL（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ファーチャー構築（features テーブルへ保存）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"upserted {n} features")
```

- シグナル生成（signals テーブルへ保存）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"generated {count} signals")
```

- ニュース収集と銘柄紐付け
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 抽出対象の有効銘柄コードセット（例: {'7203','6758',...}）
res = run_news_collection(conn, known_codes={'7203','6758'})
print(res)  # {source: saved_count, ...}
```

- カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

## 注意点 / 運用上のヒント
- J-Quants の API レート制限（120 req/min）を内部で順守する実装がありますが、長時間のフルバックフィル等は注意してください。
- 自動トークンリフレッシュや HTTP の再試行ロジックは組み込まれています（一定回数の指数バックオフ）。
- features / signals 等は target_date ごとの日付単位置換（削除→挿入）で冪等性を保ちます。
- KABUSYS_ENV を `live` にすると本番口座動作フラグとなるため、発注周りや通知の動作に注意してください（本実装では execution 層の具体的注文送信は別実装を想定）。
- .env はプロジェクトルートの .git または pyproject.toml を基に自動検出されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイル・モジュール構成（src/kabusys）:

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
    - (その他 ETL / 品質チェック関連モジュール)
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
  - monitoring/
    - (監視・メトリクス用モジュール置き場)

（上記は本 README に含まれる主要モジュールを抜粋しています。実際のファイル一覧はリポジトリのツリーをご参照ください。）

---

問題報告・改善提案があれば、利用時のログや実行例（簡単な再現スクリプト）を添えて共有してください。README に追加してほしいサンプルや運用手順（cron / Airflow 等）を指定いただければ、具体例を追記します。