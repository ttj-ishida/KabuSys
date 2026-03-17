# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、マーケットカレンダー、監査ログスキーマなど、取引システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要な目的を持ったモジュール群を提供します。

- J-Quants API から株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを安全に取得するクライアント（レート制御・リトライ・トークン自動更新・fetched_at 記録）。
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）。
- ETL パイプライン（差分取得、バックフィル、品質チェック）。
- RSS ベースのニュース収集と銘柄コード紐付け（SSRF 対策、XML 安全パーサ、トラッキングパラメータ除去、冪等保存）。
- マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間バッチ更新）。
- 監査ログ（シグナル→注文→約定のトレース、冪等キー、UTC タイムスタンプ）。

設計上の特徴:
- 冪等性を重視（DuckDB 側は ON CONFLICT を活用）。
- ネットワーク・セキュリティ対策（SSRF、XML Bomb、レスポンスサイズ制限）。
- テストしやすい設計（id_token 注入やモック可能な内部関数を想定）。

---

## 機能一覧

- 環境変数/設定管理（自動で .env / .env.local をロード可能）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - リトライ、レート制限、401 時のトークンリフレッシュ
  - DuckDB への保存関数（save_* 系）
- DuckDB スキーマ管理
  - init_schema / get_connection
  - テーブル群（raw_prices / raw_financials / raw_news / prices_daily / features / signals / orders / trades / positions / など）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新、バックフィル、品質チェックとの統合
- ニュース収集
  - fetch_rss / fetch_rss -> save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化、記事ID（SHA-256 トリム）、銘柄抽出（4桁コード）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチで差分更新）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db
  - signal_events / order_requests / executions テーブル群
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（コードは型ヒントに union 型などを使用）
- DuckDB と defusedxml を依存に含みます

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - minimal:
     ```bash
     pip install duckdb defusedxml
     ```
   - 実際のプロジェクトでは追加で HTTP クライアントや Slack ライブラリ等が必要になる可能性があります。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - 任意:
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - `.env` の例（.env.example を参考に作成してください）:
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

## 使い方（コード例）

以下は代表的なユースケースの Python スニペットです。プロジェクト内に CLI は実装されていませんが、スクリプトやスケジューラからこれらの関数を呼び出して利用します。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはメモリ DB
# conn = schema.init_schema(":memory:")
```

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token, run_quality_checks など調整可能
print(result.to_dict())
```

- ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は抽出で有効とみなす銘柄コードの集合（例: 全上場銘柄リスト）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: 新規保存件数, ...}
```

- マーケットカレンダー夜間更新（バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants から直接データ取得して保存（テスト用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# トークンは settings から自動取得されるが、明示的に注入することも可
id_token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from="20230101", date_to="20231231")
jq.save_daily_quotes(conn, records)
```

- 監査ログ（audit）初期化
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

注意点:
- run_daily_etl 等は内部で例外を捕捉して継続する設計です。戻り値（ETLResult）でエラーや品質問題を確認してください。
- J-Quants クライアントは 120 req/min のレート制限、最大 3 回のリトライ、401 時の自動トークンリフレッシュを実装しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込み
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（差分更新・統合ジョブ）
    - schema.py              — DuckDB スキーマ定義・初期化
    - calendar_management.py — マーケットカレンダー管理・ジョブ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal/order/execution）スキーマ
  - strategy/
    - __init__.py            — 戦略レイヤ（拡張場所）
  - execution/
    - __init__.py            — 発注・約定・ブローカー連携（拡張場所）
  - monitoring/
    - __init__.py            — 監視・アラート（拡張場所）

ファイル別の主な責務はソースコメント（各モジュール冒頭）に詳述されています。

---

## 開発・デバッグのヒント

- 自動 .env ロードを無効化する:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テストや isolated 環境で有用です。

- DuckDB をメモリで利用する場合は db_path に `":memory:"` を使えます（テストで便利）。

- news_collector のネットワーク呼び出しは内部で `_urlopen` を使っているため、テストではこの関数をモックして外部呼び出しを遮断できます。

- J-Quants の ID トークンはモジュールレベルでキャッシュされます（ページネーション間で共有）。再取得したい場合は `get_id_token(refresh_token)` を呼ぶか、内部キャッシュを強制更新する方法を使用してください（jquants_client の _get_cached_token を参照）。

- 監査テーブルは UTC でのタイムスタンプ保存を前提としています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## ライセンス・貢献

（ここにライセンス情報や貢献手順を記載してください）

---

README は開発初期段階向けの概要ドキュメントです。各モジュールの詳細な使い方や API 仕様、実運用設定（ブローカー接続、Slack 通知、ジョブスケジューラ設定など）は別途ドキュメント（DataPlatform.md 等）を参照してください。