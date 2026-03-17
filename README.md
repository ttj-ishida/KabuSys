KabuSys
======

概要
----
KabuSys は日本株の自動売買プラットフォーム向けのデータ基盤・ETL・監査機能を提供する Python パッケージです。J-Quants API と RSS を用いたデータ収集、DuckDB によるスキーマ定義・永続化、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）などを備え、戦略層・実行層の基盤となる機能群を提供します。

主な設計方針
- データ取得は冪等性を重視（DuckDB への INSERT は ON CONFLICT で更新）。
- J-Quants API に対してはレート制限・リトライ・トークン自動リフレッシュを実装。
- RSS ニュース収集は SSRF・XML Bomb 等に対する防御（defusedxml、ホスト検証、サイズ制限）を備える。
- 品質チェックは Fail-Fast ではなく問題を収集し呼び出し元が判断できるようにする。
- 監査ログは UUID 連鎖でシグナル→発注→約定をトレース可能にする。

機能一覧
--------
- J-Quants クライアント
  - 株価日足（OHLCV）取得（fetch_daily_quotes）
  - 財務データ（四半期 BS/PL）取得（fetch_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar）
  - トークン取得・自動リフレッシュ（get_id_token）
  - レートリミッタ、リトライ（指数バックオフ、401 時トークンリフレッシュ）
- ニュース収集（RSS）
  - RSS 取得・前処理（URL 除去、空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性確保
  - SSRF 対策（スキーム検証、プライベートアドレスブロック、リダイレクト検査）
  - DuckDB への冪等保存（raw_news, news_symbols）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化（init_schema）
  - 監査ログ（signal_events, order_requests, executions）初期化（init_audit_schema / init_audit_db）
- ETL パイプライン
  - 差分更新（最終取得日ベースの差分取得 + backfill）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリ（run_daily_etl）で一括実行
- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・期間内営業日取得
  - 夜間バッチ更新ジョブ（calendar_update_job）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行

セットアップ手順
----------------

前提
- Python 3.10+（typing に | 等が使われているため）
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

推奨: 仮想環境を作成してからインストールしてください。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数（Settings により参照）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意（デフォルトあり）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）

使い方（簡易サンプル）
--------------------

1) DuckDB スキーマ初期化

```python
from kabusys.config import settings
from kabusys.data import schema

# 設定されたパス（デフォルト data/kabusys.duckdb）へスキーマを作成して接続を受け取る
conn = schema.init_schema(settings.duckdb_path)
```

2) J-Quants トークン取得（明示的に取得したい場合）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

3) 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) RSS ニュース収集を実行して DB へ保存

```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードのセット。提供がなければ紐付け処理をスキップする
known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # 各ソースの新規保存件数
```

5) カレンダー関連ユーティリティ

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

主な API 関数（参考）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / get_id_token
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.quality.run_all_checks
- kabusys.data.calendar_management.calendar_update_job / is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- kabusys.data.audit.init_audit_schema / init_audit_db

自動ロード・.env の挙動
---------------------
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し、.env を自動読み込みします。
- 読み込み順: OS 環境変数（既存） > .env > .env.local（.env.local は上書き）
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル）
-----------------------------
- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース取得・保存
    - schema.py               -- DuckDB スキーマ定義・初期化
    - pipeline.py             -- ETL パイプライン（差分更新・日次ETL）
    - calendar_management.py  -- マーケットカレンダー管理
    - quality.py              -- データ品質チェック
    - audit.py                -- 監査ログ（発注→約定トレーサビリティ）
    - pipeline.py             -- ETL 実行ロジック（含む品質チェック）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（注）strategy / execution / monitoring パッケージはエントリポイントを用意しており、各自で戦略・実行ロジックを実装して統合できます。

設計上の注意点・運用上のヒント
------------------------------
- J-Quants API のレート制限（120 req/min）に合わせた内部 RateLimiter を実装していますが、大量ページネーションでの連続実行時は適切な間隔を開ける運用をしてください。
- DuckDB のファイルパスは settings.duckdb_path で管理されています。バックアップや排他（複数プロセス同時書き込み）に注意してください。
- ニュース収集時は外部フィードに依存するため、失敗耐性を考えソース単位での例外処理が組み込まれています。ソース追加は DEFAULT_RSS_SOURCES を拡張してください。
- 監査ログは削除しない前提です。容量管理のために古い監査ログの別途アーカイブ方針を検討してください。
- 品質チェック結果（QualityIssue）は ETL の停止判断には使わない設計です（呼び出し元で扱いを決定）。

トラブルシューティング
----------------------
- 環境変数未設定で ValueError が発生する場合は .env を確認してください（.env.example がある場合は参照）。
- DuckDB 接続エラーやテーブル不整合が発生した場合は、スキーマ初期化を再実行（init_schema）するか、必要に応じてデータベースファイルの整合性を確認してください。
- RSS 取得でプライベートホストや不正スキームによりスキップされることがあります（セキュリティ対策のため）。外部公開フィードを使用してください。

ライセンス・貢献
----------------
- 本リポジトリにライセンスや貢献ルールが含まれている場合はそちらに従ってください。

以上が README の概要です。必要であれば以下を追加で作成できます:
- .env.example の雛形
- 実運用向けのデプロイ手順（systemd / Airflow / cron 等）
- ユニットテストの実行方法と CI 設定例