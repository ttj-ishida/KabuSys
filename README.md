# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API や RSS を取り込み、特徴量計算・品質チェック・ETL・監査ログなどの機能を提供します。

## 概要

KabuSys は以下のレイヤーを想定した設計になっています。

- データ取得（J-Quants API）と保存（DuckDB）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量計算（モメンタム/ボラティリティ/バリュー 等）
- ETL パイプライン（差分取得・バックフィル・カレンダー調整）
- ニュース収集（RSS → 正規化 → DuckDB）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

本リポジトリは、研究（research）、データ（data）、戦略（strategy）、発注実行（execution）、監視（monitoring）をモジュール単位で分離しています。

## 主な機能一覧

- J-Quants API クライアント（レート制限・リトライ・トークン自動更新対応）
  - 日足（OHLCV）取得、財務データ取得、市場カレンダー取得
- DuckDB スキーマ定義 / 初期化（冪等にテーブル・インデックスを作成）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl による日次 ETL の一括実行
- データ品質チェック（missing / duplicates / spike / date consistency）
- ニュース収集（RSS 取得、SSRF 対策、トラッキングパラメータ除去、記事ID生成、銘柄抽出）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - calc_momentum, calc_volatility, calc_value
- 研究用ユーティリティ
  - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、Zスコア正規化等
- 監査ログスキーマ（signal_events / order_requests / executions）

## 必要環境・依存ライブラリ

- Python 3.10 以上（型注釈に `|` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをパッケージとして開発モードで使う場合は、別途 pyproject.toml / setup を整備している前提で:
```bash
pip install -e .
```

※ 実行にあたってはその他ライブラリ（Slack 連携など）が別途必要になる可能性があります。各機能を呼び出す箇所で明示的に使う標準/外部ライブラリを確認してください。

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）
   - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
5. DuckDB スキーマを初期化

例 (.env の最低必須項目の例):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション API（発注を行う場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作モード: development | paper_trading | live
KABUSYS_ENV=development

# ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_LEVEL=INFO
```

## 環境変数自動ロード

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settingsで参照されるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- そのほか `DUCKDB_PATH` などはデフォルト値あり

## データベース初期化 (DuckDB)

Python REPL やスクリプトから実行する例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH に依存（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
# これで必要なテーブル・インデックスが作成されます
```

インメモリ DB を使う例（テスト用）:
```python
conn = init_schema(":memory:")
```

監査ログ専用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

## ETL の使い方

日次 ETL の実行例:

```python
from datetime import date
import duckdb

from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化 / 接続
conn = init_schema(settings.duckdb_path)

# 今日の ETL を実行（id_token は省略可: 内部で settings.jquants_refresh_token を使って取得）
result = run_daily_etl(conn)

# 結果確認
print(result.to_dict())
```

個別 ETL（価格/財務/カレンダー）も呼べます:
- run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline モジュール）

バックフィルや特定期間取得などの引数も利用可能です。

## ニュース収集（RSS）例

RSS を取得して DB に保存する例:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 既知の銘柄コードセット（extract_stock_codes に渡すため）
known_codes = {"7203", "6758", "9984", ...}

result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(result)  # {source_name: saved_count, ...}
```

fetch_rss / save_raw_news / save_news_symbols といった関数を個別に使うこともできます。

## 研究・特徴量計算の使い方

特徴量や研究用ユーティリティは kabusys.research にまとまっています。

例: モメンタム計算 → IC 計算

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 5)

factors = calc_momentum(conn, target)
forw = calc_forward_returns(conn, target, horizons=[1,5])

ic = calc_ic(factors, forw, factor_col="mom_1m", return_col="fwd_1d")
print("Spearman IC:", ic)
```

Zスコア正規化は `kabusys.data.stats.zscore_normalize`（あるいは再エクスポートされた `kabusys.data.features.zscore_normalize`）を利用します。

## カレンダー管理

カレンダー関連ユーティリティは kabusys.data.calendar_management にあります:

- calendar_update_job: J-Quants からカレンダー差分取得・保存
- is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day: 営業日判定・探索

例:

```python
from kabusys.data.calendar_management import calendar_update_job, is_trading_day
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)

print("is trading day 2024-01-04:", is_trading_day(conn, date(2024,1,4)))
```

## ロギング設定

ライブラリは logging を利用します。アプリ側で適切に logging.basicConfig や dictConfig 等でログレベルやハンドラ（ファイル、STDOUT、Slack など）を設定してください。環境変数 `LOG_LEVEL`（Settings）で意図しない値が渡された場合は ValueError を送出します。

## 注意点 / 設計上のポリシー

- DuckDB の SQL はパラメータバインド（?）を使用しています。SQL インジェクションに注意する必要は低い設計です。
- ETL は後出し修正（API 側データ訂正）を吸収するためにバックフィルを行います（デフォルト3日）。
- ニュース RSS 取得では SSRF 対策（スキームチェック、プライベートIPブロック、リダイレクト検査）を実装しています。
- J-Quants クライアントはレート制限（120 req/min）対応のシンプルな RateLimiter を備えています。
- 本ライブラリは本番口座への発注処理を含むモジュールを持ちます。`KABU_API_PASSWORD` 等の取り扱いは厳重に行ってください。運用時は paper_trading / live 等の環境変数 `KABUSYS_ENV` を適切に設定してください。

## ディレクトリ構成

主要なファイル / モジュールの概観:

- src/kabusys/
  - __init__.py
  - config.py                - 環境設定 / .env ロード / Settings
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント、保存ユーティリティ
    - news_collector.py      - RSS 取得・前処理・保存
    - schema.py              - DuckDB スキーマ定義 / init_schema
    - stats.py               - 統計ユーティリティ（zscore）
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - features.py            - 特徴量公開インターフェース
    - calendar_management.py - 市場カレンダー管理
    - audit.py               - 監査ログスキーマ初期化
    - etl.py                 - ETL 関連の公開インターフェース
    - quality.py             - データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py - 将来リターン計算 / IC / summary
    - factor_research.py     - momentum/value/volatility の計算
  - strategy/                - 戦略層（空のパッケージ、拡張ポイント）
  - execution/               - 発注・実行層（空のパッケージ、拡張ポイント）
  - monitoring/              - 監視・メトリクス（空のパッケージ）

ドキュメントや設計図は README の他に `DataPlatform.md`, `StrategyModel.md` 等（コメント内参照）に基づいて設計されていますが、リポジトリに含まれていない場合があります。

## 最後に

この README はコードベースの主要な利用方法とセットアップ手順をまとめたものです。実際の運用では下記点に留意してください。

- 機密情報（API トークン、パスワード）は安全に保管すること
- 本番発注ロジックを扱う際は paper_trading で十分に検証してから live 環境に切り替えること
- DuckDB ファイルのバックアップ・監査ログ運用方針を明確にすること

追加で README に入れたい内容（例: コンテナ化手順、CI 設定、具体的な Slack 通知実装例、サンプルデータロード手順）があれば教えてください。必要に応じて追記します。