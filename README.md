# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ層）。  
本リポジトリはデータ取得・ETL・データ品質チェック・ニュース収集・マーケットカレンダー管理・監査ログ用スキーマ等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された内部ライブラリ群です。主な役割は以下のとおりです。

- J-Quants API を用いた市場データ（株価日足、財務データ、JPX カレンダー）の取得
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義・初期化
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日/半日/SQ 判定、夜間更新ジョブ）
- 監査ログ（signal → order → execution のトレーサビリティ）スキーマ
- データ品質チェック（欠損・重複・スパイク・日付整合性）

設計上のポイント：
- J-Quants API のレート制限（120 req/min）を守る制御と再試行ロジック
- データの冪等性（DuckDB 側で ON CONFLICT による更新）
- Look-ahead bias を避けるための fetched_at / UTC タイムスタンプ記録
- RSS 収集での SSRF / XML Bomb 対策（スキーム検証、defusedxml、受信サイズ制限）

---

## 機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - id_token の自動リフレッシュ、リトライ（指数バックオフ）、レートリミッタ
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema()：DB 初期化
- data.pipeline
  - run_daily_etl()：日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data.news_collector
  - fetch_rss()：RSS フィード取得（SSRF / サイズ制限 / gz 解凍等）
  - save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化（トラッキングパラメータ除去）／ID は SHA-256 の先頭 32 文字
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job(): 夜間バッチで JPX カレンダー更新
- data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks()
- data.audit
  - 監査用テーブル定義・初期化（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db

---

## 要求環境（推奨）

- Python 3.10+
- 必須ライブラリ（最低限）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに追加で必要な外部パッケージがあれば requirements.txt を整備してください）

---

## 環境変数（設定）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージ位置から探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は明記）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

.env の例（参考）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```
4. プロジェクトルートに `.env` を作成し必要な環境変数を設定
5. DuckDB スキーマの初期化（下記「使い方」参照）

---

## 使い方（簡単な例）

以下は基本的な操作例です。Python REPL やスクリプトから利用できます。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作成
```

- 監査ログ用 DB 初期化（専用DBを使う場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL を実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

- ニュース収集ジョブを実行（既知の銘柄リストを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None, reference_date=date.today())
for i in issues:
    print(i)
```

- J-Quants のトークンを直接取得（必要な場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
```

注意点:
- run_daily_etl 等は各ステップで例外を捕捉して継続する設計ですが、戻り値の ETLResult.errors を確認してください。
- J-Quants API のレート制限（120 req/min）を遵守する実装になっています。大量取得時は時間を要する場合があります。
- テスト時に自動 .env 読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発メモ / 実装のポイント

- data.jquants_client
  - レートリミッタ（固定間隔スロットリング）と指数バックオフリトライを実装。
  - 401 受信時はキャッシュ更新して1回だけ自動リトライ。
  - ページネーション対応（pagination_key）。
  - save_* は ON CONFLICT による冪等保存。
- data.news_collector
  - URL 正規化／トラッキングパラメータ除去、記事 ID は SHA-256 の先頭 32 文字。
  - SSRF 対策（スキーム検証、ホストがプライベートかどうかチェック、リダイレクト検査）。
  - 受信サイズの上限（10 MB）、gzip の解凍チェック。
  - DB 保存はチャンク化してトランザクションで実行し、INSERT ... RETURNING を使用して実際に追加された ID を取得。
- data.calendar_management
  - DB の market_calendar を優先し、未登録日は曜日フォールバック（平日＝営業日）で処理。
  - next/prev_trading_day は最大探索日数で無限ループ防止。
- data.quality
  - 各チェックは QualityIssue オブジェクトのリストを返す（Fail-Fast しない）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集と DB への保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py       — マーケットカレンダー管理・夜間更新
    - audit.py                     — 監査ログスキーマ初期化
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 空（戦略層は別途実装）
  - execution/
    - __init__.py                  — 空（発注/ブローカー連携は別途実装）
  - monitoring/
    - __init__.py                  — 空（監視・メトリクスは別途実装）

ドキュメント参照:
- DataPlatform.md, DataSchema.md 等（リポジトリに存在する想定の仕様ドキュメント）に基づいて実装されています。

---

## ライセンス / 貢献

本リポジトリのライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（ここには含まれていません）。

---

### 最後に
何か特定の使い方（例: 自動化スケジュール、Docker 化、CI テスト用のモック設定等）を README に追加したければ教えてください。用途に応じた例や運用ガイドを追記します。