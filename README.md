# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
J-Quants API や RSS フィード等からデータを取得して DuckDB に保存し、ETL・品質チェック・監査ログ・ニュース収集などを行うためのモジュールを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python ライブラリです。

- J-Quants から株価（日足）・財務データ・マーケットカレンダーを安全に取得するクライアント
- DuckDB ベースのスキーマ定義と初期化機能（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS フィードからのニュース収集・前処理・銘柄抽出（SSRF や XML 攻撃対策を含む）
- 監査ログ（signal → order → execution のトレーサビリティ）スキーマ初期化

設計上の特徴：
- API レートリミット遵守（J-Quants: 120 req/min）
- 冪等性（ON CONFLICT / INSERT … RETURNING 等で重複を排除）
- リトライ、指数バックオフ、トークン自動リフレッシュ（401 時）
- セキュリティ対策（ニュース収集での SSRF / XML 攻撃対策等）
- 品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- 環境変数管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可）
  - 必須項目の取得・バリデーション（`kabusys.config.settings`）

- J-Quants クライアント (`kabusys.data.jquants_client`)
  - トークン取得（`get_id_token`）
  - 日足取得（`fetch_daily_quotes`）
  - 財務データ取得（`fetch_financial_statements`）
  - マーケットカレンダー取得（`fetch_market_calendar`）
  - DuckDB への保存（`save_daily_quotes` / `save_financial_statements` / `save_market_calendar`）
  - レート制御・リトライ・ログ一貫設計

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード取得（gzip 対応、受信サイズ制限）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256 の先頭32文字）
  - XML パースに `defusedxml` を使用（XML Bomb 等の防止）
  - SSRF 対策（スキーム検査・リダイレクト先のプライベートアドレス検査）
  - DuckDB への冪等保存（`save_raw_news` / `save_news_symbols`）

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層の DDL を定義・初期化（`init_schema`）
  - 監査ログ用 DB 初期化（`init_audit_db` / `init_audit_schema`）

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分取得ロジック（最終取得日からの再取得・backfill）
  - 日次 ETL エントリ（`run_daily_etl`）
  - 個別ジョブ（`run_prices_etl`, `run_financials_etl`, `run_calendar_etl`）
  - 品質チェック統合（`kabusys.data.quality` と連携）

- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - 営業日の判定、前後営業日の取得、範囲内営業日リスト生成
  - 夜間カレンダー更新ジョブ（`calendar_update_job`）

- 品質チェック (`kabusys.data.quality`)
  - 欠損データ、重複、スパイク（前日比閾値）、日付不整合の検出
  - 各チェックは `QualityIssue` を返す（severity: error / warning）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈の | 演算子 等を使用）
- OS 依存の追加ライブラリはほぼ不要（DuckDB の wheel で事足ります）

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   最低限必要なパッケージ:
   - duckdb
   - defusedxml

   例:

   ```
   pip install duckdb defusedxml
   ```

   （パッケージ管理のため requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数設定

   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` および任意で `.env.local` を作成すると自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。

   必須環境変数（少なくとも以下は設定してください）:

   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN        — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID       — 通知先の Slack チャネル ID

   省略可能（デフォルト値あり）:
   - KABU_API_BASE_URL      — kabu API のベース URL （デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH            — DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH            — SQLite 監視 DB（デフォルト data/monitoring.db）
   - KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なコード例）

以下はライブラリを使った基本的なワークフロー例です。

- DuckDB スキーマ初期化（1回だけ実行）

```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

- 日次 ETL の実行（J-Quants トークンは settings から自動取得されます）

```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")

# 既知の銘柄コードセットを用意（抽出に使用）
known_codes = {"7203", "6758", "9984", "9432"}

results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- 監査ログスキーマを追加で初期化（監査DBを別ファイルにする場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
```

- J-Quants の低レベル API 呼び出し例

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from datetime import date

id_token = get_id_token()  # settings.jquants_refresh_token を利用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 主要 API / モジュールの説明（抜粋）

- kabusys.config
  - settings — 必須/任意の環境変数をプロパティとして取得
  - 自動で .env/.env.local をプロジェクトルートから読み込む（無効化可）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - extract_stock_codes(text, known_codes)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

- kabusys.data.calendar_management
  - is_trading_day(conn, date)
  - next_trading_day(conn, date)
  - prev_trading_day(conn, date)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成

リポジトリ内の主要ファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (空のパッケージプレースホルダ)
  - strategy/ (空のパッケージプレースホルダ)
  - monitoring/ (空のパッケージプレースホルダ)
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - calendar_management.py
    - schema.py
    - audit.py
    - quality.py

ドキュメント・設計資料の参照先（コード内コメントで言及）:
- DataPlatform.md（スキーマ・ETL 設計の根拠）
- その他 README 等（プロジェクトルートにある場合）

---

## 運用上の注意事項

- 環境変数管理：
  - プロジェクトルート（.git または pyproject.toml）から .env を自動読み込みします。CI/テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API：
  - レート制限（120 req/min）を守るため内部でスロットリングしています。
  - 401 受信時はリフレッシュトークンで自動再取得を試みます（1回のみ）。
  - 408/429/5xx 等はリトライ（指数バックオフ）対象です。

- ニュース収集：
  - RSS の受信サイズは上限（10MB）で制限しています。
  - URL の正規化・トラッキング除去を行い、記事IDは SHA-256（先頭32文字）で生成して冪等性を担保します。
  - リダイレクト先のプライベートアドレスを検査し、SSRF を防止します。

- DuckDB スキーマ：
  - DDL は冪等的に作成されるため、何度でも init_schema を呼べます。
  - audit 用の初期化は `init_audit_db`（トランザクションあり）を推奨します。

---

## 拡張・開発ヒント

- strategy や execution パッケージは拡張ポイントです。戦略生成 → signals テーブル → signal_queue → order 作成 → audit ログ の流れで発注フローを実装してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、ダミー環境変数を明示的に設定して下さい。
- news_collector の _urlopen はテスト時に差し替え（モック）しやすいように設計されています。

---

## 最後に

この README はコードベース（src/kabusys）を基に作成しています。詳しい設計意図や追加のドキュメント（DataPlatform.md 等）がリポジトリ内にあればそちらも参照してください。質問や追加の README に含めたい例・運用手順があれば教えてください。