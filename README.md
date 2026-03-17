# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants API や RSS を使ったデータ収集、DuckDB ベースのスキーマ定義、ETL パイプライン、品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定トレーサビリティ）などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要 API / サンプル）
- 環境変数（設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤向けユーティリティ群です。設計上の特徴は次のとおりです。

- J-Quants API から株価（日足）・財務・マーケットカレンダーを安全に取得（レート制限・リトライ・トークン自動更新）。
- RSS からニュースを収集し、銘柄コード抽出・DB保存を行うニュースコレクタ（SSRF、XML攻撃、gzip爆弾等に対する対策あり）。
- DuckDB を用いた 3 層（Raw / Processed / Feature）＋ Execution / Audit のスキーマを定義・初期化。
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）を提供。
- マーケットカレンダー管理・営業日判定ユーティリティ。
- 発注〜約定までの監査ログ（トレーサビリティ）を保持する監査用スキーマ。
- データ品質チェック（欠損、重複、スパイク、日付不整合など）。

---

## 主な機能

- data.jquants_client
  - 株価（日足）・財務（四半期）・マーケットカレンダー取得
  - レートリミッタ（120 req/min）、指数バックオフリトライ（408/429/5xx）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
  - fetched_at による取得時刻のトレース（Look-ahead 防止）
- data.news_collector
  - RSS フィード取得、記事正規化、ID（URL 正規化 SHA-256 の先頭 32 文字）生成
  - SSRF 対策（リダイレクト検証・プライベートホスト拒否）、defusedxml による安全な XML パース、受信サイズ制限
  - DuckDB への冪等保存（INSERT ... RETURNING、チャンク処理）
  - 銘柄コード抽出（4 桁）と news_symbols テーブルへの紐付け
- data.schema
  - DuckDB のスキーマ定義（raw_prices, raw_financials, raw_news, prices_daily, features, signals, orders, trades, positions, 監査テーブル等）
  - init_schema(db_path) で初期化
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェック（オプション）
  - 差分更新、バックフィル、品質チェック結果を ETLResult として返却
- data.calendar_management
  - 営業日判定、前後営業日取得、期間内営業日列挙、calendar_update_job（夜間バッチでカレンダー更新）
- data.audit
  - 監査（signal_events, order_requests, executions）テーブルと初期化関数（init_audit_schema / init_audit_db）
- data.quality
  - 欠損検出、スパイク検出、重複検出、日付整合性チェック、run_all_checks

---

## セットアップ手順

前提: Python 3.8+（型アノテーションや一部標準ライブラリ挙動に依存します。推奨は最新の安定版）

1. リポジトリをクローン（開発環境）
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - またはパッケージ化されている場合: pip install -e .

   ※ 必要に応じて logging, urllib 等の標準ライブラリを利用します。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込み（config.py にて .git または pyproject.toml を基準に探索）
   - 自動読み込みを無効化する場合は環境変数:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化（例）
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. 監査DBを別ファイルとして使う場合:
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

---

## 環境変数（設定）一覧

主に config.Settings 経由で利用されます。必須項目は _require により未設定時に例外を投げます。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client の認証で使用）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注層を実装する際に利用）
- SLACK_BOT_TOKEN : Slack 通知用トークン（任意機能を実装する場合）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV : 開発環境識別（development | paper_trading | live）。デフォルト "development"
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト "INFO"
- DUCKDB_PATH : DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH : 監視用 SQLite パス。デフォルト "data/monitoring.db"
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" をセットすると自動 .env 読み込みを無効化

.env ファイルのパースは明示的にシェル風の `export KEY=val` を許容し、クォートやインラインコメント等の取り扱いに配慮しています。

---

## 使い方（主要 API とサンプル）

以下は典型的なワークフローの例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# デフォルトパスを使う例
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date=None -> 今日
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 事前に有効な銘柄一覧を用意
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

5) 監査スキーマ初期化（監査用 DB を別ファイルで用いる場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意:
- jquants_client の API 呼び出しは内部でレート制限・リトライ・トークンリフレッシュを行います。テスト時は id_token を明示的に注入して副作用を制御できます。
- news_collector は外部ネットワークアクセスを行います。テストでは _urlopen をモックして安全に動作を検証できます。

---

## ディレクトリ構成

（リポジトリの主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動読み込み機能）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ベースのニュース収集・保存・銘柄抽出
    - schema.py               -- DuckDB スキーマ定義・初期化
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  -- マーケットカレンダー管理（営業日判定など）
    - audit.py                -- 監査ログ（signal_events / order_requests / executions）
    - quality.py              -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py            -- 戦略関連モジュール（拡張領域）
  - execution/
    - __init__.py            -- 発注・ブローカー接続関連（拡張領域）
  - monitoring/
    - __init__.py            -- 監視関連（拡張領域）

---

## 開発メモ / 実装上の留意点

- DuckDB をデータレイクの永続レイヤとして採用。init_schema は冪等であり、既存テーブルは再作成されません。
- jquants_client はページネーション対応、ページ間で同一トークンを利用するためのモジュールレベルキャッシュを持ちます。
- news_collector は安全面（SSRF, XML Bomb, Gzip Bomb, サイズ制限）を強く意識して実装しています。外部 RSS を扱うため、実運用ではソースリスト（DEFAULT_RSS_SOURCES）を管理してください。
- 品質チェックは Fail-Fast ではなく全件収集し、呼び出し元が結果に応じて処理方針（停止/通知）を決定します。
- config の .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御できます。

---

フィードバックや補足ドキュメント（例: DataPlatform.md, DataSchema.md）に基づいて README を拡張できます。必要であれば各モジュールの使用例や API 詳細、運用手順（cron / Airflow などへの組み込み例）を追記します。