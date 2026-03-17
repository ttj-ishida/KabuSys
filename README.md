# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（コアモジュール群）

このリポジトリは、データ収集（J-Quants / RSS）、データベーススキーマ、ETLパイプライン、品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）など、自動売買システムの基盤機能を提供します。

## 主な特徴（概要）
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPXマーケットカレンダーを取得
  - レートリミット（120 req/min）制御、リトライ、トークン自動リフレッシュ
  - 取得時刻（fetched_at）をUTCで記録してLook‑ahead biasを抑制
  - DuckDBへの冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）
  - RSSフィードの取得、前処理（URL除去、空白正規化）、記事IDは正規化URLのSHA-256で生成
  - SSRF対策、gzip上限、XMLパースの安全化（defusedxml）
  - DuckDBへ冪等保存（INSERT ... RETURNING）
  - 本文から銘柄コード（4桁）抽出（既知コードセットでフィルタ）
- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit（監査）層のテーブル定義
  - インデックス定義、外部キー、制約による整合性確保
- ETLパイプライン
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次ETLエントリ（run_daily_etl）でカレンダー→価格→財務→品質チェックを実行
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、夜間バッチ更新ジョブ
- 監査ログ（audit）
  - シグナル→発注要求→約定の階層トレーサビリティ（UUIDベース）
  - order_request_id を冪等キーとして二重発注を防止

---

## 必要な環境変数（主なもの）
以下はアプリケーションが参照する主な環境変数です（Settings クラス参照）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — SQLite（監視用）パス。デフォルト: data/monitoring.db

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動的に読み込みます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発用）
以下はローカルで動かすための基本手順例です。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は最低限次のパッケージが必要です:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （パッケージは実際のプロジェクトで requirements に合わせてください）

4. 環境変数を設定（.env をプロジェクトルートに置くことを推奨）

---

## 使い方（主要なコード例）

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

- J-Quants ID トークン取得（内部で settings のリフレッシュトークンを使用）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

- 日次 ETL 実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema 実行を想定
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL（価格のみ）:
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- ニュース収集（RSS）とDB保存
```python
from kabusys.data import news_collector as nc
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
# 既知の銘柄コードセットを与えると銘柄紐付けまで行う
known_codes = {"7203", "6758", "9432"}  # 例
results = nc.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- マーケットカレンダー夜間バッチ更新
```python
from kabusys.data import calendar_management as cm
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = cm.calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- データ品質チェック（個別／全件）
```python
from kabusys.data import quality
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 主要モジュールと責務（機能一覧）
- kabusys.config
  - 環境変数・設定管理。プロジェクトルートの .env を自動ロード（無効化可）。
  - Settings クラスで環境値を型安全に取得。
- kabusys.data.jquants_client
  - J-Quants API とのやり取り。fetch_*/save_* 関数を提供。
  - RateLimiter、リトライ、トークンリフレッシュ、DuckDBへの冪等保存実装。
- kabusys.data.news_collector
  - RSS 取得／前処理／DuckDB への保存。SSRF対策、gzip上限、XMLの安全パースなどを実装。
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（init_schema）。
  - Raw / Processed / Feature / Execution のテーブル定義、インデックス。
- kabusys.data.pipeline
  - ETL の差分更新ロジック、日次ETL（run_daily_etl）。
  - backfill、calendar lookahead、品質チェック呼び出し。
- kabusys.data.calendar_management
  - market_calendar に基づく営業日判定、next/prev/get_trading_days、calendar_update_job。
- kabusys.data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）定義と初期化。
- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）。QualityIssue 型で結果を返す。
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 各パッケージの入り口（__init__.py）。戦略ロジック・実行（ブローカー接続）・監視ロジックはここに実装される想定。

---

## ディレクトリ構成
（重要ファイル・モジュールの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・init_schema
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（日次ETL等）
    - news_collector.py      — RSS ニュース収集・保存
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ（発注・約定トレーサビリティ）
    - quality.py             — 品質チェック
  - strategy/
    - __init__.py
    — 戦略 (未実装/拡張ポイント)
  - execution/
    - __init__.py
    — 発注 / ブローカー連携 (未実装/拡張ポイント)
  - monitoring/
    - __init__.py
    — 監視 / アラート (未実装/拡張ポイント)

---

## 注意事項 / 実運用上のヒント
- 設定は必ず秘密情報を含むため .env をソース管理しないでください。
- J-Quants のレート制限や kabu API の認証・パスワード管理は運用に合わせて適切に管理してください。
- DuckDB はローカルファイルベースのデータベースです。複数プロセスからの同時書き込みなど運用条件に注意してください。
- news_collector の extract_stock_codes は既知銘柄コードセットを必要とします。全銘柄リストを用意して与えることで紐付け精度が向上します。
- ETL 実行は定期ジョブ（cron/airflow/任意のスケジューラ）で回す想定です。run_daily_etl は idempotent（差分取得）なので定期実行に適しています。
- ロギング（LOG_LEVEL）を調整して、本番では INFO/ERROR、デバッグ時に DEBUG を使用してください。

---

## 貢献 / 拡張ポイント
- strategy パッケージに具体的な売買戦略（特徴量生成 → シグナル生成）を実装
- execution パッケージに各ブローカー用のコネクタ（kabuステーションや他ブローカー）を実装
- monitoring パッケージで Prometheus / Slack / Datadog 連携を追加
- News の言語解析や NLP による感情スコアを ai_scores テーブルへ投入する処理を追加

---

READMEの内容はこのコードベースの現状に基づく概要・使い方ガイドです。より詳細な運用手順（CI/CD、インフラ、権限管理など）はプロジェクト方針に合わせて追加してください。必要であれば、このREADMEをベースに導入手順のスクリプトやサンプル設定ファイル（.env.example）を作成します。どの部分を優先して整備しましょうか？