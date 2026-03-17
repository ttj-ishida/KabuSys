# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants API や RSS フィードから市場データ・ニュースを取得し、DuckDB に保存・整備するための ETL、データ品質チェック、マーケットカレンダー管理、監査ログ基盤などを提供します。

主な設計思想は「冪等性」「トレーサビリティ」「安全（SSRF対策・XML脆弱性対策）」「APIレート制御」「リトライ＆トークン自動更新」です。

## 機能一覧
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応、レートリミット・リトライ）
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - リフレッシュトークンからの id_token 取得／キャッシュ
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義（冪等で作成）
- ETL パイプライン
  - 差分更新ロジック（最終取得日からのバックフィル）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS）
  - RSS 取得・パース（defusedxml）、URL正規化、トラッキングパラメータ削除、記事ID生成（SHA-256）
  - SSRF 対策（リダイレクト先検査、プライベートアドレス遮断）
  - raw_news / news_symbols への冪等保存（チャンク挿入、INSERT ... RETURNING）
- マーケットカレンダー管理
  - 営業日判定、前後営業日検索、カレンダー差分更新ジョブ
- 品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue による集約（error / warning）
- 監査ログ（audit）
  - signal_events, order_requests, executions などの監査テーブルを初期化
  - 発注フローのトレースをUUIDチェーンで担保

## 必要な環境変数
このプロジェクトは .env ファイル（または OS 環境変数）から設定を取得します。自動読み込みはプロジェクトルートに .env/.env.local がある場合に有効です。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV — 環境: one of `development`, `paper_trading`, `live`（デフォルト: development）
- LOG_LEVEL — ログレベル: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の例（実際の値はそれぞれ設定してください）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトで requirements.txt を用意している場合はそれに従ってください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を配置するか、OS環境変数を設定。
   - 自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから初期化を実行します（例は下記「使い方」参照）。

## 使い方（例）

以下は主要なユースケースの最小例です。実行前に必要な環境変数がセットされていることを確認してください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = schema.init_schema(settings.duckdb_path)
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # 既に init_schema 済みとする
result = run_daily_etl(conn)  # target_date や id_token 等はオプション
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# known_codes は銘柄コードの集合（例: {'7203', '6758', ...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
print(results)
```

- カレンダー更新ジョブ（夜間バッチ用）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査ログスキーマ初期化（audit 用テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
init_audit_schema(conn)
```

ログ・エラー処理:
- 各モジュールは logging を利用しています。実行環境でログ設定（レベルやハンドラ）を行ってください。

API レート・リトライ:
- J-Quants API は 120 req/min に基づく固定間隔スロットリングを実装しています。
- ネットワークエラーや 408/429/5xx 系に対しては指数バックオフでリトライ（最大 3 回）。
- 401 受信時はリフレッシュトークンで id_token を自動更新し 1 回リトライします。

## 主要なモジュール（概要）
- kabusys.config — 環境変数・設定管理（.env の自動ロード、必須キー取得、環境判定）
- kabusys.data.schema — DuckDB スキーマ定義 / init_schema / get_connection
- kabusys.data.jquants_client — J-Quants API クライアント（取得 / 保存用 helper）
- kabusys.data.pipeline — ETL パイプライン（run_daily_etl 等）
- kabusys.data.news_collector — RSS 取得・記事前処理・DB保存・銘柄抽出
- kabusys.data.calendar_management — マーケットカレンダー管理・営業日ロジック
- kabusys.data.quality — データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.audit — 監査ログ用スキーマ初期化
- kabusys.execution, kabusys.strategy, kabusys.monitoring — パッケージプレースホルダ（モジュール分割のためのパッケージ構成）

## ディレクトリ構成
（主要なファイル・モジュールのみ抜粋）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ execution/
   │  └─ __init__.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ monitoring/
   │  └─ __init__.py
   └─ data/
      ├─ __init__.py
      ├─ jquants_client.py
      ├─ news_collector.py
      ├─ schema.py
      ├─ pipeline.py
      ├─ calendar_management.py
      ├─ audit.py
      └─ quality.py
```

## 注意点・運用上のヒント
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb`。バックアップや排他制御（複数プロセスからの同時書き込み）に注意してください。
- RSS 取得は外部ネットワークアクセスを伴うため、内部ネットワークやプライベートIPへ接続しないよう SSRF 対策を実装しています。fetch_rss はスキーム・ホストの検証を行います。
- ETL の差分ロジックは「最終取得日」からのバックフィルを行います。バックフィル日数は pipeline のパラメータで調整可能です。
- 監査ログ（order_requests 等）は削除せず永続化することを想定しています。時刻は UTC で保存されます。
- 開発環境（KABUSYS_ENV=development）では実際の発注を行わない等のガードを別途用意してください（execution 層の実装に依存）。

---

不明点や README に追加したい利用例（CI/CD、cron ジョブ、Docker 化など）があれば教えてください。README を用途に合わせて拡張します。