# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。J-Quants や RSS を用いたデータ収集、DuckDB ベースのデータスキーマ、ETL パイプライン、品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、自動売買システムに必要なデータ基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX 市場カレンダーを取得
  - レート制限（120 req/min）を考慮した RateLimiter 実装
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（UTC）を記録し Look-ahead Bias を防止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS から記事を取得し前処理 → raw_news に冪等保存
  - URL 正規化（utm 等トラッキング除去）、記事 ID は URL の SHA-256（先頭32文字）
  - SSRF/zip bomb 対策（スキーム検証、最大受信バイト数、defusedxml）
  - 銘柄コード抽出と news_symbols への紐付け

- ETL パイプライン
  - 差分更新（DB の最終取得日に基づく差分フェッチ）とバックフィル対応
  - 市場カレンダー先読み、品質チェックの実行（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括実行

- DuckDB ベースのスキーマ
  - Raw / Processed / Feature / Execution 層を備えた DDL を提供
  - インデックス定義・監査テーブルも含む初期化 API

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ
  - 夜間バッチでの差分更新ジョブ

- 監査ログ（Audit）
  - signal → order_request → execution を UUID 連鎖でトレース可能にするテーブル群
  - 発注の冪等性（order_request_id）やステータス管理をサポート

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を SQL ベースで検出
  - QualityIssue オブジェクトで問題を集約（severity: error/warning）

---

## 必要条件

- Python 3.10 以上（型付けに PEP 604 の `|` を使用）
- 主な依存パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクト全体の追加依存は用途に応じて必要になります。たとえば Slack 通知等を行う場合は slack-sdk 等を追加してください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## セットアップ手順（開発向け・ローカル）

1. リポジトリをクローンし、仮想環境を用意する
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. 環境変数を設定する
   - .env をプロジェクトルートに置くと自動で読み込まれます（ただしテスト時や他用途で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack Bot トークン（通知を使う場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを無効化
     - KABUSYS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite モニタリング DB（デフォルト: data/monitoring.db）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトからスキーマを初期化します。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査ログを別 DB に作る場合:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な API の例）

- 設定値の取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 環境変数から値を取得（未設定なら例外）
```

- J-Quants から株価取得（fetch）と保存（save）
```python
import duckdb
from kabusys.data import jquants_client as jq

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- RSS ニュース収集と保存
```python
from kabusys.data import news_collector as nc
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = nc.save_raw_news(conn, articles)
print(f"new articles: {len(new_ids)}")
```

- ETL 日次実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- カレンダー操作例
```python
from kabusys.data import calendar_management as cm
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
today = date.today()
print(cm.is_trading_day(conn, today))
print(cm.next_trading_day(conn, today))
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) - kabu API パスワード
- KABU_API_BASE_URL - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) - Slack Bot トークン
- SLACK_CHANNEL_ID (必須 for Slack) - Slack チャンネル ID
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - development | paper_trading | live（デフォルト: development）
- LOG_LEVEL - ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 1 を設定すると自動で .env をロードしない

環境変数は .env / .env.local から自動読み込みされます（プロジェクトルートの判定は .git または pyproject.toml を基準）。

---

## ディレクトリ構成

以下は主要ファイルとディレクトリの構成（src 配下）です:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - news_collector.py              — RSS ニュース収集・保存ロジック
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         — 市場カレンダー管理ユーティリティ
    - schema.py                      — DuckDB スキーマ定義・init_schema
    - audit.py                       — 監査ログ用テーブル定義・初期化
    - quality.py                     — データ品質チェック（QualityIssue）
  - strategy/
    - __init__.py                    — 戦略層の入り口（拡張場所）
  - execution/
    - __init__.py                    — 発注・実行層の入り口（拡張場所）
  - monitoring/
    - __init__.py                    — モニタリング / メトリクス（拡張場所）

---

## 設計上のポイント / 注意点

- レート制限、リトライ、トークンリフレッシュを組み合わせて堅牢な API 呼び出しを実現していますが、実運用ではさらに監視や適切なスロットリング実装（分散環境）を検討してください。
- 各種保存処理は冪等（ON CONFLICT を利用）を目指して実装されていますが、外部からの手動変更やスキーマの破壊的変更があると想定外の動きになる可能性があります。
- RSS 処理では SSRF・XML Bomb 等の防御を行っていますが、公開 RSS を大量に取得する際は運用面での制限や信頼できるソースの採用を推奨します。
- DuckDB によるローカル DB を前提としています。共有 DB や大規模運用では別途耐久性やバックアップ戦略を設計してください。

---

## 開発 / 貢献

- 新しい戦略や実行モジュールは `strategy/`、`execution/` に実装してください。
- テストを追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env ロードを無効化できます。
- 既存のスキーマや DDL を変更する場合は後方互換性に注意してください（既存データのマイグレーションが必要になる可能性があります）。

---

ご不明点や追加してほしいドキュメント（例: CLI、デプロイ手順、Slack 通知例、kabuステーション連携サンプルなど）があれば教えてください。README を拡張して具体的な利用手順を追加できます。