# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けデータ基盤・ETL・監査・収集モジュール群をまとめたライブラリです。J-Quants API や RSS フィードからデータを取得して DuckDB に格納し、品質チェック・カレンダー管理・ニュース収集・監査ログを提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 環境変数ベースの設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可）
  - 必須項目はランタイムで検証
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存
- ETL パイプライン
  - 差分更新（最終取得日からの差分／バックフィル対応）
  - 市場カレンダー先読み、品質チェック連携（欠損・スパイク・重複・日付不整合）
  - 日次 ETL のメインエントリポイント
- ニュース収集（RSS）
  - RSS フィードから記事を集め、URL 正規化・トラッキングパラメータ除去、SHA-256 による記事ID生成（先頭32文字）
  - SSRF 対策（スキーム検証 / プライベートIPブロッキング / リダイレクト検査）
  - レスポンスサイズ制限・gzip 解凍後のサイズ検査（DoS対策）
  - DuckDB へ冪等保存（INSERT ... RETURNING で挿入されたIDを返す）
  - 記事と銘柄コードの紐付け支援（テキストから 4 桁銘柄コード抽出）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義・初期化
  - インデックス定義、監査ログ用スキーマ分離（init_audit_schema 等）
- カレンダー管理
  - 営業日判定・前後営業日探索・期間内営業日取得・SQ日判定
  - DB にない場合は曜日ベースのフォールバック
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を SQL ベースで検出し QualityIssue リストとして返す
- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを保持する監査テーブル群
  - UUID ベースの冪等キー設計、UTC タイムスタンプ保存

---

## 必要条件 / 依存パッケージ

- Python 3.9+
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml

（実際のインストール要件はプロジェクトの packaging / requirements を参照してください）

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt  （requirements がある場合）
   - または最低限:
     - pip install duckdb defusedxml

4. 環境変数 / .env ファイルを用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（デフォルト）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（Settings が参照するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意・デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト "INFO"
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"

例 .env（最小）
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## 使い方（主要な API / 実行例）

ここでは主要な操作のサンプル（Python）を示します。

- スキーマ初期化（DuckDB ファイルを作成して全テーブルを作る）
```python
from kabusys.data import schema

# デフォルトパスを使う場合:
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

- 監査スキーマの初期化（既存接続に追加）
```python
from kabusys.data import audit

# conn は上で得た DuckDB 接続
audit.init_audit_schema(conn)
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources は {source_name: rss_url}。省略時は DEFAULT_RSS_SOURCES を使用。
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # sourceごとの新規保存件数
```

- 市場カレンダー更新ジョブ（夜間バッチ向け）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- 直接 J-Quants API を呼ぶ（取得・保存）
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェック実行
```python
from kabusys.data import quality, schema

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for iss in issues:
    print(iss)
```

---

## 環境変数 / 設定の詳細

- 自動 .env 読み込み
  - プロジェクトルートは __file__ の親階層を上へ探索して `.git` または `pyproject.toml` が見つかった場所と判定します。そこから `.env` / `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テストなどで自動読み込みを止めたい場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings による検証
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかである必要があります。
  - LOG_LEVEL は標準レベルのいずれか（"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"）である必要があります。

---

## 主要モジュール・公開 API の要約

- kabusys.config
  - settings: Settings インスタンス。JQUANTS_REFRESH_TOKEN 等のプロパティを提供。
- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...), run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source), run_news_collection(conn, ...)
  - save_raw_news(), save_news_symbols(), extract_stock_codes(), preprocess_text()
- kabusys.data.calendar_management
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- kabusys.data.quality
  - run_all_checks(), check_missing_data(), check_spike(), check_duplicates(), check_date_consistency()
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                             -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                    -- J-Quants API クライアントと DuckDB 保存
    - news_collector.py                    -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                            -- DuckDB スキーマ定義と初期化
    - pipeline.py                          -- ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py               -- マーケットカレンダー管理
    - audit.py                             -- 監査ログスキーマ（signal/order/execution）
    - quality.py                           -- データ品質チェック
  - strategy/
    - __init__.py                          -- 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                          -- 発注・約定管理の拡張ポイント
  - monitoring/
    - __init__.py                          -- 監視・メトリクス関連（今後実装）

---

## 開発・貢献メモ

- 新機能を追加する場合は、DuckDB スキーマ更新が必要なら schema.py を更新し、互換性・冪等性（CREATE TABLE IF NOT EXISTS）を保ってください。
- 外部 API 呼び出しはリトライ・レート制御を守る設計になっています。トークンや認証まわりの処理を変更するときは無限再帰やトークンキャッシュの扱いに注意してください。
- ニュース収集は外部コンテンツを扱うため、XML パースは defusedxml を使い、SSRF 対策（スキーム検査 / プライベート IP ブロック）を行っています。これらの安全措置を削除・変更する場合はリスクを理解してください。

---

README に書かれている以外の使い方や拡張、CI/デプロイ手順などが必要であれば、追加で詳しいドキュメントを作成します。必要な部分（例: CLI コマンド、systemd タイマーでの ETL 実行、Slack 通知連携サンプル等）を教えてください。