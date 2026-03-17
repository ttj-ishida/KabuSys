# KabuSys

日本株自動売買システムのライブラリ（パッケージ）です。  
データ取得・ETL・品質チェック・ニュース収集・監査ログなど、アルゴリズム取引基盤のコア機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API を使った株価・財務・市場カレンダーの取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いた三層データレイク構成（Raw / Processed / Feature）とスキーマ初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、冪等保存）
- 監査ログ（信号→発注→約定のトレーサビリティ管理）
- 簡易的な設定/環境変数管理（.env 自動読み込み）

設計上のポイント：
- 冪等性を重視（ON CONFLICT / RETURNING を多用）
- Look-ahead bias を避けるためにフェッチ時刻を UTC で記録
- 外部アクセスに対するセキュリティ対策（SSRF, XML Bomb, レスポンスサイズ制限 等）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック の順に実行
  - 差分取得・バックフィルロジックを備える
- data/schema.py
  - DuckDB のスキーマ定義・初期化（init_schema, get_connection）
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス
- data/news_collector.py
  - RSS フィードからニュース記事を収集・前処理・正常化・DB保存（save_raw_news / save_news_symbols）
  - URL 正規化、トラッキング除去、SSRF 対応、gzip サイズチェック、XML パースの堅牢化
- data/quality.py
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 問題は QualityIssue オブジェクトのリストで返却
- data/audit.py
  - 監査ログ用テーブル群（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db を提供
- config.py
  - 環境変数/.env の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で主要設定にアクセス
  - 自動 .env 読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提
- Python 3.10 以上（Union/Type hint に `|` を使用しているため）
- pip が使えること

1. リポジトリをクローン / パッケージを配置
2. 必要なパッケージをインストール（最低限）
   - duckdb
   - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   実際のプロジェクトでは requirements.txt / poetry 等に依存関係を記載してください。

3. 環境変数を設定
   - 環境変数は OS 環境、またはプロジェクトルートの `.env` / `.env.local` から自動で読み込まれます。
   - 自動読み込みを無効にしたい場合は、パッケージを import する前に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（config.Settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack チャンネル ID

任意 / デフォルト付き:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH       — デフォルト: data/kabusys.duckdb
- SQLITE_PATH       — デフォルト: data/monitoring.db
- KABUSYS_ENV       — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL         — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

ここでは代表的な利用例を示します。実行は Python スクリプトや REPL から行えます。

1) スキーマ初期化（DuckDB）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH の Path オブジェクト（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に使う有効銘柄コードセット（省略可）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4) 監査スキーマの初期化（監査用テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema

# 既に init_schema() で取得した conn を渡す
init_audit_schema(conn)
```

5) J-Quants API から直接データ取得（テスト／個別取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_market_calendar

# id_token を指定しなければ内部キャッシュから自動取得（リフレッシュ対応）
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
calendar = fetch_market_calendar()
```

注意点:
- ETL は各ステップで例外をキャッチして継続する設計です。戻り値 ETLResult の errors / quality_issues を確認してください。
- run_daily_etl 内で品質チェックを行い、その結果も返します（quality.run_all_checks）。
- ニュース収集は SSRF 等の安全策を取っていますが、公開環境での RSS ソースは信頼できるものを使用してください。

---

## ディレクトリ構成（抜粋）

以下は本リポジトリ内の主要ファイル・モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                     — DuckDB スキーマ定義と初期化
    - jquants_client.py             — J-Quants API クライアント（取得 & 保存）
    - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
    - news_collector.py             — RSS ニュース収集・保存
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ
    - audit.py                      — 監査ログスキーマ
  - strategy/
    - __init__.py                   — （戦略関連モジュールを格納）
  - execution/
    - __init__.py                   — （発注/約定関連モジュールを格納）
  - monitoring/
    - __init__.py                   — （監視・メトリクス関連）

---

## 補足 / 運用注意

- Python バージョン: 3.10 以上を推奨（型注釈に `X | Y` を使用）。
- 外部 API 制限: J-Quants はレート制限（120 req/min）があります。jquants_client はこれを尊重する実装です。
- セキュリティ:
  - news_collector は SS RF 対策、XML パースに defusedxml、レスポンスサイズ制限を実施しています。
  - .env 読み込みはプロジェクトルート（.git または pyproject.toml を検知）を基準に行われます。テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベルや環境（development/paper_trading/live）は環境変数で制御します（KABUSYS_ENV, LOG_LEVEL）。
- DuckDB ファイルのバックアップや同時アクセスに注意してください（運用上のロック・リカバリ戦略を検討してください）。

---

もし README に追加したい具体的な例（cron/airflow ジョブ設定例、Slack 通知の使い方、CI 設定など）があれば教えてください。必要に応じて章を追加して詳述します。