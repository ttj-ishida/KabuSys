# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants や kabuステーション等の外部 API からデータを取得し、DuckDB に整備されたスキーマで保存、ETL・品質チェック・ニュース収集・監査ログ をサポートします。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS を元にニュースを収集して記事と銘柄紐付けを行うニュースコレクタ
- 市場カレンダー管理（営業日判定、前後営業日の取得など）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 将来的な戦略／実行／モニタリングモジュールの基盤

設計上の特徴：
- J-Quants API のレート制限（120 req/min）、リトライ、トークン自動リフレッシュ対応
- DuckDB を用いた冪等的保存（ON CONFLICT / RETURNING を活用）
- ニュース収集時の SSRF / XML-Bomb / Gzip-Bomb 対策
- ETL は差分更新＋バックフィル（後出し修正への耐性）
- 品質チェックは Fail-Fast ではなく全件検出を行い呼び出し元で判断

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レート制御、リトライ、401 時の自動トークン更新、ページネーション対応
  - DuckDB へ保存する save_* 関数（冪等）
- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェックの流れを実行
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector
  - RSS 取得・前処理・記事 ID（正規化URLの SHA-256 切り取り）生成
  - raw_news / news_symbols への保存（チャンク・トランザクション管理）
  - SSRF / プライベートアドレス検査、受信サイズ制限などの安全対策
- data.schema / data.audit
  - DuckDB スキーマ初期化（raw / processed / feature / execution / audit）
  - 監査用スキーマとインデックスの作成（init_schema / init_audit_db）
- data.calendar_management
  - 営業日判定、next/prev_trading_day、期間内の営業日取得、calendar_update_job
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す）

---

## セットアップ手順

前提
- Python 3.10 以上（型の | 記法や typing の機能を使用）
- Git 等によりプロジェクトルートが存在すること（.env 自動読み込みのため）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布パッケージがある場合）pip install -e .

必要な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャネル ID（必須）

任意/デフォルト
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に `1` をセット

.env 自動読み込み
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml のある場所）を基に .env と .env.local を自動読み込みします。
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。Python スクリプトや CLI から呼び出してパイプライン実行やデータ収集を行います。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはメモリDB
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources をカスタマイズ可能（省略時 DEFAULT_RSS_SOURCES を使用）
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存件数, ...}
```

4) J-Quants API 直接呼び出し（テストやカスタム取得時）
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
jq.save_daily_quotes(conn, records)
```

5) 監査ログ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 既存 main conn に対しては init_audit_schema(conn) でも追加可能
```

ログレベルや環境は環境変数で制御します（KABUSYS_ENV, LOG_LEVEL）。

---

## 主要 API の説明（概要）

- kabusys.config.settings
  - 環境変数を読む Settings オブジェクト。必須値未設定時は例外を投げます。
  - 自動 .env ロードは有効（無効化可能）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl: 一括実行、品質チェック付き

- kabusys.data.news_collector
  - fetch_rss: RSS をフェッチして記事リストを返す
  - save_raw_news: raw_news テーブルに記事を保存し、新規挿入 ID を返す
  - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付け保存
  - run_news_collection: 複数ソースを巡回して DB に保存、銘柄紐付けまで実行

- kabusys.data.schema
  - init_schema(db_path): 全スキーマを作成（冪等）
  - get_connection(db_path): 既存 DB へ接続

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job: 夜間バッチでカレンダーを更新

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue 型で問題の詳細を返す

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定 / .env ローダー
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + DuckDB 保存
    - news_collector.py           — RSS ニュース収集と保存
    - pipeline.py                 — 日次 ETL パイプライン
    - schema.py                   — DuckDB スキーマ定義・初期化
    - calendar_management.py      — 市場カレンダー管理
    - audit.py                    — 監査ログスキーマ（signal/order/execution）
    - quality.py                  — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略関連プレースホルダ
  - execution/
    - __init__.py                  — 実行（発注）関連プレースホルダ
  - monitoring/
    - __init__.py                  — 監視・メトリクスプレースホルダ

---

## 運用上の注意 / ベストプラクティス

- API レート制限を厳守してください（jquants_client は内部で制御しますが、並列呼び出しに注意）。
- 機密情報（トークン等）は .env に保存せず、Git 管理下に置かないでください。
- ETL は品質チェックでエラーを検出しても処理を継続する設計です。結果（ETLResult）を確認して適切な運用判断を行ってください。
- news_collector は外部 URL を取り扱うため SSRF 対策や受信サイズ制限を導入しています。テスト時は _urlopen をモックして外部呼び出しを制御してください。
- DuckDB ファイルは定期バックアップを推奨します。監査ログは削除しない前提で設計されています。

---

## 付記

- 本 README は現時点のコードベース（src/kabusys/*.py）に基づいて作成しています。追加の CLI、CI、テスト、インストール要件ファイル（pyproject.toml / requirements.txt）がある場合はそれに従ってください。
- 実運用での注文・資金管理ロジックは非常に重要です。本ライブラリは基盤を提供しますが、実際の売買ロジック・リスク管理は利用者側で厳密に実装・検証してください。