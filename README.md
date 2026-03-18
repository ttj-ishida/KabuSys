# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログなどを含むデータプラットフォーム／リサーチ／実行基盤の基礎実装を提供します。

主な設計方針
- DuckDB を中心としたローカルデータレイク設計（冪等な INSERT / ON CONFLICT 処理）
- J-Quants API からの差分取得（レート制御・リトライ・トークン自動リフレッシュ）
- News RSS 収集での SSRF / XML Bomb 対策
- ETL／品質チェック／監査ログによりトレーサビリティとデータ健全性を担保
- Research モジュールは本番取引 API にアクセスせず、価格・財務データのみで完結

----

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（例: JQUANTS_REFRESH_TOKEN）
- データ取得（data.jquants_client）
  - 日次株価（OHLCV）、財務四半期データ、JPXマーケットカレンダーの取得（ページネーション対応）
  - レートリミッター、リトライ、401時のトークン自動リフレッシュ
  - DuckDB へ冪等に保存する save_* 関数
- ETL パイプライン（data.pipeline）
  - 差分更新ロジック、バックフィル、カレンダー先読み
  - 日次 ETL 実行エントリポイント run_daily_etl
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合などを検出して QualityIssue を返す
- DuckDB スキーマ定義・初期化（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema / get_connection ユーティリティ
- ニュース収集（data.news_collector）
  - RSS フィード取得、URL 正規化、記事ID生成（SHA-256）、前処理、DB 保存、銘柄抽出
  - SSRF 対策、Content-Length チェック、gzip 解凍上限などの防御機構
- リサーチ（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - zscore 正規化ユーティリティの再エクスポート
- 監査ログ（data.audit）
  - signal → order_request → executions のトレーサビリティ用テーブル群
  - init_audit_schema / init_audit_db

----

## セットアップ手順（開発環境向け）

前提
- Python 3.10 以上（| 型ヒントを使用）
- ネットワークアクセス可能（J-Quants API、RSS）

推奨パッケージ（最低限）
- duckdb
- defusedxml

例（仮想環境を使う）
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# （プロジェクト配布パッケージがある場合）pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
- SLACK_BOT_TOKEN        : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID       : Slack 通知先チャンネルID（必須）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL              : ログレベル ("DEBUG","INFO",...)

.env ファイル例（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動環境読み込みの無効化（テストなど）:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みをスキップします。

----

## 使い方（簡単なコード例）

以下は代表的なユースケースの最小例です。実行前に必要な環境変数を設定してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ":memory:" でインメモリ DB、またはファイルパスを指定
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J-Quants から差分取得して保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブを走らせる
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")

# known_codes は銘柄抽出に使う有効コード集合（省略可）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) ファクター計算（Research）
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 正規化（例）
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) J-Quants から日足を直接取得して保存
```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(saved)
```

注意: 実運用での発注や Slack 通知などは本 README の例では触れていません。kabu ステーション連携や監査ログ機能を使う場合は別途認証情報・運用フローが必要です。

----

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得 & 保存）
    - news_collector.py         # RSS ニュース収集・DB保存
    - schema.py                 # DuckDB スキーマ定義・初期化
    - stats.py                  # 統計ユーティリティ（zscore など）
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - quality.py                # データ品質チェック
    - calendar_management.py    # 市場カレンダー更新 / 営業日判定
    - audit.py                  # 監査ログ（signal/order/execution）
    - features.py               # 特徴量ユーティリティ再エクスポート
    - etl.py                    # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py        # モメンタム / ボラ / バリュー計算
    - feature_exploration.py    # 将来リターン / IC / サマリー
  - strategy/                    # 戦略関連（空のパッケージ）
  - execution/                   # 発注実行関連（空のパッケージ）
  - monitoring/                  # 監視関連（空のパッケージ）

----

## 開発メモ / 運用注意

- DuckDB ファイルのバックアップとサイズ管理を行ってください。
- J-Quants API のレート制限（120 req/min）に従う必要があります。jquants_client はレート制御を含みます。
- run_daily_etl は各ステップで例外をキャッチして処理を継続します。戻り値の ETLResult で quality_issues / errors を確認してください。
- NewsCollector は RSS の XML をパースします。外部入力の安全対策（defusedxml、SSRF 検査、サイズ上限）を実装していますが、運用時は信頼できるフィードのみの利用を推奨します。
- 実際の売買（live）を行う場合、KABUSYS_ENV を適切に設定し、kabu/API 周りの認証情報・安全回線を用意してください。実口座での発注には十分なリスク管理が必要です。

----

必要があれば、README に以下の追記を行えます：
- CI / テスト実行方法（ユニットテスト例）
- 推奨パッケージバージョン（requirements.txt）
- 実運用でのワークフロー例（デイリーバッチ cron / Airflow など）
- 監視・アラート設定（Slack 通知例）

追加で補足したい項目や、実際に README に含めたいサンプル .env.example を作成するなど、ご希望があれば対応します。