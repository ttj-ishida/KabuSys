# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や各種 RSS を利用したデータ収集、DuckDB を使ったスキーマ管理、ETL パイプライン、監査ログ (audit) 等の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群を含むプロジェクトです。

- J-Quants API からの市場データ（株価日足・財務データ・JPX カレンダー）取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB を利用したスキーマ定義と永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

設計上のポイント:
- API レート制限対応（J-Quants: 120 req/min）
- リトライ、トークン自動リフレッシュ、冪等保存（ON CONFLICT）を重視
- ニュース収集でのセキュリティ（SSRF 防止、XML 脆弱性対策、受信サイズ制限）
- 品質チェック（欠損、スパイク、重複、日付不整合検出）

---

## 機能一覧

主なモジュール / 機能

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）
  - 環境変数の取得ラッパー（必須チェック・デフォルト値）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数
  - RateLimiter、リトライ、トークン再取得ロジック
- kabusys.data.news_collector
  - RSS フェッチ（defusedxml、gzip 対応、SSRF リダイレクト検査）
  - URL 正規化・追跡パラメータ除去、記事 ID 生成（SHA-256）
  - raw_news, news_symbols への冪等保存
  - 銘柄コード抽出（4桁）
- kabusys.data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) で初期化可能
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分取得、backfill、品質チェックの統合
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチでカレンダー更新）
- kabusys.data.audit
  - 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality
  - 各種品質チェック（欠損、重複、スパイク、日付不整合）
- その他: strategy, execution, monitoring 用のパッケージプレースホルダ

---

## セットアップ手順

1. Python 環境の用意（推奨: 3.9+）
   - 仮想環境作成例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - 必須ライブラリ:
     - duckdb
     - defusedxml
   - pip でインストール:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

オプション / デフォルト
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）

.env の行パース仕様:
- コメント行、先頭に `export ` がある行、シングル/ダブルクォートで囲まれた値、インラインコメントの取り扱いに対応

---

## 使い方

基本的な利用例（Python スクリプト内で呼び出す想定）

1) DuckDB スキーマ初期化
```py
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはメモリ DB
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL を実行する
```py
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 市場カレンダーの夜間更新ジョブ（例: cron で実行）
```py
from kabusys.data import calendar_management
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved", saved)
```

4) ニュース収集ジョブ
```py
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# DEFAULT_RSS_SOURCES を使う場合
results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: new_count}
```

5) 監査ログ用スキーマ初期化
```py
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
# もしくは専用 DB を作成
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- jquants_client は内部でレートリミットとリトライを行います。長時間の一括取得では API 制限に注意してください。
- get_id_token はリフレッシュトークンを用いて ID トークンを取得します（settings.jquants_refresh_token を使用）。
- news_collector は SSRF 対策（リダイレクト検査、プライベートIP拒否）、受信サイズ制限、XML の安全パーサを備えています。

---

## 主要 API（抜粋）

- schema.init_schema(db_path) -> DuckDB 接続（初回テーブル作成）
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
- data.jquants_client.save_daily_quotes(conn, records), save_financial_statements(...)
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
- data.news_collector.fetch_rss(url, source, timeout=30)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.calendar_management.is_trading_day(conn, date), next_trading_day(...), prev_trading_day(...)
- data.audit.init_audit_schema(conn, transactional=False), init_audit_db(db_path)
- data.quality.run_all_checks(conn, target_date=None, reference_date=None)

各関数は docstring に使用方法・引数・戻り値の説明があります。コード内のコメントや設計ノートも参照してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - news_collector.py      — RSS ニュース収集・前処理・保存
    - pipeline.py            — ETL パイプライン（差分更新・統合）
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - calendar_management.py — 営業日ロジック / calendar_update_job
    - audit.py               — 監査ログスキーマ / init_audit_db
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連のプレースホルダ
  - execution/
    - __init__.py            — 発注 / ブローカー連携のプレースホルダ
  - monitoring/
    - __init__.py            — 監視用プレースホルダ

- pyproject.toml (想定)
- .git/ (想定)

---

## 運用上の注意 / ベストプラクティス

- 環境変数は秘匿情報を含むため `.env` をバージョン管理しないでください。`.env.example` を作って配布するのが望ましいです。
- 本番（live）環境では KABUSYS_ENV を `live` に設定し、テスト用の `paper_trading` を分けて運用してください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログは削除しない運用を想定しています。
- J-Quants の API 呼び出しはレート制限・リトライロジックを備えていますが、過度な同時実行は避けてください。
- news_collector は外部 URL を取得するため、実行する環境のネットワークポリシー（プロキシ、アウトバウンド制限等）を確認してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効にできます。

---

## ライセンス / 貢献

（ここにライセンスや貢献方法を記載してください）

---

README のサンプルコードや設定値について不明点があれば、使用したいユースケース（例: 日次 ETL を cron で実行したい、監査 DB を分離したい、ニュースの RSS ソースを追加したい等）を教えてください。具体的な例やスクリプトを提供します。