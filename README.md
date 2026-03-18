# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（参考実装）。

このリポジトリはデータ取得・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、
監査ログ（オーダー/約定のトレーサビリティ）など、自動売買システムの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API を用いた市場データ（株価・財務・マーケットカレンダー）の取得と DuckDB への保存
- RSS フィードからのニュース収集とテキスト前処理、銘柄コードの抽出・紐付け
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー（JPX）管理と営業日判定ロジック
- 監査ログ（シグナル → 発注 → 約定）用スキーマ初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上のポイント:
- DuckDB を永続化ストアとして利用（:memory: も可）
- API 呼び出しのレート制御、再試行、トークン自動更新を実装
- DB 操作は冪等的（ON CONFLICT / DO UPDATE / DO NOTHING）で再実行に安全
- セキュリティ対策（RSS パーサーに defusedxml、SSRF 対策、応答サイズ制限 等）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レートリミット、リトライ、401 時の自動トークンリフレッシュ
  - DuckDB への保存ユーティリティ（save_daily_quotes 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・XML パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去、記事ID生成（SHA256）
  - SSRF・リダイレクト対策、受信サイズ制限、DuckDB へのバルク保存
  - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - init_schema(db_path) による初期化（冪等）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 差分更新（最終取得日ベース）・backfill 対応
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job による夜間差分更新処理
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化
  - init_audit_db / init_audit_schema
- 品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks による一括実行。QualityIssue オブジェクトで結果返却

---

## 要件 / 前提

- Python 3.10 以上（型注釈の | 合併等を使用）
- ライブラリ（代表例）:
  - duckdb
  - defusedxml

実行環境によっては追加で requests 等が必要になるケースがありますが、
本コードは標準ライブラリの urllib をベースに実装されています。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# または requirements.txt があれば: pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成して依存パッケージをインストール
3. 環境変数を設定（.env または OS 環境変数）
   - 自動ロード: パッケージ起点で .git または pyproject.toml を探し、ルートにある .env/.env.local を読み込みます。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. DuckDB データベース初期化

必須の主要環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意／推奨:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で .env 自動ロードを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な例）

以下は Python スクリプトや REPL からの利用例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 結果は ETLResult オブジェクト
print(result.to_dict())
```

- 部分的な ETL（株価のみ）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(fetched, saved)
```

- J-Quants API から生データ取得（トークン自動処理）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))
```

- ニュース収集ジョブを実行して保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄リスト（例）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- マーケットカレンダーの判定
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 3, 20)))
print(next_trading_day(conn, date(2026, 3, 20)))
```

- 監査ログスキーマ初期化（監査専用DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- 設定値参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 環境変数が未設定だと ValueError
print(settings.env)  # development / paper_trading / live
```

---

## ディレクトリ構成

（重要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント + DuckDB 保存
    - news_collector.py      - RSS 取得・前処理・保存・銘柄抽出
    - schema.py              - DuckDB スキーマ定義 & init_schema/get_connection
    - pipeline.py            - ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py - マーケットカレンダー管理と営業日ロジック
    - audit.py               - 監査ログスキーマ（信頼性・トレーサビリティ）
    - quality.py             - データ品質チェック
  - strategy/
    - __init__.py            - （戦略モジュールを配置するためのパッケージ）
  - execution/
    - __init__.py            - （発注・ブローカー連携を置くためのパッケージ）
  - monitoring/
    - __init__.py            - （監視用モジュール）

---

## 開発上の注意点 / トラブルシューティング

- Python バージョン: 3.10 以上を推奨
- .env 自動読み込み
  - プロジェクトルートは __file__ を起点に親ディレクトリで .git または pyproject.toml を探して決定します。
  - 自動読み込みを抑止する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルの親ディレクトリが存在しない場合、init_schema や init_audit_db が自動で作成します。
- RSS フィードの取得では SSRF 対策としてリダイレクト先のホストの判定・スキーム検証を行います。内部ネットワークや非 http/https スキームは拒否されます。
- J-Quants API 呼び出しはレート制限（120 req/min）とリトライロジックが実装されていますが、実運用ではさらに注意深いレート管理が必要な場合があります。
- settings プロパティは必須値未設定時に ValueError を上げます。CI/本番環境では環境変数の管理を厳格に行ってください。
- DuckDB の SQL はパラメータバインド（?）を基本としていますが、DDL 等は文字列として実行しています。外部から注入される SQL 文字列への注意が必要です。

---

## 今後の拡張ポイント（案）

- 発注（execution）層の kabuステーションや証券会社 API 連携実装
- 戦略モジュールのサンプル（ポートフォリオ最適化、シグナル生成）
- モニタリング（Prometheus / Grafana 統合）、Slack 通知の実装
- CI テストとサンプルデータを用いた統合テスト

---

もし README に追加して欲しい項目（例: サンプル .env.example、運用手順、詳細な API 使用例、Docker 化手順など）があれば教えてください。必要に応じて追記します。