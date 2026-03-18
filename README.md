# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）  
このリポジトリは、J-Quants 等の外部 API からマーケットデータ／財務データ／ニュースを収集し、DuckDB に蓄積・品質チェック・特徴量生成・発注監査用スキーマを提供することを目的としたモジュール群です。

主な設計方針：
- データ取得は冪等（ON CONFLICT）で保存し、Look-ahead Bias を防止するため fetched_at 等のトレーサビリティを保持
- API レート制限・リトライ・トークン自動リフレッシュに対応
- RSS ニュース収集は SSRF／XML 攻撃対策・追跡パラメータ除去などを実装
- DuckDB を中心とした三層データ設計（Raw / Processed / Feature）と、Execution/Audit 層を提供

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - 自動トークンリフレッシュ、レート制限、リトライ（指数バックオフ）
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義と索引
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分 + backfill）
  - 日次一括実行（カレンダー取得 → 株価 → 財務 → 品質チェック）
- ニュース収集モジュール
  - RSS フィード取得、前処理（URL除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成（冪等）
  - SSRF / Gzip bomb / XML 攻撃対策
  - raw_news / news_symbols への保存（チャンク・トランザクション）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト
  - 夜間カレンダー差分更新ジョブ
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
  - QualityIssue 型で問題を集約
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までを追跡する監査スキーマ
  - 発注要求は冪等キー（order_request_id）を想定

---

## 必要条件

- Python 3.10 以上（typing 機能を活用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS 等）

（実際のインストールはプロジェクトの requirements.txt があればそれを利用してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - ルートに `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（使用する機能に応じて設定）:
     - JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabuステーション API パスワード（注文実行系を使う場合）
     - SLACK_BOT_TOKEN：Slack 通知用トークン（任意）
     - SLACK_CHANNEL_ID：Slack チャンネル ID（任意）
   - データベースパス（任意、デフォルトを使用可能）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB; デフォルト: data/monitoring.db）
   - 実行モード:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C00000000
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## データベース初期化

DuckDB のスキーマを初期化するには `kabusys.data.schema.init_schema()` を使用します。

例:
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")

# またはメモリ DB
conn_mem = schema.init_schema(":memory:")
```

監査ログ（audit）用スキーマは別関数で追加できます:
```python
from kabusys.data import audit

# 既存の接続に監査スキーマを追加
audit.init_audit_schema(conn, transactional=True)

# 監査専用 DB を作成する場合
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

注意:
- init_schema は冪等（既存テーブルはスキップ）です。
- init_audit_schema は接続の TimeZone を UTC に固定します。

---

## 基本的な使い方

### 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
```python
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
# あるいは初期化済み conn = schema.init_schema(...)

result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は以下を順次実行します：
1. カレンダー ETL（先読み）
2. 株価日足 ETL（差分 + backfill）
3. 財務データ ETL（差分 + backfill）
4. 品質チェック（オプションで無効化可能）

オプション例:
- target_date: ETL 対象日（省略時は今日）
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3 日）
- run_quality_checks: 品質チェックの実行有無

### ニュース収集
RSS フィードから記事を取得して raw_news に保存する:
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# 既知の銘柄コードセット（抽出時に使用）
known_codes = {"7203", "6758", "9984"}  # 実運用では銘柄マスターから

# ソース指定省略時は DEFAULT_RSS_SOURCES を使用
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

個別RSS取得:
```python
articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/...", source="yahoo_finance")
new_ids = news_collector.save_raw_news(conn, articles)
```

設計上のポイント:
- URL 正規化（utm_* 等のトラッキング除去）
- 記事IDは正規化 URL の SHA-256（先頭32文字）
- SSRF 対策（スキーム検証、リダイレクト先のプライベートIP拒否）
- Gzip 圧縮レスポンス・サイズ制限（デフォルト 10MB）

### J-Quants API クライアントの直接利用例
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 認証トークンは settings.jquants_refresh_token を用いるか、明示的に渡す

# 株価取得
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)

# 財務取得
fins = jq.fetch_financial_statements(code="7203")
jq.save_financial_statements(conn, fins)

# カレンダー取得
calendar = jq.fetch_market_calendar()
jq.save_market_calendar(conn, calendar)
```

J-Quants クライアントの特徴:
- レート制限 120 req/min を固定間隔スロットリングで順守
- リトライ（最大 3 回、指数バックオフ）と 401 時のトークン自動リフレッシュ
- fetched_at を UTC ISO8601 で記録しトレーサビリティを確保

---

## 品質チェック（quality モジュール）

提供チェック：
- 欠損データ検出（open/high/low/close の NULL）
- 重複レコード検出（主キー重複）
- スパイク検出（前日比の変動率が閾値を超える）
- 日付整合性チェック（未来日付・非営業日のデータ）

全チェック実行:
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

QualityIssue 型により、check_name / table / severity / detail / rows を取得できます。

---

## マーケットカレンダー関係

便利関数:
- is_trading_day(conn, d): 指定日が営業日か判定
- next_trading_day(conn, d): 次の営業日
- prev_trading_day(conn, d): 前の営業日
- get_trading_days(conn, start, end): 期間内の営業日リスト
- is_sq_day(conn, d): SQ日判定
- calendar_update_job(conn): 夜間カレンダー差分取得ジョブ

カレンダーが未取得の場合は曜日（土日）ベースのフォールバックが適用されます。

---

## Auto .env 読み込み

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で自動ロードします。
- OS 環境変数は保護され、`.env.local` の override は OS 環境変数を上書きしません。
- 自動ロードを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env のパースは Bash の export KEY=val 形式やクォート、インラインコメント等に対応しています。

---

## 主なファイル・ディレクトリ構成

（ライブラリは src/kabusys 以下に配置）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - calendar_management.py — カレンダー更新・営業日ロジック
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ（発注 → 約定トレース）
  - strategy/                 — （戦略モジュールの雛形）
  - execution/                — （発注・ブローカー接続の雛形）
  - monitoring/               — （監視・メトリクスの雛形）

---

## 開発メモ / 注意点

- DuckDB の SQL 実行ではプレースホルダ（?）を使用してインジェクションリスクを抑えていますが、文字列連結での DDL はコード中に存在するため、外部から DDL を直接書き換える際は注意してください。
- ニュース収集では受信サイズ上限（デフォルト 10MB）や Gzip 解凍後サイズチェックを行い、Gzip bomb などの攻撃を軽減しています。
- J-Quants API のレート制限は固定間隔（スロットリング）方式で制御しています。バースト処理を行いたい場合は別実装が必要です。
- テスト時に .env 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてください。

---

## 参考 / よく使う関数一覧

- data.schema.init_schema(db_path)
- data.schema.get_connection(db_path)
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, ...)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.quality.run_all_checks(conn, ...)
- data.audit.init_audit_schema(conn) / init_audit_db(path)
- data.calendar_management.is_trading_day(conn, d)

---

ご不明点や README に追加したい利用シナリオ（例：kabuステーション経由の注文フロー、Slack 通知連携サンプル等）があれば教えてください。必要に応じてサンプルコードや運用手順を追加します。