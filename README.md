# KabuSys

日本株向けの自動売買／データプラットフォーム。J-Quants API や RSS フィードからデータを取得し、DuckDB に保存、ETL（差分取得・バックフィル）、品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレース）などの機能を提供します。

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX カレンダーを取得
  - レート制限（120 req/min）に従ったスロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC 記録し、look-ahead bias を防止

- ニュース収集（RSS）
  - RSS から記事を取得し前処理して DuckDB に保存（冪等）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 回避、受信サイズ制限
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成
  - 記事と銘柄コードの紐付け機能

- ETL パイプライン
  - 差分取得・バックフィル（デフォルト 3 日）・保存（ON CONFLICT DO UPDATE）
  - 市場カレンダー先読み（デフォルト 90 日）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査ログ用スキーマ（signal → order_request → execution のトレース）
  - インデックス定義・冪等な初期化関数

- 監査・トレーサビリティ
  - signal_events / order_requests / executions を使用して発注〜約定を UUID で追跡
  - すべてのタイムスタンプは UTC 保存を想定

---

## 必要要件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS / Linux: source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布があれば）pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - 省略可能:
     - KABUSYS_ENV=(development|paper_trading|live)  # default development
     - LOG_LEVEL=(DEBUG|INFO|WARNING|ERROR|CRITICAL)  # default INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

例: `.env`（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB スキーマを作成するには `kabusys.data.schema.init_schema` を使います。

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ（order_requests / executions 等）を追加で初期化する場合:
```python
from kabusys.data import audit, schema
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

※ `:memory:` を渡すとインメモリ DB を使用できます。

---

## 使い方（例）

- 日次 ETL（価格・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS 取得 → DuckDB 保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# sources: {source_name: rss_url} の辞書（省略時は DEFAULT_RSS_SOURCES）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants の個別利用（トークン取得、日足取得）
```python
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings の JQUANTS_REFRESH_TOKEN を使用
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 設計上のポイント・注意点

- レート制限: J-Quants は 120 req/min を想定し、内部で固定間隔のスロットリングを行います。
- 冪等性: raw テーブルへの保存は ON CONFLICT DO UPDATE / DO NOTHING を使い冪等化されています。
- セキュリティ:
  - RSS: defusedxml による XML パース、SSRF 対策、受信サイズ上限（10MB）などを実装。
  - 環境変数ロード: `.env` を自動ロードするが、テスト等で無効化可能。
- 日付処理: 全体で date オブジェクトを使用し、タイムゾーン混入に注意しています（監査ログでは UTC を前提）。
- 品質チェック: ETL 後に品質チェックを行い、error/warning を返すが、即時停止せず呼び出し元で判断できる設計です。

---

## ディレクトリ構成

以下はソースの主要構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                --- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      --- J-Quants API クライアント（取得・保存）
    - news_collector.py      --- RSS ニュース収集・保存・銘柄抽出
    - schema.py              --- DuckDB スキーマ定義・初期化
    - pipeline.py            --- ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py --- 市場カレンダー管理（営業日判定等）
    - audit.py               --- 監査ログ（signal / order_request / executions）
    - quality.py             --- データ品質チェック
  - strategy/
    - __init__.py            --- 戦略関連（空のパッケージ）
  - execution/
    - __init__.py            --- 実行（発注）関連（空のパッケージ）
  - monitoring/
    - __init__.py            --- 監視関連（空のパッケージ）

（実際のプロジェクトには README・ドキュメント・CI 設定などが別途あります）

---

## トラブルシューティング

- 環境変数が見つからない/未設定の場合:
  - config.Settings は必須変数アクセス時に ValueError を送出します。
  - 自動 .env ロードを無効化している場合は再度有効化するか、環境に直接設定してください。

- J-Quants 401 エラー:
  - ライブラリは自動でリフレッシュを試みますが、refresh token が無効な場合は手動で更新してください。

- RSS 取得で不正な URL / プライベートホスト検出:
  - SSRF 対策としてプライベート IP / 非 http(s) スキームは拒否されます。ソース URL を確認してください。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。詳細な仕様や運用手順（監視・アラート・Slack 通知・kabu ステーションとの連携など）は別ドキュメントを参照してください。