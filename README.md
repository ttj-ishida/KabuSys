# KabuSys

日本株向け自動売買基盤（KabuSys）のライブラリ群です。本リポジトリはデータ収集・ETL、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、アルゴリズム取引プラットフォームの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は主に以下を目的とした内部ライブラリ群です。

- J-Quants API からの市場データ（株価日足、財務、マーケットカレンダー）取得と DuckDB への永続化
- RSS を用いたニュース収集と記事の正規化・銘柄紐付け
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- マーケットカレンダーによる営業日判定ヘルパー
- 監査ログ（シグナル → 発注要求 → 約定）のスキーマと初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴：
- API レート制限遵守（J-Quants: 120 req/min）やリトライ、トークン自動リフレッシュなど堅牢な HTTP 実装
- DuckDB を用いた冪等性のある保存（ON CONFLICT を利用）
- RSS パースでの SSRF / XML Bomb 対策（URL 検証、defusedxml、レスポンスサイズ制限 等）
- 品質チェックは Fail-Fast ではなく問題の収集を重視

---

## 主な機能一覧

- data.jquants_client
  - get_id_token: リフレッシュトークンから ID トークン取得（自動リフレッシュ対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応の API 取得
  - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB へ冪等保存

- data.news_collector
  - fetch_rss: RSS 取得（SSRF / 圧縮 / XML パースの堅牢化）
  - save_raw_news: raw_news テーブルへバルク保存（INSERT ... RETURNING）
  - extract_stock_codes: テキストから 4 桁銘柄コード抽出
  - run_news_collection: 複数ソースからの収集ジョブ

- data.schema
  - init_schema: DuckDB のスキーマ（Raw / Processed / Feature / Execution）初期化
  - get_connection: 既存 DB へ接続

- data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
  - 差分更新・backfill（API の後出し修正吸収）に対応

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job: 夜間のカレンダー差分更新

- data.audit
  - 監査ログ用スキーマ定義・初期化（signal_events / order_requests / executions 等）
  - init_audit_schema / init_audit_db

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks: まとめて実行して QualityIssue を返却

- config
  - 環境変数の自動読み込み（.env, .env.local）、必須設定取得のラッパー（Settings）

注意: strategy / execution / monitoring パッケージは現在モジュール初期化のみ（具象実装は別途）。

---

## 必要環境（依存パッケージ）

- Python 3.10+
- duckdb
- defusedxml

（その他、標準ライブラリのみで動く箇所もありますが、実行環境に応じて追加の HTTP ライブラリ等が必要になることがあります）

例: pip で最低限のパッケージを入れる
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発依存があれば requirements-dev.txt 等を用意している想定で追加インストール
```

2. 環境変数を設定
- .env/.env.local か環境変数で必要な値を設定します。config.Settings から参照される主なキー:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

任意（デフォルト有り）:
- KABUSYS_ENV: development / paper_trading / live （デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト時などに便利）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

3. DuckDB スキーマ初期化
Python REPL またはスクリプトから schema.init_schema を呼び出します。

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査用 DB を別ファイルで初期化する場合
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（基本例）

J-Quants からデータ取得して保存、ETL を実行する際の代表的なコード例を示します。

- 日次 ETL を実行する（市場カレンダーの先読み・差分取得・品質チェック）
```python
from kabusys.data import schema, pipeline
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行する
```python
from kabusys.data import schema, news_collector

conn = schema.init_schema("data/kabusys.duckdb")
# sources をカスタム辞書で渡せます。既定値は DEFAULT_RSS_SOURCES。
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- 個別に J-Quants API を叩いてデータを取得する（テストやデバッグ用）
```python
from kabusys.data import jquants_client as jq
# トークンは settings から自動取得されます。get_id_token はリフレッシュを実行します。
id_token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 監査ログスキーマを初期化
```python
from kabusys.data import schema, audit
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続へ監査テーブルを追加
```

---

## 注意事項 / セキュリティ

- RSS パースや HTTP 取得では SSRF / XML Bomb / 大容量レスポンス対策を導入していますが、取得先を慎重に管理してください。
- J-Quants の API レート制限（120 req/min）をコードレベルで守る仕組みがあります。大量同時実行する場合は調整が必要です。
- 環境変数は秘匿情報を含むため適切な方法で管理してください（例: CI シークレット、Vault 等）。
- DuckDB による ON CONFLICT 更新で多くの冪等性を保証していますが、外部から直接 DB を触ると整合性を損なう可能性があります。

---

## ディレクトリ構成

（主要ファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集、正規化、銘柄抽出、保存
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — マーケットカレンダーの管理・営業日判定
    - audit.py               — 監査ログ（発注→約定のトレーサビリティ）定義
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層（プレースホルダ）
  - execution/
    - __init__.py            — 発注・約定周り（プレースホルダ）
  - monitoring/
    - __init__.py            — 監視・メトリクス（プレースホルダ）

ドキュメント / 設計参照:
- DataPlatform.md 等の外部設計文書に基づいた実装（コメントに参照あり）

---

## 開発・テストについて

- config モジュールは .env 自動読み込みを行います。テスト時に自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector の _urlopen はユニットテストでモック可能な設計になっています。
- DuckDB をインメモリで利用することで単体テストの高速化が可能です（db_path に ":memory:" を指定）。

---

もし README に追記してほしい情報（例: CLI、CI、具体的な戦略テンプレート、詳細な env.example）や、別ファイルのドキュメント化希望があれば教えてください。