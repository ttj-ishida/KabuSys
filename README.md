# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

このリポジトリは、J-Quants API を中心とした日本株データ収集、ETL、品質チェック、ニュース収集、および実行/監査のためのスキーマとユーティリティ群を提供します。DuckDB をデータストアとして利用し、戦略層・発注層へつなぐための基盤機能を備えています。

---

## 特徴（主要機能）

- 環境設定管理
  - .env / .env.local を自動で読み込み（必要に応じて自動読み込み無効化可）
  - 必須環境変数の簡易取得（settings オブジェクト）

- J-Quants クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を尊重する固定間隔レートリミッタ
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスに配慮
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - 複数 RSS ソースからの収集、トラッキングパラメータ除去、URL 正規化
  - 記事ID に SHA-256（先頭 32 文字）を採用して冪等性を確保
  - defusedxml による XML 攻撃対策、SSRF 対策（スキーム検証とプライベートIP排除）、レスポンスサイズ上限
  - DuckDB へのバルク保存（トランザクション、INSERT ... RETURNING）

- ETL パイプライン
  - 差分更新（最終取得日を確認して未取得分のみ取得）
  - backfill（直近数日分を再取得して API の後出し修正を吸収）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 結果を ETLResult として集約

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層を定義
  - 監査ログ（signal_events / order_requests / executions）を別途初期化可能
  - インデックスや制約を含む完全な DDL を提供

---

## 必要条件（依存環境）

- Python 3.9+（typing の | 型や typing.TypedDict を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, logging, datetime, hashlib など

（プロジェクト配布時は requirements.txt または pyproject.toml を用意してください）

---

## 環境変数（主なもの）

アプリケーション設定は環境変数から読み取ります。必須変数は settings から参照時にチェックされます。

必須（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）

※ .env.example を参考に .env を作成することを想定しています。

---

## セットアップ手順（開発用）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate または .venv\Scripts\activate

2. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトが配布される際は pip install -r requirements.txt）

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な変数をセット
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行（下記「使い方」参照）

---

## 使い方（簡単なコード例）

以下は主要なモジュールの使い方例です。実アプリではロギング設定やエラーハンドリングを適切に行ってください。

- settings の利用（環境変数のアクセス）

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 日次 ETL の実行

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 省略時は今日を対象に実行
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取込）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- J-Quants から株価のみ直接取得して保存（テスト用途）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from kabusys.config import settings
import duckdb

conn = init_schema(settings.duckdb_path)
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- 監査ログスキーマの初期化（監査テーブルのみ）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルで用意する場合
audit_conn = init_audit_db(":memory:")
# あるいは既存の conn に対して init_audit_schema(conn) を呼ぶことも可能
```

---

## 実装上の注意点 / 設計メモ

- J-Quants クライアントはモジュールレベルで ID トークンをキャッシュしており、ページネーション間で共有します。401 が返った場合は 1 回だけ自動的にリフレッシュして再試行します。
- ニュース収集は SSRF や XML 攻撃対策、Gzip 解凍後のサイズ検査など堅牢性に配慮しています。リンク正規化・トラッキング除去を行い、記事 ID は SHA-256（先頭 32 文字）で決定します。
- DuckDB への保存は基本的に冪等（ON CONFLICT）設計となっており、ETL は差分更新とバックフィルを組み合わせて堅牢に動作します。
- 品質チェックモジュールは Fail-Fast ではなく問題を集めて返す設計です。呼び出し側（運用ジョブ）は severity に応じた対応を行ってください。
- market_calendar データが欠損している場合は曜日ベースでのフォールバック（週末は非営業日）を行います。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル/モジュール構成は以下の通りです（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - news_collector.py                — RSS ニュース収集・保存
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - schema.py                        — DuckDB スキーマ定義 / init_schema
    - calendar_management.py           — カレンダー関連ユーティリティと更新ジョブ
    - audit.py                         — 監査ログ用テーブル初期化
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（実際のリポジトリには追加のユーティリティや CLI、サンプルスクリプトがある場合があります）

---

## 開発・運用 Tips

- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。パスは DUCKDB_PATH で変更可能。
- J-Quants API のレート制限を超えないため、直接大量のリクエストを投げるようなコード変更は避けてください。ライブラリの _RateLimiter が 120 req/min を想定しています。
- ニュース収集で外部 RSS をフェッチする際はタイムアウトや例外ログを監視し、リトライルールや監視アラートを整備してください。

---

## ライセンス / コントリビューション

（ここにライセンスやコントリビューションに関する情報を追記してください）

---

README に不足している実行スクリプトや設定ファイル（.env.example、requirements.txt、CLI ラッパー等）はプロジェクトに合わせて追加してください。必要であれば README を拡張して CLI / systemd / Docker の運用手順やサンプル .env を追記します。