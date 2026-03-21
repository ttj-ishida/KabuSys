# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリセット（KabuSys）。  
データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義など、取引アルゴリズムの研究から本番運用までを想定したコンポーネント群を提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は次のレイヤーで構成された日本株自動売買システム向けの共通ライブラリです。

- Data（データ取得・ETL）: J-Quants API から株価／財務／カレンダーを取得し DuckDB に保存する機能。
- Research（研究）: ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索（将来リターン、IC、統計サマリ）。
- Strategy（戦略）: 特徴量の正規化・合成（features の生成）と最終スコア算出による売買シグナル生成。
- Execution / Monitoring: 発注・監視層のためのプレースホルダ（将来的にブリッジを実装）。
- Config: .env / 環境変数からの設定読み込み、検証。

設計上のポイント:
- DuckDB を中心としたローカル永続化（冪等保存、トランザクションを使用）。
- ルックアヘッドバイアス回避のため「target_date 時点のデータのみ」を使用。
- API レート制御（J-Quants）やリトライ、RSS の SSRF 対策など堅牢性に配慮。

---

## 主な機能一覧

- 環境設定読み込みと検証（kabusys.config）
  - .env・.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- データ取得（kabusys.data.jquants_client）
  - J-Quants API から株価・財務・カレンダーのページネーション対応取得
  - レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェックフック
  - 日次 ETL 実行エントリポイント run_daily_etl
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（URL 正規化＋SHA-256）
  - SSRF 対策、サイズ上限、defusedxml による安全なパース
  - raw_news / news_symbols 保存（冪等）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、カレンダー更新ジョブ
- 研究用ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value 等
  - 将来リターン計算、IC（Spearman）算出、統計サマリ
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 生ファクターのマージ、ユニバースフィルタ、Zスコア正規化、features テーブルへのアップサート
- シグナル生成（kabusys.strategy.signal_generator）
  - 正規化済み特徴量＋AIスコア統合による final_score 計算
  - Bear レジーム判定、BUY/SELL の生成、signals テーブルへ冪等保存
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

---

## 要件

- Python 3.10 以上（typing の構文、| 型などを使用）
- 必要なライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

実プロジェクトでは pyproject.toml / requirements.txt に依存関係を明示してください。

---

## セットアップ手順

1. リポジトリを取得し、ソースディレクトリを PYTHONPATH に含めるかパッケージとしてインストールします。

   例（開発インストール）:
   ```
   pip install -e .
   ```

2. 必要パッケージをインストール:
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）。自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 主な必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - KABUSYS_ENV: development / paper_trading / live（省略時: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）
   - DUCKDB_PATH / SQLITE_PATH: DB ファイルパス（省略時デフォルトあり）

   .env のサンプル（README 用簡易例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 初期化（DuckDB スキーマ作成）

DuckDB ファイルを初期化してスキーマを作成します。

Python 例:
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 返り値は duckdb.DuckDBPyConnection
```

メモリ DB を使う場合:
```
conn = init_schema(":memory:")
```

既存 DB に接続するだけなら get_connection を使用します。

---

## 使い方（主な操作例）

以下はライブラリ関数を直接呼ぶ例です。実際の運用ではスクリプト / サービスから呼び出してください。

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
```
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（features テーブルの生成）
```
from datetime import date
from kabusys.strategy import build_features
conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2026, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ書き込み）
```
from datetime import date
from kabusys.strategy import generate_signals
conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2026, 1, 31))
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS から raw_news へ保存）
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 必要なら既知コードセットを渡す
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job
conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants からの生データ取得（テスト用途）
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,1,31))
```

---

## 環境変数と設定（kabusys.config）

自動的にプロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止できます。

主要プロパティ（Settings クラス）:
- jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
- kabu_api_password (KABU_API_PASSWORD) — 必須
- kabu_api_base_url (KABU_API_BASE_URL) — デフォルト: http://localhost:18080/kabusapi
- slack_bot_token / slack_channel_id — 必須（Slack 連携）
- duckdb_path (DUCKDB_PATH) — デフォルト: data/kabusys.duckdb
- sqlite_path (SQLITE_PATH) — デフォルト: data/monitoring.db
- env (KABUSYS_ENV) — development / paper_trading / live
- log_level (LOG_LEVEL) — DEBUG/INFO/WARNING/ERROR/CRITICAL

未設定の必須変数にアクセスすると ValueError が発生します。

---

## ディレクトリ構成

主要なファイル/パッケージ（src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py                    # 環境変数/.env 管理
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（取得＋保存）
    - news_collector.py         # RSS ニュース収集・前処理・保存
    - schema.py                 # DuckDB スキーマ定義・初期化
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - stats.py                  # 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py    # マーケットカレンダー管理、ジョブ
    - audit.py                  # 監査ログ用 DDL/初期化（発注・約定のトレーサビリティ）
    - features.py               # data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py        # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py    # 将来リターン、IC、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py    # features テーブル構築ロジック
    - signal_generator.py       # final_score 計算と signals 書き込み
  - execution/                   # 発注・ブローカー連携のためのスケルトン
    - __init__.py
  - monitoring/                  # 監視用ユーティリティ（プレースホルダ）
    - __init__.py

各モジュールは「DuckDB 接続を受け取る」かたちで実装されており、外部副作用を限定しています（テスト容易性を確保）。

---

## 開発・テストのヒント

- 自動環境読み込みを抑止してユニットテストしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB をインメモリで作成すればテストで高速にスキーマ初期化できます:
  ```
  conn = init_schema(":memory:")
  ```
- RSS フィードの取得周りはネットワーク依存のため、news_collector._urlopen をモックしてテスト可能です。

---

必要に応じて README を拡張して、運用手順（cron/runner）の例、Slack 通知ハンドラ、kabu ステーションとの発注フロー、監査ログの閲覧方法などを追加してください。