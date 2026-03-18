# KabuSys

日本株自動売買のためのライブラリ群・データ基盤コンポーネント集です。  
DuckDB を内部データストアとして用い、J-Quants API や RSS を経由したデータ収集、データ品質チェック、特徴量生成、監査ログなどを含む設計になっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムを構成するためのモジュール群です。主な目的は次の通りです。

- J-Quants API から市場データ（終値・OHLCV）や財務データ、マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して記事保存・銘柄紐付けを行うニュースコレクタ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（Momentum / Volatility / Value 等）計算や将来リターン計算、IC 計算などのリサーチ用ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ
- 設定管理（.env 自動読み込み、環境区分・ログレベル判定）

設計方針として、DuckDB を中心に SQL と Python 標準ライブラリで完結すること、外部ライブラリへの依存を最低限にすること（pandas 等に依存しない）を掲げています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（認証リフレッシュ・ページネーション・レートリミット・リトライ）
  - fetch/save 用関数: fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
- data/schema
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution / audit など）
  - init_schema(db_path) で DB を初期化
- data/pipeline
  - 日次 ETL 実行エントリポイント: run_daily_etl
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
  - 差分更新・バックフィル・品質チェックを備えた ETL
- data/news_collector
  - RSS 取得・正規化・前処理・DB 保存（raw_news）・銘柄抽出・news_symbols 登録
  - run_news_collection でソース集合から一括収集
- data/quality
  - 欠損チェック、スパイク検出、重複チェック、日付不整合チェック、run_all_checks
- data/stats / data/features
  - zscore_normalize（クロスセクション Z スコア正規化）
- research
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関）、factor_summary、rank
- audit（監査ログ）
  - signal_events / order_requests / executions テーブル定義と初期化関数（init_audit_schema / init_audit_db）
- config
  - 環境変数管理（.env 自動読み込み、必須キー取得、環境/ログレベルバリデーション）

---

## 必要条件（環境）

- Python 3.10 以上（型注釈や構文に依存）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, datetime, logging, hashlib 等）

インストール例（最低限）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクト固有の追加依存がある場合は、requirements.txt を参照してインストールしてください。

---

## 環境変数（主なもの）

このプロジェクトは .env（または環境変数）から設定を読み込みます。プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` が自動で読み込まれます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD  
  - kabuステーション API のパスワード（発注等に使用）
- SLACK_BOT_TOKEN  
  - Slack 通知に使用する Bot Token
- SLACK_CHANNEL_ID  
  - Slack 通知先チャンネル ID

任意・デフォルトあり:

- KABUSYS_ENV  
  - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL  
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH  
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH  
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD  
  - 自動 `.env` 読み込みを無効化（値が設定されていると無効）

例（.env の最小例）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発者向け簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（例: duckdb, defusedxml）
4. .env を作成（上記の必須設定を記述）
5. DuckDB スキーマを初期化

例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

監査ログ専用 DB を別途作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 基本的な使い方（コード例）

- 日次 ETL を実行
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回は init_schema を
result = run_daily_etl(conn)  # target_date を与えればその日を処理
print(result.to_dict())
```

- 個別 ETL（株価のみ）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
# conn は init_schema または get_connection で得た接続
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄リスト（"7203" 等）の set。なければ None
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

- ファクター計算 / リサーチ
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

# conn は DuckDB 接続
moms = calc_momentum(conn, date(2024, 1, 31))
vols = calc_volatility(conn, date(2024, 1, 31))
vals = calc_value(conn, date(2024, 1, 31))

fwd = calc_forward_returns(conn, date(2024, 1, 31))
ic = calc_ic(moms, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(moms, ["mom_1m","mom_3m","ma200_dev"])
zscore = zscore_normalize(moms, ["mom_1m", "ma200_dev"])
```

- J-Quants からデータを直接取得して保存
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## よくある利用上の注意点 / ヒント

- DuckDB の初期化:
  - 初回は init_schema() を使って必要テーブルを作成してください。get_connection() は既存 DB への接続のみ行います。
- 環境読み込み:
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml）から自動ロードされます。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API:
  - レート制限（120 req/min）や 401 自動リフレッシュ、リトライロジックが組み込まれています。大量データ取得やバッチ実行時は API 制限を考慮してください。
- ニュース収集:
  - RSS のサイズ上限（10 MB）や SSRF 対策（リダイレクト先チェック、プライベートアドレス拒否）が組み込まれています。
- 品質チェック:
  - run_daily_etl のオプションで品質チェックを有効化できます。品質チェックで「error」レベルの問題が返った場合は処理停止判定を呼び出し元で行ってください（ライブラリは Fail-Fast を行いません）。

---

## ディレクトリ構成

主要ファイル・モジュールの一覧（src/kabusys を基準）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch/save）
    - news_collector.py  — RSS 収集・前処理・保存・銘柄抽出
    - schema.py  — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - features.py  — features の公開 API（zscore_normalize 等）
    - stats.py  — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - audit.py  — 監査ログスキーマ初期化（signal/order/execution）
    - etl.py  — ETL 公開 API（ETLResult 再エクスポート）
    - quality.py — 品質チェック（欠損・スパイク・重複・日付不整合）
  - research/
    - __init__.py  — 研究用 API エクスポート
    - feature_exploration.py  — 将来リターン、IC、サマリー
    - factor_research.py  — Momentum / Volatility / Value 等のファクター計算
  - strategy/
    - __init__.py  — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py  — 実行（発注）関連（拡張ポイント）
  - monitoring/
    - __init__.py  — 監視関連（拡張ポイント）

---

## 貢献 / 開発メモ

- コードは DuckDB の SQL を多用しています。SQL の変更はスキーマやインデックスへの影響を考慮してください。
- テストのために環境変数自動読み込みを無効化する際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のトークンは `JQUANTS_REFRESH_TOKEN` で管理します。テストでは短期間のアクセストークンをキャッシュする挙動があります。

---

README に含める追加情報（例: requirements.txt、.env.example、運用手順、CI/CD、監視アラートルール等）はプロジェクトの運用方針に応じて別途作成してください。必要であればこれらのテンプレートや詳細ドキュメントも作成します。