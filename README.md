# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants、RSS）、DuckDBベースのスキーマ定義、ETLパイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤モジュール群です。主に次を実現します。

- J-Quants API を利用した株価（OHLCV）、財務データ、マーケットカレンダーの取得と DuckDB への冪等保存
- RSS フィードからのニュース収集および銘柄紐付け（SSRF 対策、gzip サイズ制限、XML セキュリティ）
- DuckDB 上のデータレイヤ（Raw / Processed / Feature / Execution）スキーマ定義と初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 市場カレンダー管理（営業日の判定、next/prev_trading_day など）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）スキーマ

設計上、API レート制限やリトライ、トークン自動リフレッシュ、Look-ahead バイアス回避（fetched_at の記録）、冪等性（ON CONFLICT）に配慮しています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、id_token 自動更新）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar

- data/news_collector.py
  - RSS フィード取得（gzip 対応、SSRF 防止、XML 脆弱性対策）
  - 記事正規化・ID 生成（URL 正規化 → SHA-256）
  - raw_news への冪等保存（INSERT ... RETURNING を利用）
  - 銘柄コード抽出・news_symbols 保存

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）と初期化関数 init_schema/get_connection

- data/pipeline.py
  - ETL の差分更新ロジック（市場カレンダー先読み、バックフィル、品質チェック）
  - run_daily_etl を起点に価格・財務・カレンダー ETL を実行

- data/calendar_management.py
  - market_calendar 管理、is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）

- data/quality.py
  - 欠損チェック・スパイク検出・重複・日付整合性チェック
  - run_all_checks による一括実行

- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化関数

- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパー settings
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順

必須: Python 3.9+（typing の一部機能のため）を想定しています。以下は最小セットアップ例です。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   必須依存（最低限）:
   ```
   pip install duckdb defusedxml
   ```
   追加でロギング/Slack連携等を行いたい場合は別途パッケージを追加してください（例: slack-sdk 等）。

   ※ プロジェクトに requirements.txt があればそれを使用してください:
   ```
   pip install -r requirements.txt
   ```

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` と `.env.local` を置くと自動的に読み込まれます（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（任意, デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)
   - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---

## 使い方

以下は代表的な利用例です。Python スクリプト／REPL からモジュールをインポートして利用します。

- スキーマ初期化（DuckDB）
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

- 監査ログスキーマの初期化
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続
audit.init_audit_schema(conn)
```

- 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数, ...}
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2024, 1, 1))
for i in issues:
    print(i)
```

- 環境設定取得（コード内での利用）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 自動環境読み込みの挙動

- config.py はプロジェクトルート（.git または pyproject.toml の祖先）を探索し、見つかれば `.env` → `.env.local` を順に読み込みます。
- OS 環境変数が優先され、.env の値は既存の環境変数を上書きしません（ただし .env.local は上書き可能）。
- 自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用など）。

---

## ディレクトリ構成

リポジトリの主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース収集・前処理・DB保存
    - schema.py               -- DuckDB スキーマ定義・初期化
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  -- マーケットカレンダー管理
    - audit.py                -- 監査ログスキーマ（signal / order / execution）
    - quality.py              -- データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記以外にプロジェクトルートに .env.example, pyproject.toml, README.md などがある想定です）

---

## 開発・運用上の注意

- API レート制限に注意:
  - J-Quants の default は 120 req/min。jquants_client は固定間隔でスロットリングを実装しています。
- 認証トークン:
  - get_id_token はリフレッシュトークンから id_token を取得します。401 発生時は自動リフレッシュしてリトライします。
- DuckDB スキーマ:
  - init_schema は冪等でテーブルを作成します。既存データを破壊しません。
- ニュース収集セキュリティ:
  - RSS のリダイレクト先や最終ホストがプライベートアドレスの場合はブロックします（SSRF 対策）。
  - XML パーサーには defusedxml を使用して脆弱性に対処しています。
  - レスポンスは最大 10 MB に制限（Gzip解凍後も同様）。
- 品質チェック:
  - run_all_checks はエラー/警告を収集して返します。呼び出し元で重大度に応じた処理を行ってください。
- `.env` のパースはシェル風の表記（export KEY=val、クォート、コメント）に対応していますが、複雑なケースは検証してください。

---

## トラブルシューティング（よくある問題）

- DuckDB が見つからない / import エラー:
  - 依存パッケージがインストールされているか確認してください（pip install duckdb）。
- J-Quants 認証エラー（401）:
  - settings.jquants_refresh_token が正しくセットされているか確認。トークンが有効であればクライアントは自動でリフレッシュを試みますが、refresh_token 自体が無効な場合は手動更新が必要です。
- RSS フェッチで urllib.error.URLError:
  - ターゲット URL の到達性、TLS 設定、プロキシ環境を確認してください。SSRF/プライベートアドレスチェックに引っかかっている場合はログを確認してください。
- 自動 .env 読み込みを無効化したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば、README にサンプル .env.example のテンプレートや、CI / cron ベースのバッチ実行例（systemd / cron / GitHub Actions）を追加できます。追加してほしい項目があれば教えてください。