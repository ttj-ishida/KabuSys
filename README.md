# KabuSys — 日本株自動売買基盤

KabuSys は日本株向けのデータ収集・ETL・監査基盤を提供するライブラリ群です。J-Quants API や RSS を用いたデータ取り込み、DuckDB による永続化、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレース）など、アルゴリズム売買システムの基盤機能をまとめています。

本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

注意: このリポジトリは src/ 配下にパッケージを配置する一般的な Python プロジェクト構成を想定しています。

---

目次
- プロジェクト概要
- 機能一覧
- 必要な環境・依存関係
- セットアップ手順
- 環境変数（.env）について
- 使い方（コード例）
  - DuckDB スキーマ初期化
  - 日次 ETL の実行
  - RSS ニュース収集ジョブ
  - カレンダー更新ジョブ
  - 監査ログスキーマ初期化
- よく使う API サマリ
- ディレクトリ構成

---

プロジェクト概要
- 目的: J-Quants 等の外部データソースから取得した市場データ・財務データ・ニュース等を DuckDB に蓄積し、品質チェック・特徴量作成・シグナル生成・発注監査までつなげる基盤を提供する。
- 設計方針のハイライト:
  - API レート制御・リトライ・トークン自動更新を備えた耐障害性のあるデータ取得
  - DuckDB を用いた冪等（ON CONFLICT）保存
  - ニュース収集における SSRF 防止、XML 攻撃対策、トラッキングパラメータ除去
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（発注→約定）を追跡可能にするスキーマ

---

機能一覧
- データ取得
  - J-Quants から株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得（ページネーション対応）
  - RSS フィードからニュース記事を取得・前処理・ID一意化（SHA-256）して保存
- 永続化 / スキーマ
  - DuckDB 上に Raw / Processed / Feature / Execution / Audit 層のスキーマを定義・初期化
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）をサポート
- ETL パイプライン
  - 差分取得（最終取得日からの差分）+ バックフィルで API の後出し修正に対応
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL 統合エントリポイント
- カレンダー管理
  - JPX カレンダーの夜間差分更新ジョブ
  - 営業日 / SQ 日判定、前後営業日の取得等のユーティリティ
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル
  - UTC タイムスタンプ固定、トランザクションサポート
- その他
  - 設定管理（.env または環境変数の読み込み、自動ロード、保護キー）
  - ロギングレベル判定（環境変数）

---

必要な環境・依存関係
- Python 3.10 以上（`X | Y` の型注釈が使用されているため）
- 主要依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, logging, json, datetime, pathlib, typing など

依存は pyproject.toml / requirements.txt があればそれに従ってください。手元にない場合は最低限次のようにインストールします:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージを editable install する場合（プロジェクトルートに pyproject.toml がある想定）
pip install -e .
```

---

セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存ライブラリをインストール（上記参照）
3. 環境変数を設定（.env ファイルをプロジェクトルートに置くか OS 環境変数で設定）
   - プロジェクトはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
4. DuckDB スキーマを初期化
   - 既定の DB パスは DUCKDB_PATH 環境変数（デフォルト: data/kabusys.duckdb）
   - 監査ログ専用 DB を使う場合は init_audit_db を利用

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーションなどの API パスワード
  - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
- 任意 / デフォルトあり:
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- 自動 .env ロードの制御:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効にできます

.env の読み込み優先度:
- OS 環境変数 > .env.local > .env
- プロジェクトルートはこのモジュールの __file__ を起点に .git または pyproject.toml を探索して決定します（CWD 依存しない）

---

使い方（代表例）

Python コンソールやスクリプトから直接呼び出して操作します。以下は最小限の使用例です。

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # パスは任意、:memory: 可
```

2) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETLResult の内容を確認
```

run_daily_etl の主要な引数:
- target_date: ETL 対象日（省略で今日）
- id_token: J-Quants の id_token を注入可能（テスト向け）
- run_quality_checks: True/False（デフォルト True）
- backfill_days: 後出し修正吸収のための再取得日数（デフォルト 3）

3) RSS ニュース収集ジョブ

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# sources を渡さない場合は DEFAULT_RSS_SOURCES を使います
known_codes = {"7203", "6758"}  # 銘柄コードセットを渡すと紐付けを行う
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # 各ソースの新規保存数を返す
```

fetch_rss や save_raw_news は個別にテストや再利用できます。

4) カレンダー更新ジョブ（夜間バッチなどで利用）

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

5) 監査ログスキーマの初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

---

よく使う API サマリ（モジュール・関数）
- kabusys.config
  - settings: 環境変数からアプリ設定を取得（settings.jquants_refresh_token など）
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=...)
- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

各関数の詳細は docstring を参照してください。

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（取得・保存）
      - news_collector.py     # RSS ベースのニュース収集
      - pipeline.py          # ETL パイプライン（差分取得・品質チェック）
      - schema.py            # DuckDB スキーマ定義・初期化
      - calendar_management.py  # カレンダー管理ユーティリティ
      - audit.py             # 監査ログスキーマ初期化
      - quality.py           # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

この README はコード内の docstring と設計を要約したものです。詳細な挙動（パラメータや返り値の仕様、エラー処理など）は各モジュールの docstring を参照してください。

---

トラブルシューティング / 注意点
- Python バージョンは 3.10 以上を推奨します。型記法や一部の言語機能で必要です。
- .env の自動読み込みはプロジェクトルート（.git や pyproject.toml）を基準に行います。CI やテストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レート制限に合わせたスロットリングとリトライ実装がありますが、大量同時実行は避けてください。
- news_collector は外部 URL を取得するため SSRF 対策や Content-Length / gzip 解凍上限を実装しています。実運用時は HTTP タイムアウトや例外ハンドリングを適切に設定してください。

---

ライセンスやその他
- このリポジトリのライセンス情報や貢献ガイドがある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（本 README には含まれていません）。

ご不明点があれば、どの機能について詳しく知りたいか教えてください。README に追記するサンプルスクリプトや CLI 提案も作成できます。