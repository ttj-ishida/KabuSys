# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants などの外部 API から市場データ・財務データ・ニュースを収集し、DuckDB に保存、品質チェック・監査ログ・カレンダー管理・ETL パイプラインを提供します。

---

## プロジェクト概要

- 名前: KabuSys
- バージョン: 0.1.0（src/kabusys/__init__.py）
- 目的: 日本株の自動売買システムのためのデータ収集・保存・ETL・モニタリング基盤を提供する。
- 主な技術:
  - DuckDB をデータストアとして使用
  - J-Quants API 経由で株価（日足）、財務（四半期 BS/PL）、JPX カレンダー等の取得
  - RSS からニュース収集（XML 解釈は defusedxml を利用）
  - データ品質チェック、監査ログ（発注・約定のトレーサビリティ）
  - 設定は環境変数 / .env により管理

---

## 主な機能一覧

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時はリフレッシュトークンで自動更新
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義とインデックス
  - 冪等な初期化（存在する場合はスキップ）

- ETL パイプライン
  - 差分取得（最終取得日を元に未取得分のみ取得）
  - backfill による直近再取得（API 後出し修正対応）
  - 市場カレンダー先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集
  - RSS フィード取得、URL 正規化（UTM 等除去）、SHA-256（先頭32文字）で記事 ID 生成
  - SSRF 対策、受信サイズ制限（デフォルト 10 MB）、gzip 対応
  - raw_news / news_symbols への冪等保存

- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、期間内営業日列挙
  - カレンダー夜間更新ジョブ（バックフィル含む）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、発注から約定までのトレーサビリティ
  - order_request_id を冪等キーとして二重発注を防止

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比）、重複、将来日付や非営業日の検出
  - QualityIssue オブジェクトで問題を返却

---

## 必要条件 / 依存パッケージ（概略）

- Python 3.10+
- duckdb
- defusedxml
- （その他標準ライブラリ: urllib, datetime, logging, etc.）

pip などのパッケージ管理によりインストールしてください。具体的な requirements.txt はリポジトリに応じて用意してください。

---

## セットアップ手順

1. リポジトリをクローン／取得する。

2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

3. 依存関係をインストール:
   - pip install duckdb defusedxml
   - （プロジェクトの setup.cfg / pyproject.toml / requirements.txt があればそれを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（src/kabusys/config.py による自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の例（最低限必要なもの）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb    # 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot 用トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化 (1)

各必須項目は src/kabusys/config.py の Settings から参照します。未設定の場合は例外が発生します。

---

## 使い方（簡易サンプル）

以下は Python インタラクティブやジョブスクリプトから利用する例です。

- DuckDB スキーマ初期化 + 接続
```py
from kabusys.data import schema
from kabusys.config import settings

# 設定で指定されたパスに DB を初期化
conn = schema.init_schema(settings.duckdb_path)

# またはインメモリ DB
# conn = schema.init_schema(":memory:")
```

- 日次 ETL 実行
```py
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- ニュース収集（RSS）を実行して保存
```py
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- J-Quants のトークン取得（必要に応じて）
```py
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得
```

- 監査ログの初期化（監査専用 DB を分ける場合）
```py
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 品質チェック単体実行
```py
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 主要な API（モジュール／関数まとめ）

- kabusys.config
  - settings: Settings オブジェクト（環境変数参照）

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

---

## ディレクトリ構成

リポジトリ内の主要構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールは役割ごとに分割されており、data 以下にデータ取得・保存・品質・監査関連のロジックがまとまっています。

---

## 運用上の注意 / 実装上のポイント

- J-Quants API のレート制限（120 req/min）を尊重するため、jquants_client は固定間隔のスロットリングを実装しています。大量データの取得時も制限に注意してください。
- jquants_client は 401 を検知した場合、自動でリフレッシュトークンから ID トークンを取得して 1 回だけ再試行します。
- news_collector は SSRF や XML Bomb、巨大レスポンスに対する保護（URL スキーム検証、プライベートアドレス拒否、受信サイズ上限、defusedxml）を実装しています。
- DuckDB のテーブル作成は冪等（IF NOT EXISTS）なので、本番ジョブで毎回 init_schema を呼んでも安全です。
- audit.init_audit_schema はタイムゾーンを UTC に固定します（SET TimeZone='UTC'）。
- config の自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 開発 / テスト

- 単体テストでは以下が有用です:
  - jquants_client の HTTP 呼び出し部分は urllib を使っているためモック可能です。_urlopen 等の内部関数を差し替えてテストしやすく設計されています。
  - news_collector._urlopen はテスト用にモックして外部ネットワークに依存しないようにできます。
  - DuckDB の ":memory:" を使えばインメモリ DB でスキーマ作成・ETL 動作をテストできます。

---

必要であれば、README に実行スクリプト例（systemd timer / cron / Airflow / Prefect などのジョブ化）や .env.example の完全なテンプレート、CI 設定例も追加します。どの情報を優先して追加しますか？