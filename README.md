# KabuSys

日本株向けの自動売買 / データプラットフォームのライブラリ群です。  
DuckDB をデータバックエンドに、J-Quants API などから市場データを取得・加工し、特徴量計算・品質チェック・監査ログなどの基盤機能を提供します。

主な設計方針
- データ取得は J-Quants API（rate limit とリトライを考慮）で差分取得（ETL）
- DuckDB に層別スキーマ（Raw / Processed / Feature / Execution）を用意
- Research 用のファクター計算（モメンタム・ボラティリティ・バリュー等）を提供
- ニュース収集（RSS）と銘柄抽出、冪等保存
- 品質チェック・市場カレンダー管理・監査ログ機能を備える
- 本番発注 API には依存しない設計（データ処理 / 研究と発注は分離）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（パッケージルート検出）, 必須値チェック
- データ取得・保存
  - J-Quants クライアント（株価・財務・市場カレンダー）、ページネーション・トークンリフレッシュ・レート制御・リトライ
  - raw_prices / raw_financials / market_calendar 等の冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分更新（最終取得日からの再取得 + backfill）
  - run_daily_etl でカレンダー・株価・財務の一括差分ETLと品質チェック
- DuckDB スキーマ初期化
  - init_schema(db_path) で全テーブルとインデックスを作成
  - 監査ログ用 init_audit_schema / init_audit_db
- 研究（Research）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank
  - zscore_normalize（data.stats）
- ニュース収集
  - RSS 取得（SSRF対策、gzip・サイズ制限、XML安全パース）
  - 記事正規化、SHA-256 による冪等 ID、raw_news 保存、news_symbols への紐付け
- 品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による差分更新
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化

---

## 前提 / 必要環境

- Python 3.10+（型注釈に union types 等を使用）
- 必要なライブラリ（最低限）:
  - duckdb
  - defusedxml
- 推奨: プロジェクトの setup.py / pyproject.toml に依存関係を記載して pip install してください。

例（簡易インストール）:
```bash
python -m pip install duckdb defusedxml
# またはパッケージとして配布している場合:
# pip install -e .
```

---

## 環境変数（必須 / 任意）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード（発注機能がある場合）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite 等（デフォルト: data/monitoring.db）

.env の例はリポジトリに .env.example を置いておくことを推奨します。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を準備（venv 等）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # pip install -e . などパッケージ配布があれば利用
   ```

3. 必要な環境変数を設定
   - .env を作成（.env.example を参考）
   - または CI / 実行環境の環境変数に設定

4. DuckDB スキーマを初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

5. 監査ログ DB を初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（主要な例）

以下は Python からの利用例です。実際のバッチ・ジョブに組み込んで使います。

- 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 市場カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
conn.close()
```

- ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は既知の銘柄コード集合（例: 全上場銘柄リスト）を渡すと記事に紐付ける
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
conn.close()
```

- ファクター計算 / 研究ユーティリティ
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

conn = init_schema("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)               # list[dict] (date, code, mom_1m, ...)
fwd = calc_forward_returns(conn, t)       # list[dict] (date, code, fwd_1d, ...)
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d") # Spearman ρ or None
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
conn.close()
```

- J-Quants からの直接データ取得（テスト用途）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.config import settings

# id_token は自動取得されます（settings.jquants_refresh_token 必須）
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

---

## API（主要なモジュールと関数）

- kabusys.config
  - settings: 環境変数ラッパー（jquants_refresh_token など）

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token

- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(conn, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date, spike_threshold)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job

- kabusys.data.audit
  - init_audit_db(db_path), init_audit_schema(conn, transactional=...)

---

## ディレクトリ構成（抜粋）

(プロジェクトの src/kabusys 以下)
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ stats.py
│  ├─ pipeline.py
│  ├─ features.py
│  ├─ calendar_management.py
│  ├─ audit.py
│  ├─ etl.py
│  └─ quality.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  └─ __init__.py
├─ execution/
│  └─ __init__.py
└─ monitoring/
   └─ __init__.py
```

各ファイルの役割は上の「機能一覧」やモジュール説明を参照してください。

---

## 注意事項 / 運用上のヒント

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を探索）から読み込まれます。CI 等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限とリトライ挙動は jquants_client に実装されていますが、運用時は大量リクエストのスケジューリングに注意してください。
- DuckDB に対する DDL/DDL 操作は冪等性を考慮していますが、既存データのバックフィルやスキーマ変更時はバックアップを推奨します。
- ニュース収集は外部 RSS を読むため SSRF・XML Bomb・巨大レスポンス等への対策を実装していますが、未知のフィードを追加する際は十分に監視してください。
- 監査ログは削除しない想定です（トレーサビリティを保証）。ディスク容量とバックアップ戦略を設計してください。

---

README は開発／運用中に随時更新してください。機能追加時は対応するモジュールのドキュメントに処理フローや副作用（外部 API 呼び出し、トランザクションの有無など）を明記することを推奨します。