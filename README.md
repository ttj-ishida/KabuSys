# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株のデータ取得・ETL・品質チェック・ニュース収集・監査ログなどを備えた自動売買プラットフォームのライブラリ群です。J-Quants API や RSS フィードを利用してデータを取得し、DuckDB に蓄積・整形して戦略/実行層へ渡すための基盤機能を提供します。

主な設計方針：
- データ取得はレート制限・リトライ・トークン自動リフレッシュ等を備えた堅牢な実装
- DuckDB に対して冪等（idempotent）にデータを保存
- ニュース収集は SSRF / XML Bomb / トラッキングパラメータ対策を実装
- データ品質チェック・市場カレンダー管理・監査ログ（トレーサビリティ）を提供

## 機能一覧
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - ページネーション対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス定義、冪等なテーブル作成
- ETL パイプライン
  - 差分取得（最終取得日からの差分計算）、バックフィル（後出し修正の吸収）
  - 日次 ETL エントリ（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損、主キー重複、前日比スパイク、日付不整合（未来日・非営業日）検出
- ニュース収集
  - RSS フィード取得、テキスト前処理、記事ID の生成（正規化 URL + SHA-256）
  - SSRF 対策、gzip/サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING を利用）
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、夜間バッチ更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティ用テーブル群
  - UTC 固定、冪等キー（order_request_id）による二重発注防止

## 前提 / 要件
- Python 3.10+（型 | を使用しているため）
- 推奨ライブラリ（インストール例は下記）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィードなど）

例: 必要パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしくはプロジェクトの requirements.txt があればそれを使用
```

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード）
```bash
git clone <repo_url>
cd <repo>
pip install -e .
```

2. 環境変数（.env）を準備する
- プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（※テスト時は無効化可能）。
- 自動ロードを無効にする場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

推奨する環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot token（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（簡単な例）

以下は Python スクリプトや REPL から使う基本例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # parent dir は自動作成
```

- 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants API を直接利用してデータ取得
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を利用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```
- 株価データを保存（save_daily_quotes）
```python
from kabusys.data.jquants_client import save_daily_quotes
saved = save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出フィルタとして使用）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- 監査スキーマの初期化（audit テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
# 既存の DuckDB 接続 conn を渡す
init_audit_schema(conn, transactional=True)
```

- 設定を参照する
```python
from kabusys.config import settings
print(settings.kabu_api_base_url)
print(settings.env)
```

注意点：
- jquants_client は内部でレートリミッタとリトライを行います。大量リクエストや並列化の際は設計に注意してください。
- news_collector は外部 RSS を取得する際に SSRF / private host をブロックします。社内ネットワークの RSS を利用する場合は注意が必要です。

## 主要 API の説明（抜粋）
- kabusys.config.Settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path など

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token, code, date_from, date_to) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(...)
  - save_market_calendar(...)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ... ) -> ETLResult

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[str] (新規挿入された記事ID)
  - run_news_collection(conn, sources=None, known_codes=None) -> dict[source,int]

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=90) -> int

## 環境変数の自動読み込みについて
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト等で有用）。

## ディレクトリ構成（概要）
以下は主要ファイルの一覧です（提供されたコードベースに基づく）。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       # RSS ニュース収集・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（差分更新・日次ETL）
    - calendar_management.py  # 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                # 監査ログ（signal/order_request/execution）スキーマ
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py             # 戦略関連（未展開）
  - execution/
    - __init__.py             # 発注 / 実行関連（未展開）
  - monitoring/
    - __init__.py             # 監視関連（未展開）

（上記は現状の実装に基づく。strategy/execution/monitoring 層は初期スケルトンになっています）

## 開発・貢献
- バグ報告や機能追加の提案は issue を立ててください。
- テスト・CI は将来的に追加を予定しています。ローカルでの動作確認には DuckDB とネットワークアクセス（J-Quants / RSS）を用いてください。

---

この README は提供されたソースコードの機能に基づいて作成しています。実運用時は各種 API トークンやパスワードの管理、秘密情報の取り扱い、実際の発注ロジックやリスク管理の実装を必ず整備してください。