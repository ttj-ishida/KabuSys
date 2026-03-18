# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ収集（J‑Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主に内部で DuckDB をデータ層に使い、J‑Quants API や各種 RSS フィード等からのデータ取得を idempotent（冪等）に保存することを目的としたモジュール群です。

## 特徴（概要）
- J‑Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - API レート制御（120 req/min）とリトライ（指数バックオフ）
  - 401 の場合はリフレッシュトークンから自動トークン更新
  - データ取得時刻（fetched_at）を UTC で付与して Look‑ahead Bias を防止
  - DuckDB へは ON CONFLICT を使い冪等保存
- ETL パイプライン
  - 差分更新（最終取得日を基準に自動判定）＋バックフィルオプション
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）
  - URL 正規化（utm 等のトラッキングパラメータ除去）→ SHA‑256 ハッシュで冪等キー生成
  - defusedxml を用いた安全な XML パース、SSRF 対策、受信サイズ制限
  - 銘柄コード抽出（4桁の既知コードのみ）
- マーケットカレンダー管理
  - market_calendar を使った営業日判定、前後営業日の検索、夜間バッチ更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → execution の階層を UUID で追跡する監査テーブル群
  - 発注の冪等キー（order_request_id）対応
- DuckDB スキーマの初期化・管理ユーティリティ

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数チェック（Settings クラス）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB 保存）
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（全体 ETL）
  - 差分取得・バックフィル機能・品質チェック連携
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - URL 正規化、記事ID 生成、SSRF 対策、gzip 対応、受信サイズ制限
- kabusys.data.schema
  - init_schema(db_path) : DuckDB にスキーマ（Raw / Processed / Feature / Execution）を作成
  - get_connection(db_path)
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
  - QualityIssue 型による検出結果の集約
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path) : 監査用テーブルの初期化

---

## 必要条件
- Python 3.10 以上（PEP 604 の型記法や型ヒントに依存）
- 主な依存パッケージ（抜粋）
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib 等を使用）
- ネットワークアクセス（J‑Quants API、RSS フィード）

依存関係はプロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください。

---

## セットアップ手順（開発環境向け）
1. Python の準備
   - Python 3.10+ をインストールしてください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements ファイルがあれば pip install -r requirements.txt）

   開発モードでインストールする場合:
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を置くディレクトリ）に .env を作成すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主に必要な環境変数（Settings が必須とするもの）
   - JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

   オプション（デフォルト値あり）
   - KABUSYS_ENV : development | paper_trading | live （デフォルト development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : SQLite 監視 DB（デフォルト data/monitoring.db）

   .env の例（.env.example を参考にしてください）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベーススキーマ初期化
   - DuckDB スキーマを初期化して接続を取得します（初回のみで可）:

   Python 例:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成され、全テーブルが作られる
   ```

6. 監査ログ専用 DB の初期化（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 基本的な使い方（例）
以下は代表的なユースケースの例です。実運用ではエラー処理やログ設定を行ってください。

1. 日次 ETL を実行する（カレンダー・株価・財務・品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

2. J‑Quants から株価を取得して保存する（個別呼び出し）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

conn = init_schema(settings.duckdb_path)
# トークンは設定から自動取得される
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

3. RSS ニュース収集ジョブを実行する
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は text から抽出する有効な銘柄コードセット（例えば prices テーブルから取得）
known_codes = {"7203", "6758", "6501"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4. カレンダーの夜間更新ジョブを実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar records: {saved}")
```

5. 品質チェックを手動で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 補足（仕組み・設計上の注意）
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env を読み込みます。
  - 読み込み順は OS 環境変数 > .env.local > .env。デフォルトでは既存の OS 環境変数が保護されます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env パーサは export プレフィックスやクォート、インラインコメント等に対応しています。

- J‑Quants クライアントの振る舞い
  - レート制御は固定間隔（120 req/min）でスロットリングします。
  - リトライは指数バックオフ（最大 3 回）。408/429/5xx は再試行対象。
  - 401 が返るとリフレッシュトークンで id_token を再取得して 1 回リトライします。
  - ページネーション対応：pagination_key を追跡してページを巡回します。

- ニュース収集の安全対策
  - defusedxml を使った XML パースで XML Bomb 等への防御
  - リダイレクト先のスキーム検証とプライベート IP 検査（SSRF 対策）
  - レスポンスサイズ上限（デフォルト 10 MB）＋ gzip 解凍後の再検証

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution / Audit の多層設計
  - DDL は冪等（CREATE TABLE IF NOT EXISTS）かつ主キー・チェック制約が豊富
  - audit テーブルはタイムゾーンを UTC に固定して初期化します

---

## ディレクトリ構成
以下は主要ファイルの構成（抜粋）です。

```
src/
└── kabusys/
    ├── __init__.py
    ├── config.py
    ├── data/
    │   ├── __init__.py
    │   ├── jquants_client.py
    │   ├── news_collector.py
    │   ├── pipeline.py
    │   ├── calendar_management.py
    │   ├── schema.py
    │   ├── quality.py
    │   ├── audit.py
    │   └── pipeline.py
    ├── strategy/
    │   └── __init__.py
    ├── execution/
    │   └── __init__.py
    └── monitoring/
        └── __init__.py
```

（実際のリポジトリには pyproject.toml / setup.cfg / requirements.txt / .env.example 等が存在する想定です）

---

## 推奨運用上の注意
- 本ライブラリは実際の発注ロジック（ブローカー接続・注文送信など）を抽象化しており、実運用でのライブ発注時は徹底したテストとリスク管理が必要です（特に order_request の冪等管理や監査ログの運用）。
- J‑Quants の API 使用上限や kabuステーションの仕様に十分注意してください。
- 機密情報（トークン・パスワード）は .env やシークレットマネージャで安全に管理し、ソース管理にコミットしないでください。

---

## 追加情報・問い合わせ
- 実装や仕様に沿った拡張（戦略モジュールの追加、モニタリング機能の実装など）は strategy/、execution/、monitoring/ に実装を追加してください。
- README の補足やサンプルスクリプトが必要であれば、必要なユースケースを教えてください。