# KabuSys

日本株向け自動売買システムのライブラリ群（KabuSys）。  
J-Quants / kabuステーション 等の外部サービスからデータを取得・保存し、ETL、品質チェック、ニュース収集、監査ログ等の基盤処理を提供します。

---

## プロジェクト概要

KabuSys は以下の機能群を提供するモジュール群です。

- J-Quants API クライアント（株価・財務・市場カレンダー取得、認証／リトライ／レートリミット対応）
- DuckDB ベースのスキーマ定義および初期化
- ETL パイプライン（日次差分取得、バックフィル、品質チェック）
- ニュース収集（RSS → 正規化 → DuckDB 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、翌日/前日検索、夜間更新ジョブ）
- 監査ログ（signal → order → execution をトレースする監査テーブル群）
- 環境変数／設定管理（.env 自動読み込み、必須設定のチェック）

設計上のポイント：
- 冪等性（DB 保存は ON CONFLICT で安全）
- Look-ahead bias 対策（取得時刻 / fetched_at の記録）
- API レート制限／リトライ／トークン自動リフレッシュ対応
- SSRF / XML Bomb / メモリ DoS 等のセキュリティ対策（news_collector）

---

## 主な機能一覧

- data.jquants_client
  - get_id_token(): リフレッシュトークンから id_token を取得
  - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()（DuckDB へ冪等保存）
- data.schema
  - init_schema(db_path): DuckDB の全スキーマを作成
  - get_connection(db_path)
- data.pipeline
  - run_daily_etl(conn, target_date=..., ...): 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- data.news_collector
  - fetch_rss(url, source): RSS 取得および記事の正規化
  - save_raw_news(conn, articles), save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources, known_codes): 複数 RSS をまとめて収集・保存
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn, lookahead_days): 夜間カレンダー更新
- data.audit
  - init_audit_schema(conn[, transactional]) / init_audit_db(db_path): 監査テーブル初期化
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(conn, ...): 品質チェックの一括実行
- config
  - settings: 環境変数から各種設定値を参照するオブジェクト

---

## 前提 / 必要要件

- Python 3.10+（typing の Union/Annotated を使用しているため近年の Python を想定）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS ソースなど）

インストール例（pipenv / poetry 等の推奨はプロジェクトに合わせてください）:
```bash
pip install duckdb defusedxml
```

---

## 環境変数（主なもの）

設定は .env または環境変数から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われ、優先順位は OS 環境変数 > .env.local > .env です。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須設定（未設定の場合は読み出し時に ValueError）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

任意 / デフォルト値あり:
- KABUSYS_ENV            : environment（"development" | "paper_trading" | "live"、デフォルト "development"）
- LOG_LEVEL              : ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"、デフォルト "INFO"）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化するフラグ（値が存在すれば無効）

.env 例（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を作成して依存パッケージをインストール
3. プロジェクトルートに .env を作成（必須トークン等を設定）
4. DuckDB スキーマを初期化

手順の例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # または個別に duckdb defusedxml 等をインストール

# .env を作成して必須値をセット
cp .env.example .env
# .env を編集してトークン等を設定

# DuckDB スキーマ初期化
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

監査ログ専用 DB を別途用意する場合:
```bash
python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"
```

---

## 使い方（代表的な例）

以下はライブラリ API を直接呼ぶ例です。実運用では CLI やジョブスケジューラ（cron / Airflow 等）から呼び出してください。

- DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブの実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は抽出に使用する有効銘柄コードのセット
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # ソースごとの新規保存数
```

- カレンダー夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- 監査スキーマ初期化（既存接続に追加）:
```python
from kabusys.data.schema import get_connection
from kabusys.data.audit import init_audit_schema

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn, transactional=False)
```

- J-Quants から直接データを取得:
```python
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成

この README は配布されているコードベースに基づく想定構成の一覧です（主要ファイルのみ抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュール:
- kabusys.config: 環境設定読み込み／settings オブジェクト
- kabusys.data: データ取得・ETL・スキーマ・品質チェック

---

## 開発メモ / 注意事項

- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から推定します。テスト等で自動ロードを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）を厳守するため、jquants_client は内部でレートリミッタを使用しています。
- jquants_client は 401 を検出した場合、リフレッシュトークンから id_token を自動更新して 1 回のみリトライします。
- news_collector は SSRF や XML 攻撃、gzip/Bomb、トラッキングパラメータを考慮した堅牢な実装を目指しています。テスト時はネットワーク呼び出しをモックしてください（_urlopen を差し替え可能）。
- DuckDB の初期化は冪等であり、既存テーブルは上書きされません（CREATE TABLE IF NOT EXISTS / ON CONFLICT を使用）。
- 品質チェックは Fail-Fast を採らず、検出された全問題を収集して呼び出し元が判断できるようにしています。
- 監査スキーマはタイムゾーンを UTC に固定します（init_audit_schema で SET TimeZone='UTC' を実行）。

---

## ライセンス / 貢献

（プロジェクトに応じてライセンスや貢献指針をここに追記してください）

---

README に記載のサンプル呼び出しは最小限の使用例です。実運用ではエラーハンドリング、ログ設定、バックアップ、機密情報の管理（Vault など）を適切に設計してください。