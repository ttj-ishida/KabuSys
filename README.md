# KabuSys — 日本株自動売買システム（README）

概要
----
KabuSys は日本株の自動売買プラットフォームを支えるライブラリ群です。  
主に以下を提供します。

- J-Quants API からの市場データ取得（株価、財務、マーケットカレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理と営業日判定ロジック
- 監査ログ（signal → order → execution のトレース）用スキーマ

設計上のポイント
- J-Quants のレート制限（120 req/min）やリトライ、トークン自動リフレッシュに対応
- データ保存は冪等（ON CONFLICT）で上書き・重複排除
- ニュース収集は SSRF 対策、XML 向け安全パーサ、受信サイズ制限などを実装
- 品質チェック（欠損・重複・スパイク・日付不整合）を提供

特徴（機能一覧）
----
- data.jquants_client: J-Quants API クライアント（fetch / save 用関数）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- data.news_collector: RSS 収集と raw_news 保存、銘柄抽出と news_symbols 保存
  - fetch_rss, save_raw_news, run_news_collection
- data.schema: DuckDB スキーマ初期化（init_schema / get_connection）
- data.pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- data.calendar_management: カレンダー更新・営業日判定
  - calendar_update_job, is_trading_day, next_trading_day, prev_trading_day, get_trading_days
- data.quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- data.audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
- 環境設定: kabusys.config.Settings による .env / 環境変数管理（自動読み込み機能あり）

前提条件
----
- Python 3.10+（typing の Union 型表記や型ヒントを想定）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード取得など）

セットアップ手順
----
1. リポジトリをチェックアウト
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係をインストール（requirements.txt がある場合はそれを利用）
   ここでは最小限の例を示します：
   ```bash
   pip install duckdb defusedxml
   ```

4. パッケージをインストール（ソース開発用）
   ```bash
   pip install -e .
   ```

環境変数・設定
----
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` に配置します。パッケージ起動時に自動で .env を読み込む挙動があります（無効化は下記参照）。

主な必須環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルト値あり
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env の自動読み込み制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途など）。

サンプル .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

初期化（DuckDB スキーマ・監査DB）
----
- DuckDB スキーマを初期化するには data.schema.init_schema を使用します。

Python 例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルにスキーマ作成して接続を返す
```

- 監査用 DB 初期化（監査用専用 DB を用いる場合）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

使い方（代表的な呼び出し例）
----
- 日次 ETL を実行して市場データを取得・保存・品質チェックする：
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続（初回は init_schema を実行）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集と銘柄紐付け：
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄リスト
res = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)
```

- カレンダーの夜間更新ジョブ：
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

開発者向け：自動環境読み込みの注意
- config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを検出します。パッケージ配布後は CWD に依存しないようになっています。
- テストで .env を読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save）
    - news_collector.py  — RSS ニュース収集・前処理・保存
    - schema.py  — DuckDB スキーマ定義・初期化
    - pipeline.py  — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  — マーケットカレンダー管理・営業日ロジック
    - audit.py  — 監査ログスキーマの初期化
    - quality.py  — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

運用上の留意点
----
- J-Quants の API レート制限（120 req/min）に注意してください。jquants_client は内部でスロットリングとリトライを実装しています。
- ニュース収集モジュールは外部 URL の取り扱いに注意（SSRF 対策、最大受信サイズ制限あり）。
- DuckDB のファイルパスのディレクトリは init_schema や init_audit_db が自動作成しますが、適切な権限で実行してください。
- 本リポジトリはライブラリ部分が中心です。実運用のためには発注実行部分（kabuAPI 連携）や監視・アラート回路を実装する必要があります。

貢献・ライセンス
----
- 本ドキュメントではリポジトリのライセンス情報は明示していません。実際の利用・配布は該当リポジトリの LICENSE を参照してください。

問い合わせ
----
不具合報告や機能追加提案がある場合は issue を立ててください。