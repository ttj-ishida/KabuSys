# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants や RSS 等からデータを収集し、DuckDB に格納・整形して戦略・研究用の特徴量を提供することを目的としています。発注・監査・モニタリングのためのスキーマ/ユーティリティ群も含みます。

---

## 主要な特徴 (Features)

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS 取得・ニュース収集（SSRF/サイズ/圧縮対策、記事ID生成、銘柄抽出）
- ETL パイプライン
  - 差分取得（差分・バックフィル）、冪等保存（ON CONFLICT）
  - 市場カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- データスキーマ
  - Raw / Processed / Feature / Execution / Audit 層をカバーする DuckDB スキーマ定義
  - 監査テーブル群（signal → order_request → executions のトレーサビリティ）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Z-score 正規化ユーティリティ
- セーフティ／運用配慮
  - API レートリミット制御・リトライロジック・トークン自動リフレッシュ
  - RSS の XML 脆弱性対策（defusedxml）、SSRF 対策、レスポンスサイズ制限
  - 環境変数自動ロード（プロジェクトルートの .env / .env.local）

---

## 必要条件 (Requirements)

- Python 3.9+
- 外部パッケージ（例）
  - duckdb
  - defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## 環境変数 / 設定

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードはデフォルトで有効です（プロジェクトルートは `.git` または `pyproject.toml` を起点に探索）。無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行環境フラグ / ログレベル
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

注意: Settings は厳密に必須環境変数を検査します。未設定でアクセスすると ValueError が発生します。

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン
2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （実際は requirements.txt / pyproject.toml を使用）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポート
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development
5. DuckDB スキーマの初期化（次節参照）

---

## 初期化: DuckDB スキーマ

Python REPL やスクリプトで DuckDB スキーマを初期化します。

例: メインスキーマを初期化する
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

監査（audit）専用 DB を初期化する（または既存接続に監査テーブルを追加）
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
# 新規 DB
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# 既存接続に追加する場合
init_audit_schema(conn)  # conn は init_schema で得た接続
```

---

## よく使う使い方 (Usage)

以下は主要 API の使用例です。詳細は各モジュールのドキュメンテーション（コード内 docstring）を参照してください。

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 株価データを J-Quants から直接取得して保存する（個別ジョブ）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コード集合（抽出時に利用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d)
# IC 計算例
from kabusys.research.feature_exploration import calc_ic
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

- カレンダー管理ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- J-Quants 生データフェッチ（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 注意事項 / 運用メモ

- 環境変数の自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git / pyproject.toml 探索）から `.env` / `.env.local` を自動で読み込みます。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み順: OS 環境変数 > .env.local > .env
- J-Quants API
  - レート制限（120 req/min）を守るため内部でスロットリングおよびリトライ処理があります。
  - 401 を受けた場合はリフレッシュトークンで自動更新を試みます（1回）。
- RSS ニュース
  - defusedxml を使い XML 攻撃を防いでいます。RSS フィードは HTTP(S) のみを許可し、リダイレクト先は内部 IP（プライベート）を拒否します。
- DuckDB スキーマ
  - 多数のテーブルとインデックスを定義します。init_schema は冪等で、既存のテーブルは上書きしません。
- 安全性
  - 取引系（execution / order）モジュールは本コードベースに含まれるスキーマを備えますが、実際の発注フロー（証券会社APIとの接続や鍵管理）を組み込む場合は厳重な監査とテストを行ってください。
- ログレベルと環境（KABUSYS_ENV）
  - 本番モード（live）では実際の発注・接続処理を伴う設計のため、KABUSYS_ENV によるガードやサンドボックス化を行ってください。

---

## ディレクトリ構成 (抜粋)

（実際のリポジトリには追加ファイルがあるかもしれません。ここでは提供ソースからの構成を示します）

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
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
    - (戦略実装ファイルを配置)
  - execution/
    - __init__.py
    - (発注関連実装を配置)
  - monitoring/
    - __init__.py
    - (監視・アラート関連を配置)

---

## 貢献 / 開発メモ

- 単体テストや CI を導入する際は、環境変数の自動ロードを無効化してテスト用の .env を手動で読み込んでください。
- DuckDB を使ったテストでは ":memory:" を使うことでファイル I/O を回避できます。
- 新しいデータソースや戦略を追加する場合は、必ず以下を満たすようにしてください:
  - 冪等性 (DB への保存は ON CONFLICT を利用)
  - Look-ahead bias の防止（fetched_at を記録する等）
  - 外部 API のレート制限・エラー処理を行う

---

この README はコードベース内の docstring と実装仕様に基づいて作成しています。詳細な利用方法や API 仕様は各モジュールの docstring を参照してください。質問や追加のドキュメント化リクエストがあれば教えてください。