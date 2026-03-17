# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、ニュース収集、監査ログ用スキーマなど、トレーディングシステムの基盤となる機能群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリです。主に以下を目的としています。

- J-Quants API からの株価・財務・マーケットカレンダーの取得と DuckDB への永続化
- RSS フィードからのニュース記事収集と銘柄紐付け
- ETL（差分取得・バックフィル）、データ品質チェック
- 監査ログ（signal → order → execution のトレース）用スキーマ
- 設定の環境変数管理（.env 自動読み込み機能）

設計方針として、API レート制御・リトライ・冪等性（ON CONFLICT）・SSRF対策・XMLパースの安全化など実運用を意識した実装がなされています。

---

## 主な機能一覧

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境ごとの検証（development / paper_trading / live）
  - 必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン自動取得・キャッシュ
  - レートリミッタ（120 req/min）
  - 再試行（指数バックオフ、401 時はトークン刷新を1回実行）
  - データ取得: 日次株価（OHLCV）、財務（四半期）、マーケットカレンダー
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・パース（defusedxml）
  - URL 正規化とトラッキングパラメータ除去
  - 記事ID を正規化URL の SHA-256（先頭32文字）で生成し冪等性確保
  - SSRF 対策（スキーム検証、リダイレクト検査、プライベートホスト拒否）
  - レスポンスサイズ制限・gzip 解凍対策
  - DuckDB への記事保存・銘柄紐付け（INSERT ... RETURNING を使用）

- スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義
  - インデックス作成
  - init_schema(db_path) による冪等初期化

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日に基づく差分/バックフィル）
  - カレンダー先読み（lookahead）
  - 品質チェック呼び出し（kabusys.data.quality）
  - run_daily_etl による一括実行と結果集約（ETLResult）

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合（未来日付・非営業日）など
  - QualityIssue オブジェクトのリストで問題を返す（error / warning）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義
  - init_audit_schema / init_audit_db による初期化
  - 発注フローを UUID でトレース可能にする設計

---

## 必要要件（推奨）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging, datetime 等）を多用

（プロジェクトの pyproject.toml / requirements.txt があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン（省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布設定がある場合）pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env（必要最小限）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意:
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。
- LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれか。

5. DuckDB スキーマの初期化
   - Python REPL やスクリプトで:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)
```
   - 監査ログテーブルを追加する場合:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（よく使う例）

1. J-Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用して取得
```

2. 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

3. ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄コードの集合（例: {'7203', '6758', ...}）を渡すと銘柄抽出を行う
res = run_news_collection(conn, known_codes={'7203','6758'})
print(res)  # {source_name: 新規保存件数, ...}
```

4. DuckDB に生データを保存する例（fetch + save）
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, recs)
print(f"saved={saved}")
```

5. 監査用 DB を別途初期化する例
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 主な API / 関数一覧（抜粋）

- 設定
  - kabusys.config.settings: Settings オブジェクト（プロパティで環境変数を取得）

- J-Quants クライアント
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- ニュース収集
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- スキーマ / DB
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)

- ETL
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...)

- 監査ログ
  - init_audit_schema(conn)
  - init_audit_db(db_path)

- 品質チェック
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

---

## 注意点 / 実運用上のポイント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CIやテストで自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client に組み込まれたレートリミッタとリトライを前提に実装されています。大量取得時は間隔に注意してください。
- ニュース収集では SSRF・XML Bomb 対策を行っていますが、実環境ではさらに HTTP タイムアウト、接続の監視、リトライ方針を設計してください。
- DuckDB のファイルパスはデフォルトで `data/kabusys.duckdb`（settings.duckdb_path）です。運用時には永続ストレージと定期バックアップを検討してください。
- run_daily_etl は各ステップを個別に例外処理しているため、あるステップで失敗しても他のステップは継続されます。返却された ETLResult を見て適切にアラート/対処してください。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）で設計されています。監査データの運用ルールを定めてください。

---

## ディレクトリ構成

リポジトリ内の主なファイル / モジュール構成（抜粋）:

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
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュールの責務:
- kabusys.config: 環境変数と設定の読み取り・検証
- kabusys.data.*: データ取得、保存、ETL、品質、監査に関連する実装
- kabusys.strategy / execution / monitoring: 戦略・発注・監視ロジック用の名前空間（実装は各自追加）

---

## 今後の拡張ポイント（例）

- 戦略実装（kabusys.strategy）と発注ドライバ（kabuステーション / 証券会社 API 連携）
- Slack / メトリクス連携（アラート・監視）
- CI/CD による定期 ETL 実行のジョブ化（例: GitHub Actions / Airflow / cron）
- テストカバレッジの拡充（ユニット・統合テスト）
- 設計書（DataPlatform.md, 使用するテーブル定義や運用フロー）の整備

---

必要であれば README にサンプルスクリプト（CLIツール化例）、さらに詳しい運用手順、.env.example のテンプレート、または各モジュールの API ドキュメント化（Sphinx 等）を追記できます。どの追加情報が必要か教えてください。