# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J‑Quants API や RSS などから市場データ・ニュースを取得し、DuckDB に蓄積、品質チェック・ETL・監査ログを備えたデータパイプラインを提供します。

主な設計方針：
- API レート制限・リトライ・トークン自動リフレッシュ対応
- データ取得時刻（fetched_at）を記録して Look‑ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT）で二重保存を防止
- RSS 収集は SSRF・XML Bomb 等の攻撃対策あり
- 品質チェックを集約して ETL 後にレポート可能

---

## 機能一覧

- 環境設定管理
  - .env / .env.local からの自動読み込み（必要に応じて無効化可能）
  - 必須設定の検証（settings オブジェクト）
- J‑Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限、再試行、401 時のトークン自動更新
  - DuckDB への冪等保存関数（save_*）
- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新、バックフィル、カレンダー先読み
  - 日次 ETL エントリ（run_daily_etl）
  - 品質チェック（quality モジュール）と統合
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードから記事収集・前処理・DuckDB への冪等保存
  - 記事ID は正規化 URL の SHA‑256（先頭 32 文字）
  - SSRF / リダイレクト検査、最大レスポンスサイズ制限、gzip 解凍チェック
  - 銘柄コード抽出と news_symbols への紐付け
- スキーマ定義・初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス、FK、制約などを含む冪等初期化
- カレンダー管理（営業日判定、next/prev/trading days）
- 監査ログスキーマ（signal_events / order_requests / executions）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 動作要件

- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - defusedxml

（ネットワーク呼び出しは標準ライブラリ urllib を使用していますが、J‑Quants や外部 API の認証情報が必要です）

---

## セットアップ手順（例）

1. リポジトリをクローン（または本パッケージをプロジェクトに取り込み）
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   ※ パッケージ配布・pyproject があれば `pip install -e .` を使ってください。
4. 環境変数を設定（.env をプロジェクトルートに置くことを想定）
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意（デフォルトあり）
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|...
     - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB のパス デフォルト data/monitoring.db)

   .env の自動読み込みは、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば無効化できます（テスト用）。

---

## .env（例）

```
# .env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DB スキーマ作成）

DuckDB のスキーマ初期化例：

```python
from kabusys.data import schema

# ファイル DB を作成して全テーブルを初期化
conn = schema.init_schema("data/kabusys.duckdb")

# 監査ログテーブルを別途初期化する場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- init_schema は冪等（存在するテーブルはスキップ）です。
- ":memory:" を渡すとインメモリ DB になります。

---

## 使い方（主要な例）

- 設定値へのアクセス
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
print(settings.env, settings.is_live)
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

- RSS ニュース収集（既知銘柄リストと一緒に）
```python
from kabusys.data.news_collector import run_news_collection

# sources を省略すると DEFAULT_RSS_SOURCES を使用
# known_codes: 例えば DB から取得した銘柄コードの集合
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J‑Quants から日足を直接取得して保存
```python
from kabusys.data import jquants_client as jq

records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## モジュール概要

- kabusys.config
  - .env 読み込みロジック、Settings クラス（settings インスタンス）
- kabusys.data.jquants_client
  - API 呼び出し、トークン更新、fetch/save 系関数
- kabusys.data.schema
  - DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution 層）
- kabusys.data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェック）
- kabusys.data.news_collector
  - RSS 取得、前処理、DuckDB へ冪等保存、銘柄抽出
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック
- kabusys.data.calendar_management
  - 営業日判定・次営業日取得・カレンダー更新ジョブ
- kabusys.data.audit
  - 監査ログ（signal / order_request / execution）スキーマ初期化
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略・執行・監視のエントリパッケージ（実装の拡張を想定）

---

## ディレクトリ構成

（要約。実際は src/kabusys 以下に各モジュールが配置されています）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 運用上の注意・ヒント

- 環境変数は OS 環境 > .env.local > .env の順で適用されます。テスト時に自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J‑Quants API はレート制限（120 req/min）があります。jquants_client 内で固定間隔レートリミッタが実装されていますが、大量取得時は配慮してください。
- news_collector は外部 URL を扱うため SSRF 対策・XML パース対策が施されていますが、企業運用では追加のネットワーク制限やタイムアウト設定などを行ってください。
- DuckDB のファイルは定期的にバックアップしてください。監査ログは削除前提ではありません。

---

## さらに進める（拡張案）

- strategy パッケージに戦略実装を追加し、signals → order_queue 経路を実装
- execution パッケージで kabu ステーション等のブローカー連携を実装
- Slack 通知や Prometheus メトリクスによる監視の追加
- CI での品質チェック・schema 初期化テスト

---

README はここまでです。個別の使い方（例: ETL スケジュール化、Kabu API 統合、Slack 通知実装等）について詳細な手順が必要なら、使いたいユースケースを教えてください。必要に応じてサンプルスクリプトや systemd / cron / Airflow 用タスクの例を作成します。