# KabuSys

日本株自動売買システムのコアライブラリ（ミニマル実装）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、DuckDB スキーマ、品質チェック、監査ログなどを提供します。

## 概要
KabuSys は日本株の自動売買に必要なデータ基盤とユーティリティ群をまとめたパッケージです。  
主に次を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得する
- RSS からニュースを収集して記事と銘柄の紐付けを行う
- DuckDB を用いてデータスキーマを初期化・永続化する
- ETL（差分取得・バックフィル・品質チェック）を実行する
- 監査ログ（シグナル→発注→約定のトレース）用スキーマを提供する
- カレンダーや営業日判定などのユーティリティを備える

このリポジトリはライブラリ層であり、実際の戦略実行・発注エンジンや UI は含みません。

## 主な機能一覧
- 環境設定読み込み（.env 自動読み込み、環境変数優先）
- J-Quants API クライアント
  - レート制限厳守、リトライ（バックオフ）、トークン自動リフレッシュ、ページネーション対応
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - init_schema, get_connection
- ETL パイプライン
  - 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl 等）
  - 差分更新、バックフィル、品質チェック統合
- ニュース収集（RSS）
  - fetch_rss / run_news_collection
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 限度
  - raw_news / news_symbols への冪等保存
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合を検出（run_all_checks）
- マーケットカレンダー管理・営業日判定ユーティリティ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログスキーマ（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db

## 要件（依存）
- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, datetime, logging 等）を使用

実プロジェクトでは pyproject.toml または requirements.txt を用意して依存管理してください。

## セットアップ手順（開発向け）
1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成 & 有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # 開発用にパッケージとしてインストールする場合
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置することで自動読み込みされます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨の最低環境変数（.env の例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

# Slack (通知等に使用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時デフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム設定
KABUSYS_ENV=development   # または paper_trading / live
LOG_LEVEL=INFO
```

注意:
- .env のパースはシェル風（`export KEY=val` 対応、クォート・コメント処理あり）です。
- `.env.local` は `.env` 上書きとして読み込まれます。

## 使い方（主な例）

以下はインタラクティブに使う例（Python スクリプト・REPL など）。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) J-Quants から日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を実行しておく
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 個別に株価 ETL を実行
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

4) ニュース収集ジョブ実行
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄候補セット（例: 既知銘柄コードの集合）
known_codes = {"7203","6758","9984"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

5) カレンダー更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
```

6) 監査ログスキーマ初期化
```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
# または専用 DB を作る
# conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

7) データ品質チェック
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

8) 低レベル: J-Quants クライアント直接利用
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token から自動的に取得されます
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,1))
```

## 設計上のポイント・注意事項
- J-Quants API クライアントはレート制限（120 req/min）を守るための固定間隔スロットリングとリトライロジックを実装しています。
- トークン（ID token）は必要に応じて自動リフレッシュされます（401 を受けた場合、一回だけリフレッシュして再試行）。
- DuckDB への保存はできる限り冪等（ON CONFLICT）を採用しています。
- ニュース収集は SSRF 対策、XML の攻撃対策（defusedxml）、レスポンスサイズ制限を備えています。
- ETL の品質チェックは Fail-Fast ではなく全件検査して問題を列挙します。致命的な問題は呼び出し元で判断してください。

## 環境設定（主な環境変数）
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API パスワード
- KABU_API_BASE_URL (任意) : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack チャンネル ID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) : 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) : 実行環境（development / paper_trading / live）
- LOG_LEVEL (任意) : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化

必須項目が未設定の場合、kabusys.config.settings の対応プロパティを呼ぶと ValueError が発生します。

## ディレクトリ構成
（抜粋、主要ファイル）
```
.
├─ pyproject.toml / setup.cfg (想定)
├─ .git/
├─ .env               # 自動ロード対象（プロジェクトルート）
├─ .env.local         # .env 上書き
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ data/
│     │  ├─ __init__.py
│     │  ├─ jquants_client.py
│     │  ├─ news_collector.py
│     │  ├─ schema.py
│     │  ├─ pipeline.py
│     │  ├─ calendar_management.py
│     │  ├─ audit.py
│     │  └─ quality.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

## 開発上のヒント
- パッケージは src レイアウトになっています。開発時は `pip install -e .` で編集可能な状態にできます。
- DuckDB は軽量で高速なためローカル開発に適しています。分析ジョブ時にはインメモリ（":memory:"）も利用可能です。
- ロギングは各モジュールで logger.getLogger(__name__) を使っています。アプリ側でハンドラ/レベルを設定してください。

## ライセンス・貢献
この README にはライセンス情報は含まれていません。実際の公開時は LICENSE を追加し、貢献フロー（CONTRIBUTING.md）を用意するとよいでしょう。

---

不明点や README に追加したい情報（例: CI、デプロイ方法、外部サービス連携の詳細、サンプルデータ）などがあれば教えてください。README を拡張して反映します。