# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（部分実装）。  
主にデータ取得・ETL・データ品質チェック・ニュース収集・マーケットカレンダー管理・監査ログ周りの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株取引に必要なデータ基盤とETL処理、及び監査トレースを提供する Python パッケージです。  
主な責務は以下の通りです。

- J-Quants API からの株価・財務・マーケットカレンダーの取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB ベースのスキーマ定義とデータ永続化（冪等保存）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキングパラメータ除去等）
- マーケットカレンダー管理（営業日判定・前後営業日探索）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイントとして、Look-ahead バイアスの防止、冪等性（ON CONFLICT を利用）、API レート制御、堅牢なエラーハンドリングを重視しています。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - DuckDB へ冪等保存（save_* 関数）
  - レートリミット（120 req/min）・リトライ・401 時の自動リフレッシュ

- data.schema
  - DuckDB のスキーマ定義および初期化（init_schema, get_connection）

- data.pipeline
  - 日次 ETL（run_daily_etl）
  - 個別 ETL：run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得と backfill 対応、品質チェック連携

- data.news_collector
  - RSS フィード取得（fetch_rss）
  - raw_news への保存（save_raw_news）
  - 銘柄コード抽出（extract_stock_codes）と news_symbols 保存
  - SSRF / XML 攻撃対策・受信サイズ制限・gzip 解凍対策

- data.calendar_management
  - 営業日判定・前後営業日探索・期間内営業日取得
  - 夜間カレンダー更新ジョブ（calendar_update_job）

- data.audit
  - 監査ログ用スキーマの初期化（init_audit_schema / init_audit_db）
  - シグナル/発注/約定のトレーサビリティテーブル

- data.quality
  - 欠損・重複・スパイク（急騰・急落）・日付不整合のチェック
  - QualityIssue を返却し、ETL 側は重大度に応じて判断可能

- その他
  - 環境変数読み込みと設定管理（kabusys.config.Settings）
  - strategy, execution, monitoring 用のパッケージプレースホルダ

---

## 要件

- Python 3.10+
  - 型ヒントに `|`（PEP 604）が用いられているため 3.10 以上を想定しています
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリで実装されている部分も多い）

インストール例（仮）:
```
python -m pip install duckdb defusedxml
# または pyproject.toml / requirements.txt がある場合はそれに従ってください
```

---

## 環境変数 / 設定

config.Settings により環境変数を読み込みます。自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（OS 環境変数 > .env.local > .env の優先順位）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — {development, paper_trading, live} のいずれか（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする
2. 仮想環境を作成し依存をインストールする
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 追加の依存があればインストール
   ```
3. 環境変数を設定（.env または環境に直接）
   - 必須キー（JQUANTS_REFRESH_TOKEN 等）を .env に記載
4. DuckDB スキーマを初期化
   - Python REPL / スクリプトから schema.init_schema を実行
   ```py
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   - 監査ログ専用 DB を作る場合:
   ```py
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な API と実行例）

以下は簡単な実行例です。用途に合わせてスクリプト化して cron / Airflow 等に組み込んでください。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```py
from kabusys.data import schema, pipeline

# DB 初期化（存在しなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を指定しないと今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ
```py
import duckdb
from kabusys.data.news_collector import run_news_collection

conn = duckdb.connect("data/kabusys.duckdb")
# sources を省略するとデフォルト（Yahoo Finance のカテゴリRSS）を使用
# known_codes は銘柄コード抽出に使う有効コード集合（省略可能）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

- カレンダー夜間更新ジョブ
```py
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- 監査スキーマ初期化（既存接続に追加）
```py
from kabusys.data import schema
from kabusys.data import audit

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

- J-Quants から直接株価を取得して保存
```py
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## ディレクトリ構成

リポジトリの主要なファイル／モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント＆保存ロジック
    - news_collector.py     — RSS ニュース収集と保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー判定／更新
    - audit.py              — 監査ログスキーマ
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py           — 戦略関連（プレースホルダ）
  - execution/
    - __init__.py           — 発注/実行関連（プレースホルダ）
  - monitoring/
    - __init__.py           — 監視関連（プレースホルダ）

---

## 開発メモ / 設計上の注意点

- API レート制御: J-Quants は 120 req/min を想定。jquants_client に固定間隔スロットリングを実装済み。
- リトライ: 408/429/5xx に対して指数バックオフを行い、401 ではリフレッシュトークンを使って一度だけ自動更新。
- データのタイムスタンプ: fetched_at や created_at は UTC を用いる方針。
- 冪等性: DuckDB への保存は ON CONFLICT を利用し重複や再実行に耐える設計。
- セキュリティ: news_collector は defusedxml を利用し、SSRF 対策（リダイレクト検査・プライベートアドレス回避）や受信サイズ制限を実装。
- Python バージョン: 型ヒントの記法などから Python >= 3.10 を推奨。

---

## よくある質問 / トラブルシュート

- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されているか、またはプロジェクトルート（.git / pyproject.toml）を検出できない場合は自動読み込みをスキップします。テスト時は明示的に環境変数を設定してください。
- DuckDB の初期化で権限エラー:
  - parent ディレクトリが存在しない場合は init_schema が自動作成しますが、OS 権限に注意してください。
- J-Quants の 401 が頻発する:
  - refresh token が無効、もしくは環境変数が正しく設定されていない可能性があります。settings.jquants_refresh_token を確認してください。

---

この README はコードベースの docstring とソースから生成しています。プロジェクトを拡張する際は strategy / execution / monitoring 以下に機能を追加し、data/schema のスキーマ変更は互換性（既存データ）に配慮してください。