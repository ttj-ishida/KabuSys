# KabuSys

日本株自動売買プラットフォーム向けのユーティリティ群（データ取得、ETL、特徴量計算、ニュース収集、監査ログなど）をまとめた軽量ライブラリです。  
このリポジトリは主に以下を提供します：

- J-Quants API を用いた株価 / 財務 / カレンダー取得クライアント（ページネーション・リトライ・レート制御付き）
- DuckDB スキーマ定義と初期化ユーティリティ（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS → 正規化 → DuckDB へ冪等保存、銘柄抽出）
- 研究（Research）向けのファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 計算、Zスコア正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- マーケットカレンダー管理、監査ログ初期化など

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（token refresh、ページネーション、レート制御、リトライ）
  - 生データを DuckDB に冪等保存する save_* 関数
- data/schema.py
  - DuckDB のスキーマ定義（多層構造）と init_schema()
- data/pipeline.py
  - run_daily_etl(): カレンダー・株価・財務の差分ETL + 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別処理
- data/news_collector.py
  - RSS フィード収集、前処理、正規化、raw_news 保存、銘柄（4桁コード）抽出
  - SSRF・XML攻撃・サイズ制限などのセキュリティ対策実装
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- research/
  - factor_research.py: calc_momentum / calc_volatility / calc_value（DuckDB 接続を受け取る）
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を再利用した正規化ユーティリティ
- data/audit.py
  - 監査ログ用テーブル定義と初期化（トレーサビリティ / 冪等性重視）
- config.py
  - .env または環境変数の自動ロード（プロジェクトルート検出）・Settings クラスで設定値を提供

---

## 動作要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, datetime, logging 等）を広く使用

（pip 用の requirements.txt がない場合は上記をインストールしてください）
例:
```
python -m pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトして、Python 環境を作成します。

2. 依存パッケージをインストールします（上記参照）。

3. 環境変数を設定します。プロジェクトは自動的にプロジェクトルート（.git または pyproject.toml の存在）を探索して `.env` / `.env.local` を読み込みます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

任意（既定値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# 任意
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

ここでは主要なユースケースを示します。すべて Python スクリプトから呼び出して利用します。

- Settings の参照
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # development|paper_trading|live
```

- DuckDB スキーマの初期化（初回のみ）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 日次 ETL 実行（カレンダー→株価→財務→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETLResult の内容
```

- ニュース収集ジョブを実行して DB に保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は既知の銘柄コードセットを渡すと、記事との紐付けが行われる
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- J-Quants からのデータ取得（直接 fetch）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.config import settings
from datetime import date

# token は省略可能（モジュール内キャッシュを使用）
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

- 研究（Research）向け関数の使用例（DuckDB 接続を渡す）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# 将来リターンを計算して IC（情報係数）を求める例
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
# fwd とファクターの join はコード側で行って calc_ic を呼ぶ
# calc_ic(factor_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
```

- 自動 .env ロードの無効化（テスト時など）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('loaded')"
```

---

## ディレクトリ構成（src/kabusys ベース）

以下は主なファイル／モジュールの一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py (placeholder)
  - execution/
    - __init__.py (placeholder)
  - monitoring/
    - __init__.py (placeholder)

（各モジュールの詳細はソース内ドキュメントと docstring を参照してください）

---

## 開発上の注意点 / 設計方針（抜粋）

- DuckDB を永続ストレージとして採用。init_schema() は冪等でテーブル・インデックスを作成します。
- J-Quants クライアントはレート制御（120 req/min 固定間隔スロットリング）とリトライ（指数バックオフ）を実装しています。401 は自動でトークンリフレッシュを試行します。
- ニュース収集は SSRF / XML Bomb / Gzip-bomb / 大容量応答 などの対策を含んでいます。
- 研究用関数は外部 API や発注系にはアクセスせず、DuckDB 上の prices_daily / raw_financials のみを参照します（Look-ahead Bias に配慮）。
- 環境設定は Settings クラスを通じてアクセスする想定（settings.jquants_refresh_token 等）。必須設定は _require() でチェックされ ValueError を発生させます。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかにしてください。

---

## トラブルシューティング

- .env が読み込まれない／テストで明示的に環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の接続・DDL 実行で失敗する場合はパーミッションやディスク容量、duckdb のバージョンを確認してください。
- J-Quants へのリクエストで 401 が返る場合は JQUANTS_REFRESH_TOKEN の有効性を確認してください。トークンは自動更新処理が入りますが、リフレッシュ失敗はエラーになります。
- news_collector で RSS の取得がブロックされる場合、対象 URL のスキームやリダイレクト先が private IP になっていないかを確認してください（SSRF 防止制約あり）。

---

必要があれば、README にサンプルの .env.example、docker-compose での実行例、CI 用のテスト手順、より詳細な API リファレンスを追加します。どの情報を優先して追加しますか？