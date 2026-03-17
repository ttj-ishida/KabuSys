# KabuSys

日本株自動売買プラットフォーム用ライブラリ（KabuSys）。  
市場データ取得、ETL、ニュース収集、データ品質チェック、DuckDB スキーマ定義、監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤コンポーネント群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足・財務データ・JPX カレンダー）
- RSS を用いたニュース収集と DuckDB への冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）
- カレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（信号→発注→約定のトレーサビリティ）
- セキュリティ・運用考慮（API レート制御、トークン自動リフレッシュ、SSRF 対策、XML デフューズ）

設計上の特徴:
- レートリミット・リトライ（指数バックオフ）
- 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT を利用）
- ニュース収集には URL 正規化・トラッキング除去・SSRF・gzip/サイズ制限を実装
- 品質チェックは Fail-Fast ではなく全件収集し呼び出し元で判断可能

---

## 機能一覧

- 環境設定読み込み（.env / .env.local、自動ロード、保護キー）
- J-Quants クライアント
  - get_id_token（トークン自動更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB に冪等保存
- ニュース収集（RSS）
  - fetch_rss（XML デフューズ、gzip 対応、SSRF 防止、最大バイト数制限）
  - save_raw_news / save_news_symbols（チャンク・トランザクションで保存）
  - 銘柄抽出（4桁コード抽出、既知銘柄フィルタ）
- DuckDB スキーマ定義と初期化（data.schema）
  - Raw / Processed / Feature / Execution / Audit テーブルとインデックス
  - init_schema / get_connection / init_audit_db
- ETL パイプライン（data.pipeline）
  - run_daily_etl（市場カレンダー→株価→財務→品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェック統合
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチで J-Quants から差分更新）
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブル、インデックス、初期化関数
- データ品質チェック（data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue 型で詳細を返す

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（コードは typing union 表記などを使用）
- DuckDB を利用（Python パッケージ duckdb）
- インターネット接続（J-Quants API, RSS）

1. リポジトリをチェックアウト
   - 例: git clone <リポジトリ>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - 必須パッケージの例:
     - duckdb
     - defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってインストール）
   - 例:
     - pip install duckdb defusedxml

4. 環境変数の設定
   - ルート（.git または pyproject.toml があるディレクトリ）に `.env` として以下を設定してください（.env.example を参考に）。
   - 必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
   - 任意:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化できます（テスト用途）

   - config.Settings が環境変数を参照します。自動ロードは .env → .env.local の順で行われ、OS 環境変数を保護します。

5. DB スキーマの初期化
   - Python REPL やスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema(settings.duckdb_path)  # もしくは schema.init_schema("data/kabusys.duckdb")
     - # 監査ログを別 DB にしたい場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡易ガイド）

以下は代表的な操作例です。Python スクリプトや CLI から呼び出して使います。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブを実行して保存・銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 事前に用意した有効銘柄リスト
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

4) カレンダー更新バッチ（夜間実行想定）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

5) 品質チェック（任意の日付で実行）
```python
from kabusys.data.quality import run_all_checks
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

注意点:
- ETL の id_token は自動的にキャッシュ・リフレッシュされますが、テスト目的で外部から id_token を渡せます。
- ニュース収集では HTTP/HTTPS 以外のスキームやプライベートアドレスへはアクセスしないよう保護しています。
- J-Quants API はレート制限 (120 req/min) を守るよう内部でスロットリングしています。

---

## ディレクトリ構成

（プロジェクトルートの src/ 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集、前処理、DB保存、銘柄抽出
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py            — ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py — カレンダー管理（営業日判定、カレンダー更新ジョブ）
    - audit.py               — 監査ログ（signal/order/execution）スキーマ & 初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注/約定管理（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視関連（拡張ポイント）

README に記載のない補助ファイル:
- .env / .env.local （自動ロード対象）
- pyproject.toml / setup.cfg（パッケージ化用、存在する場合）

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

自動読み込み無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 運用・セキュリティに関するメモ

- J-Quants へのリクエストは _RateLimiter によって単位時間当たりのリクエスト数を制御します（デフォルト 120 req/min）。自身の運用環境に応じて調整してください。
- HTTP 429 / 5xx / ネットワークエラー時は指数バックオフでリトライします。401 発生時は自動で一度トークンリフレッシュを試みます。
- RSS 処理では defusedxml を利用して XML Bomb 等を防ぎます。受信データサイズは上限を設け、gzip 展開後もサイズ検査を行います。
- ニュース収集時の URL は正規化（トラッキングパラメータ除去）して SHA-256 の先頭 32 文字を記事IDとして冪等性を担保します。
- カレンダー・ETL 処理は DB の状態に依存して動作するため、スキーマ初期化（init_schema）を事前に行ってください。
- 監査ログ（audit）では全て UTC でタイムスタンプを扱います。

---

## 追加・拡張ポイント

- strategy / execution / monitoring パッケージは拡張ポイントです。独自戦略・仮想発注モジュール・監視ダッシュボードを実装してください。
- DuckDB をそのまま利用する設計ですが、必要に応じて永続ストレージやバックアップ戦略を検討してください。
- CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、意図的に環境を注入してテストすることを推奨します。

---

お問い合わせ・貢献

- バグ報告や機能要望は issue を投げてください。
- コード規約・テスト追加については PR を歓迎します。README 記載の通り、テスト用に env ロード制御・id_token 注入が可能です。

以上。