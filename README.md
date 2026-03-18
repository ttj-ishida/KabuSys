# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants API からのデータ収集（OHLCV・財務・市場カレンダー）、RSS ニュース収集、品質チェック、特徴量計算、研究用ユーティリティ（IC 計算など）を提供します。発注・監査・実行ログのスキーマとユーティリティも含まれます。

## 主な特徴
- J-Quants API クライアント（ページネーション／レート制御／トークン自動リフレッシュ／リトライ）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF 対策、gzip 制限、トラッキング除去、銘柄抽出）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）および前方リターン / IC 計算
- 汎用統計ユーティリティ（Zスコア正規化）
- マーケットカレンダー管理（営業日判定、次/前営業日取得、バッチ更新）
- 監査ログ（シグナル→発注→約定の完全トレーサビリティ用テーブル群）

## 必要な環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN        : Slack bot トークン（必須）
- SLACK_CHANNEL_ID       : 通知先チャネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 実行環境 ("development" | "paper_trading" | "live")（省略時 "development"）
- LOG_LEVEL              : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（省略時 "INFO"）

自動でプロジェクトルートの `.env` と `.env.local`（優先順: OS 環境 > .env.local > .env）を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン（またはソースを取得）
2. 仮想環境を作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1
3. 依存パッケージをインストール（最低限）
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそれを利用）
4. 環境変数を設定する
   - 例: プロジェクトルートに `.env` を作成
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=yyyyyyyy
     SLACK_BOT_TOKEN=zzzzzzzz
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB スキーマの初期化（例）
   - Python REPL またはスクリプト内で:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```

## 使い方（主要ユースケースの例）

### 日次 ETL を実行する
DuckDB 接続を作成して ETL を実行します（市場カレンダーの先読み、株価・財務の差分取得、品質チェックを行います）。

```python
from kabusys.data import schema, pipeline

# DB 初期化（ファイルがなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を指定しなければ本日）
result = pipeline.run_daily_etl(conn)

# 結果の確認
print(result.to_dict())
```

個別に ETL ステップを実行することもできます:
- run_calendar_etl(conn, target_date, ...)
- run_prices_etl(conn, target_date, ...)
- run_financials_etl(conn, target_date, ...)

### JPX カレンダーを夜間バッチで更新する
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

### ニュース収集ジョブ
RSS フィードから記事を取得して raw_news に保存し、既知の銘柄コードセットで銘柄紐付けを行います。

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")

# sources を省略するとデフォルト RSS ソースを使用
# known_codes は抽出対象の銘柄コードセット（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

### 研究用ファクター計算 / 指標
DuckDB 接続と日付を渡して各種ファクター・統計量を取得できます。

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
target = date(2025, 1, 15)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

print("IC:", ic)
print("Summary:", summary)
```

### Zスコア正規化（クロスセクション）
```python
from kabusys.data.stats import zscore_normalize

normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

### J-Quants API を直接利用してデータを取得・保存
jquants_client がページネーション、レート制御、トークンリフレッシュ等を扱います。
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

### 設定取得
環境変数や .env で指定した設定は `kabusys.config.settings` から参照できます。
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

## ディレクトリ構成（主要ファイル）
（実際のリポジトリは src/kabusys 以下にモジュールが置かれています）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得/保存）
    - news_collector.py              -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                      -- DuckDB スキーマ定義と初期化
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl など）
    - features.py                    -- 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py         -- マーケットカレンダー管理
    - audit.py                       -- 監査ログスキーマ初期化
    - etl.py                         -- ETL インターフェース再エクスポート
    - quality.py                     -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py         -- 前方リターン / IC / サマリー
    - factor_research.py             -- Momentum/Volatility/Value の計算
  - strategy/                         -- 戦略層（空のパッケージ、拡張用）
  - execution/                        -- 発注/実行層（空のパッケージ、拡張用）
  - monitoring/                       -- 監視（空のパッケージ、拡張用）

## 注意点 / 実運用上のポイント
- DB 初期化は schema.init_schema() を使用してください。既存テーブルの再作成は行わず冪等です。
- J-Quants のレート制限（120 req/min）を尊重するため、クライアントは内部でスロットリングを行います。
- jquants_client は 401 を受け取った場合にリフレッシュトークン経由で id_token を再取得し一回だけリトライします。
- news_collector は SSRF 対策、gzip / サイズ制限、XML パースの安全ライブラリ（defusedxml）を利用しています。
- quality.run_all_checks() は Fail-Fast ではなくすべてのチェックを集めて返します。呼び出し側で重大度に応じた処理を行ってください。
- 環境を production 用（live）に切り替える場合は `KABUSYS_ENV=live` を設定し、実口座での発注ロジックを必ず確認してください（本コードベースでは発注 API 呼び出しの実装は含まれていないため、実装時に十分な安全対策を追加してください）。

## 拡張方法
- strategy/ や execution/ パッケージに戦略ロジック・発注ロジックを実装してください。
- 監査テーブルは audit.init_audit_schema() で既存 DB に追加できます。
- 特徴量や AI スコアのテーブルは schema の features / ai_scores に保存することを想定しています。

---

不明点や README の追加要望（例: 具体的な開発フロー、CI/CD、テストの書き方、依存一覧の明確化など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を追記します。